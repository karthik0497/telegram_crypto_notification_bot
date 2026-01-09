import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from dotenv import load_dotenv
import logging

load_dotenv()

# Database Config
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "telegram_bot_db")
DB_USER = os.getenv("DB_USER", "bot_user")
DB_PASS = os.getenv("DB_PASS", "bot_password")
DB_PORT = os.getenv("DB_PORT", "5432")

def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            port=DB_PORT
        )
        return conn
    except Exception as e:
        logging.error(f"Database connection error: {e}")
        return None

def add_alert(user_id, symbol, price, condition):
    conn = get_db_connection()
    if not conn:
        raise ConnectionError("Could not connect to database")
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO alerts (user_id, symbol, target_price, condition) VALUES (%s, %s, %s, %s)", (user_id, symbol, price, condition))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def init_db():
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to DB. Ensure Postgres is running.")
        return
    
    try:
        cur = conn.cursor()
        
        # Table: Users
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Table: Alerts
        cur.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                symbol TEXT,
                target_price DECIMAL,
                condition TEXT, -- 'above' or 'below'
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );
        """)

        # Table: Holdings (Portfolio)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS holdings (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                symbol TEXT,
                amount DECIMAL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                UNIQUE(user_id, symbol)
            );
        """)

        # Table: Interaction Logs
        cur.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                command TEXT,
                message TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        conn.commit()
        cur.close()
        conn.close()
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Error initializing DB: {e}")

# Helper Functions

def log_to_db(user_id, command, message):
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("INSERT INTO logs (user_id, command, message) VALUES (%s, %s, %s)", (user_id, command, message))
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            logging.error(f"Log DB Error: {e}")

def add_user(user_id, username):
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("INSERT INTO users (user_id, username) VALUES (%s, %s) ON CONFLICT (user_id) DO NOTHING", (user_id, username))
            conn.commit()
            cur.close()
            conn.close()
        except Exception:
            pass



def get_alerts():
    conn = get_db_connection()
    if conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM alerts")
        alerts = cur.fetchall()
        conn.close()
        return alerts
    return []

def get_user_alerts(user_id):
    conn = get_db_connection()
    if conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM alerts WHERE user_id = %s", (user_id,))
        alerts = cur.fetchall()
        conn.close()
        return alerts
    return []

def delete_alert(alert_id):
    conn = get_db_connection()
    if conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM alerts WHERE id = %s", (alert_id,))
        conn.commit()
        conn.close()

def delete_user_alerts(user_id):
    conn = get_db_connection()
    if conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM alerts WHERE user_id = %s", (user_id,))
        conn.commit()
        conn.close()

def update_portfolio(user_id, symbol, amount):
    conn = get_db_connection()
    if conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO holdings (user_id, symbol, amount) 
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, symbol) 
            DO UPDATE SET amount = EXCLUDED.amount, updated_at = CURRENT_TIMESTAMP
        """, (user_id, symbol, amount))
        conn.commit()
        conn.close()

def get_portfolio(user_id):
    conn = get_db_connection()
    if conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT symbol, amount FROM holdings WHERE user_id = %s", (user_id,))
        holdings = cur.fetchall()
        conn.close()
        return holdings
    return []
