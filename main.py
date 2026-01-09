import time
import threading
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import helpers
import db

# Setup
helpers.setup_logging()
config = helpers.get_config()

if not config['BOT_TOKEN']:
    raise ValueError("No BOT_TOKEN found in .env file")

bot = telebot.TeleBot(config['BOT_TOKEN'])

# Initialize Database
db.init_db()

# --- Background Task: Alert Monitor ---
def monitor_alerts():
    while True:
        try:
            alerts = db.get_alerts()
            if not alerts:
                time.sleep(60)
                continue

            # Check alerts
            # Optimization: Group by symbol to fetch price once per loop? 
            # For simplicity, doing one by one or simple cache could work.
            # Let's do simple iterate for now given low volume expectation.
            
            for alert in alerts:
                symbol = alert['symbol']
                target = float(alert['target_price'])
                condition = alert['condition']
                
                price_data = helpers.get_crypto_price(symbol, config['CMC_API_KEY'])
                if not price_data:
                    continue
                
                current_price = price_data['price']
                triggered = False
                
                if condition == 'above' and current_price > target:
                    triggered = True
                elif condition == 'below' and current_price < target:
                    triggered = True
                    
                if triggered:
                    msg = f"🔔 **ALERT TRIGGERED** 🔔\n\n{symbol} is now ${current_price:,.2f} ({condition} ${target:,.2f})!"
                    bot.send_message(alert['user_id'], msg)
                    db.delete_alert(alert['id'])
                    
            time.sleep(60) # Check every minute
        except Exception as e:
            print(f"Alert Loop Error: {e}")
            time.sleep(60)

# Start Monitor Thread
alert_thread = threading.Thread(target=monitor_alerts, daemon=True)
alert_thread.start()

# --- Menus ---

def main_menu():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🚀 Top Trending", callback_data="trending"),
        InlineKeyboardButton("💰 Portfolio", callback_data="portfolio")
    )
    markup.row(
        InlineKeyboardButton("🔔 Set Alert", callback_data="alert"),
        InlineKeyboardButton("📋 My Alerts", callback_data="view_alerts")
    )
    markup.row(
        InlineKeyboardButton("💱 Converter", callback_data="convert"),
        InlineKeyboardButton("📰 News", callback_data="news")
    )
    markup.row(
        InlineKeyboardButton("❓ Help", callback_data="help")
    )
    return markup

# --- Handlers ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user = message.from_user
    db.add_user(user.id, user.username)
    bot.reply_to(message, f"👋 Hi {user.first_name}! I am your Crypto Assistant.\n\nSelect an option below:", reply_markup=main_menu())

# --- Callback for Alert Condition ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("cond_"))
def alert_condition_callback(call):
    # Format: cond_above_PRICE_SYMBOL
    try:
        parts = call.data.split('_')
        condition = parts[1]
        price = float(parts[2])
        symbol = parts[3]
        
        db.add_alert(call.message.chat.id, symbol, price, condition)
        bot.answer_callback_query(call.id, "Alert set!")
        bot.send_message(call.message.chat.id, f"✅ Set alert for {symbol} {condition} ${price}")
        bot.send_message(call.message.chat.id, "What else would you like to do?", reply_markup=main_menu())
    except Exception as e:
        print(f"Alert Callback Error: {e}")
        bot.answer_callback_query(call.id, "Failed to set alert.")
        bot.send_message(call.message.chat.id, f"❌ Error setting alert: {str(e)}")

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = call.message.chat.id
    
    if call.data == "main_menu":
        bot.send_message(chat_id, "Select an option below:", reply_markup=main_menu())

    elif call.data == "trending":
        bot.answer_callback_query(call.id, "Fetching trending coins...")
        data = helpers.get_top_cryptos(config['CMC_API_KEY'])
        msg = "🔥 **Top Trending (24h Change)**\n"
        for coin in data:
            msg += f"• {coin['symbol']}: ${coin['price']:.2f} ({coin['change']:.2f}%)\n"
        bot.send_message(chat_id, msg)
        bot.send_message(chat_id, "What would you like to do next?", reply_markup=main_menu())
        
    elif call.data == "portfolio":
        holdings = db.get_portfolio(chat_id)
        if not holdings:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("➕ Add Holding", callback_data="add_holding"))
            markup.add(InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu"))
            bot.send_message(chat_id, "You have no holdings tracked. Add one?", reply_markup=markup)
        else:
            bot.send_message(chat_id, "Calculating portfolio value... please wait.")
            report = helpers.format_portfolio(holdings, config['CMC_API_KEY'])
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("✏️ Edit/Add", callback_data="add_holding"))
            markup.add(InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu"))
            bot.send_message(chat_id, report, parse_mode='Markdown', reply_markup=markup)

    elif call.data == "news":
        news = helpers.fetch_news()
        msg = "📰 **Latest Crypto News**\n\n"
        for item in news:
            msg += f"• [{item['title']}]({item['link']})\n"
        bot.send_message(chat_id, msg, parse_mode='Markdown', disable_web_page_preview=True)
        bot.send_message(chat_id, "What would you like to do next?", reply_markup=main_menu())

    elif call.data == "view_alerts":
        alerts = db.get_user_alerts(chat_id)
        if not alerts:
             bot.send_message(chat_id, "🔕 You have no active alerts.")
             bot.send_message(chat_id, "What would you like to do next?", reply_markup=main_menu())
        else:
            msg = "📋 **Your Active Alerts**\n\n"
            for alert in alerts:
                # Add current price context maybe? Or just keep simple.
                msg += f"• **{alert['symbol']}** {alert['condition']} ${alert['target_price']:,.2f}\n"
            
            # Add a button to clear all? Or specific? Keeping simple for now.
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🗑️ Clear All Alerts", callback_data="clear_alerts"))
            bot.send_message(chat_id, msg, parse_mode='Markdown', reply_markup=markup)

    elif call.data == "clear_alerts":
        # Delete logic
        db.delete_user_alerts(chat_id)
        bot.send_message(chat_id, "✅ All alerts cleared.")
        bot.send_message(chat_id, "What would you like to do next?", reply_markup=main_menu())

    elif call.data == "alert":
        msg = bot.send_message(chat_id, "Enter the symbol you want to watch (e.g. BTC):")
        bot.register_next_step_handler(msg, process_alert_symbol_step)

    elif call.data == "convert":
        msg = bot.send_message(chat_id, "Enter amount and symbol to convert (e.g. 100 USD to BTC or 0.5 ETH to USD)\n*Currently supports Crypto -> USD value mainly*.\nEnter: `1 BTC` to see price.")
        bot.register_next_step_handler(msg, process_convert_step)

    elif call.data == "add_holding":
        msg = bot.send_message(chat_id, "Enter symbol and amount (e.g. BTC 0.5):")
        bot.register_next_step_handler(msg, process_portfolio_add_step)
        
    elif call.data == "help":
        bot.send_message(chat_id, "Use the menu buttons to navigate. Data provided by CoinMarketCap.")

# --- Step Handlers ---

def process_alert_symbol_step(message):
    try:
        symbol = message.text.upper()
        user_data = {'symbol': symbol}
        msg = bot.reply_to(message, f"Watching {symbol}. Alert price? (e.g. 95000)")
        bot.register_next_step_handler(msg, process_alert_price_step, user_data)
    except Exception as e:
        bot.reply_to(message, "Error. Try again.")

def process_alert_price_step(message, user_data):
    try:
        text = message.text.strip().replace(',', '.').replace('$', '')
        price = float(text)
        user_data['price'] = price
        
        # Determine condition automatically based on current price?
        # Or ask user? User request: "Alert me if BTC drops below..."
        # Let's ask condition.
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("Above 📈", callback_data=f"cond_above_{price}_{user_data['symbol']}"))
        keyboard.add(InlineKeyboardButton("Below 📉", callback_data=f"cond_below_{price}_{user_data['symbol']}"))
        
        bot.reply_to(message, f"Alert when price is Above or Below ${price}?", reply_markup=keyboard)
    except ValueError:
        bot.reply_to(message, "Invalid price. Please enter a number.")

def process_convert_step(message):
    try:
        parts = message.text.strip().replace(',', '.').replace('$', '').split()
        if len(parts) >= 2:
            try:
                amount = float(parts[0])
            except ValueError:
                # Handle case where amount might be second or attached to symbol (not perfect but robust)
                 bot.reply_to(message, "Could not understand amount. Try format: 0.5 BTC")
                 return
            
            symbol = parts[1].upper() # Assuming second part is symbol
            # Revisit if symbols like "$BTC" are passed.
            symbol = symbol.replace('$', '')
            total, rate = helpers.convert_currency(amount, symbol, config['CMC_API_KEY'])
            if total:
                bot.reply_to(message, f"💱 {amount} {symbol} = ${total:,.2f} USD\n(Rate: ${rate:,.2f})")
                bot.send_message(message.chat.id, "What would you like to do next?", reply_markup=main_menu())
            else:
                bot.reply_to(message, "Could not fetch conversion.")
        else:
            bot.reply_to(message, "Format invalid. Try: 0.5 BTC")
    except Exception:
        bot.reply_to(message, "Error converting.")

def process_portfolio_add_step(message):
    try:
        parts = message.text.strip().replace(',', '.').replace('$', '').split()
        symbol = parts[0].upper()
        amount = float(parts[1])
        
        db.update_portfolio(message.chat.id, symbol, amount)
        bot.reply_to(message, f"✅ Updated portfolio: {amount} {symbol}")
        bot.send_message(message.chat.id, "What would you like to do next?", reply_markup=main_menu())
    except Exception:
        bot.reply_to(message, "Invalid format. Use: SYMBOL AMOUNT (e.g. BTC 0.5)")



if __name__ == "__main__":
    print("Bot is running with DB and Menu...")
    bot.infinity_polling()
