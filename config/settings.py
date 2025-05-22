import os
from dotenv import load_dotenv

load_dotenv()

PARAMS = {
    'symbol': 'BTCUSDT',
    'timeframe': '5m',
    'ema_short': 9,
    'ema_long': 21,
    'rsi_window': 14,
    'rsi_buy_threshold': 45,
    'rsi_sell_threshold': 55,
    'take_profit': 0.3,
    'stop_loss': 0.2,
    'quantity': 0.001,
    'sleep_time': 30,
    'use_oco': True,
}

API_KEY = os.getenv("API_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")
TESTNET = os.getenv("TESTNET", "True").lower() == "true"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
