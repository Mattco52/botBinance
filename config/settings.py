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
    'rsi_buy_threshold': 45,       # Si RSI < 45, comprar
    'rsi_sell_threshold': 65,      # Si RSI > 65, considerar vender

    # Gestión de riesgo
    'take_profit': 1.0,            # 1% de ganancia para Take Profit
    'stop_loss': 0.5,              # 0.5% de pérdida máxima

    # Cantidad base (solo usada si no se usa cálculo dinámico)
    'quantity': 0.001,

    # Factor para cálculo automático basado en minNotional
    'quantity_factor': 1.2,        # 20% por encima del mínimo requerido

    # Tiempo entre ciclos de estrategia
    'sleep_time': 30,

    # Uso de orden OCO (usualmente no disponible en testnet)
    'use_oco': False,

    # Trailing Stop (cuando no se usa OCO)
    'use_trailing_stop': True,
    'trailing_stop_pct': 0.3       # 0.3% por debajo del máximo alcanzado
}

# Claves API y entorno (Render, local o Heroku)
API_KEY = os.getenv("API_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")
TESTNET = os.getenv("TESTNET", "True").lower() == "true"

# Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
