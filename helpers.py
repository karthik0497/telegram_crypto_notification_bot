import logging
import os
import requests
import feedparser
from dotenv import load_dotenv
import db

# Load environment variables
load_dotenv()

def setup_logging():
    # Only console/file logging backup; DB is primary for user interactions
    logging.basicConfig(
        filename='bot_log.log', 
        level=logging.INFO, 
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def get_config():
    return {
        'BOT_TOKEN': os.getenv('TELEGRAM_BOT_TOKEN'),
        'CMC_API_KEY': os.getenv('CMC_API_KEY'),
        'CMC_BASE_URL': "https://pro-api.coinmarketcap.com/v1"
    }

def log_interaction(user_id, text, user_status):
    logging.info(f'User ID: {user_id} - Input: {text}')
    # Log to DB
    db.log_to_db(user_id, "message", text)

def get_crypto_price(symbol, api_key):
    try:
        url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
        headers = {'X-CMC_PRO_API_KEY': api_key}
        parameters = {'symbol': symbol}

        response = requests.get(url, headers=headers, params=parameters)
        response.raise_for_status()
        data = response.json()

        crypto_info = data['data'][symbol]['quote']['USD']
        return {
            'name': data['data'][symbol]['name'],
            'price': crypto_info['price'],
            'percent_change_24h': crypto_info['percent_change_24h'],
            'volume_24h': crypto_info['volume_24h']
        }
    except Exception as e:
        logging.error(f"Error fetching data for {symbol}: {e}")
        return None

def get_top_cryptos(api_key, limit=10):
    try:
        url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
        headers = {'X-CMC_PRO_API_KEY': api_key}
        parameters = {
            'start': '1',
            'limit': str(limit),
            'sort': 'percent_change_24h',
            'sort_dir': 'desc'
        }
        response = requests.get(url, headers=headers, params=parameters)
        data = response.json()
        
        results = []
        for coin in data['data']:
            results.append({
                'name': coin['name'],
                'symbol': coin['symbol'],
                'price': coin['quote']['USD']['price'],
                'change': coin['quote']['USD']['percent_change_24h']
            })
        return results
    except Exception as e:
        logging.error(f"Error getting top cryptos: {e}")
        return []

def convert_currency(amount, symbol, api_key):
    # If conversion endpoint isn't available on free tier, use quote price * amount
    price_data = get_any_price(symbol, api_key)
    if price_data:
        total = amount * price_data['price']
        return total, price_data['price']
    return None, None

def fetch_news(query="bitcoin"):
    # Using RSS Feed for free news
    feed_url = "https://cointelegraph.com/rss"
    feed = feedparser.parse(feed_url)
    
    news_items = []
    for entry in feed.entries[:5]:
        news_items.append({
            'title': entry.title,
            'link': entry.link
        })
    return news_items

def format_portfolio(holdings, api_key):
    total_value = 0
    report = "💰 **Your Portfolio**\n\n"
    
    for item in holdings:
        symbol = item['symbol']
        amount = float(item['amount'])
        
        info = get_any_price(symbol, api_key)
        if info:
            val = amount * info['price']
            total_value += val
            report += f"• **{symbol}**: {amount} (${val:,.2f})\n"
        else:
            report += f"• **{symbol}**: {amount} (Price N/A)\n"
            
    report += f"\n**Total Value: ${total_value:,.2f}**"
    return report

def get_metal_prices():
    try:
        # Source: GoldPrice.org (Unofficial API endpoint)
        url = "https://data-asg.goldprice.org/dbXRates/USD,INR"
        # Mimic browser to avoid blocking
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        prices = {}
        troy_oz_to_gram = 31.1034768
        
        if 'items' in data:
            for item in data['items']:
                currency = item['curr']
                gold_gram = item['xauPrice'] / troy_oz_to_gram
                silver_gram = item['xagPrice'] / troy_oz_to_gram
                
                prices[currency] = {
                    'gold_oz': item['xauPrice'],
                    'silver_oz': item['xagPrice'],
                    'gold_gram': gold_gram,
                    'silver_gram': silver_gram,
                    'gold_10g': gold_gram * 10,
                    'silver_10g': silver_gram * 10
                }
            return prices
        return None
    except Exception as e:
        logging.error(f"Error getting metal prices: {e}")
        return None

def get_any_price(symbol, api_key):
    """Unified function to get price for Crypto or Metals"""
    symbol_upper = symbol.upper()
    
    # Metal Logic
    metal_map = {
        'GOLD': ('gold_gram', 'USD'),
        'SILVER': ('silver_gram', 'USD'),
        'GOLD-INR': ('gold_gram', 'INR'),
        'SILVER-INR': ('silver_gram', 'INR'),
        'XAU': ('gold_gram', 'USD'),
        'XAG': ('silver_gram', 'USD')
    }
    
    if symbol_upper in metal_map:
        key, currency = metal_map[symbol_upper]
        prices = get_metal_prices()
        if prices and currency in prices:
            price = prices[currency][key]
            return {
                'name': symbol_upper,
                'price': price,
                'percent_change_24h': 0, # Not tracking 24h change for metals in this simple API
                'volume_24h': 0
            }
        return None

    # Crypto Logic
    return get_crypto_price(symbol, api_key)
