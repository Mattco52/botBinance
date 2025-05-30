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

    # 🔽 Más oportunidades de entrada y salida
    'rsi_buy_threshold': 45,     # antes 40
    'rsi_sell_threshold': 55,    # antes 60

    # Gestión de riesgo
    'take_profit': 0.4,          # antes 0.5
    'stop_loss': 0.3,            # antes 0.2
    'quantity': 0.001,           # esto será dinámico según symbol con calcular_cantidad_valida()
    'quantity_factor': 3.0,     # 🔼 nuevo: factor para calcular cantidad más grande

    # Tiempo entre ciclos
    'sleep_time': 30,

    # Orden OCO
    'use_oco': False,  # seguimos sin usar OCO

    # Trailing Stop dinámico
    'use_trailing_stop': True,
    'trailing_stop_pct': 0.25   # antes 0.5 → más sensible
}

# Claves API y entorno
API_KEY = os.getenv("API_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")
TESTNET = os.getenv("TESTNET", "True").lower() == "true"

# Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")