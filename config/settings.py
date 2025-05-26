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
    'rsi_buy_threshold': 45,
    'rsi_sell_threshold': 65,
    
    # Gestión de riesgo
    'take_profit': 0.5,      # en porcentaje
    'stop_loss': 0.2,        # en porcentaje

    # Cantidad base (solo usada si no se usa cálculo dinámico)
    'quantity': 0.001,

    # Factor para calcular cantidad mínima automática
    'quantity_factor': 1.1,  # ✅ Aumenta 10% sobre el mínimo notional

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
