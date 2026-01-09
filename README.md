# Crypto Tracking Telegram Bot + Postgres

A feature-rich Telegram bot that tracks cryptocurrency prices, trends, portfolio value, and sends alerts using CoinMarketCap API and PostgreSQL.

## Features

- **🚀 Top Trending**: View top 10 gainers in the last 24h.
- **💰 Portfolio**: Track your personal holdings and total value.
- **🔔 Price Alerts**: Set persistent alerts for price thresholds (Above/Below).
- **💱 Converter**: Quick crypto-to-USD conversion calc.
- **📰 News**: Fetch latest crypto headlines.
- **💾 Database**: All data saved in PostgreSQL (users, alerts, holdings, logs).

## Prerequisites

- Docker & Docker Compose (for Database)
- Python 3.8+
- Telegram Bot Token
- CoinMarketCap API Key

## Setup & Installation

1. **Start the Database**:
   ```bash
   docker-compose up -d
   ```
   This starts a PostgreSQL container on port 5432.

2. **Install Dependencies**:
   ```bash
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure**:
   Edit `.env` with your keys.
   ```env
   TELEGRAM_BOT_TOKEN=your_token
   CMC_API_KEY=your_key
   ...
   ```

## Usage

1. **Run the Bot**:
   ```bash
   python main.py
   ```

2. **Commands**:
   - `/start` - Open the Main Menu.

## Database Access (pgAdmin)

You can connect to the database using the following credentials:

- **Host**: `localhost`
- **Port**: `5432`
- **Database Name**: `telegram_bot_db`
- **Username**: `bot_user`
- **Password**: `bot_password`

## Database Management
The bot automatically creates tables (`users`, `alerts`, `holdings`, `logs`) on first run if the DB is accessible.
