import os
from dotenv import load_dotenv

load_dotenv()

# Parámetros del bot
PARAMS = {
    'symbol': 'BTCUSDT',
    'timeframe': '5m',
    'ema_short': 9,
    'ema_long': 21,
    'rsi_window': 14,
    'rsi_buy_threshold': 40,
    'rsi_sell_threshold': 60,
    
    # Gestión de riesgo
    'take_profit': 0.5,      # en porcentaje
    'stop_loss': 0.2,        # en porcentaje
    'quantity': 0.001,
    
    # Tiempo entre ciclos
    'sleep_time': 30,
    
    # Orden OCO
    'use_oco': False,  # No usar OCO en testnet, usar lógica simulada en su lugar
    
    # Trailing Stop dinámico (solo si use_oco == False)
    'use_trailing_stop': True,
    'trailing_stop_pct': 0.5  # % bajo el máximo alcanzado
}

# Claves API y entorno
API_KEY = os.getenv("API_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")
TESTNET = os.getenv("TESTNET", "True").lower() == "true"

# Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
