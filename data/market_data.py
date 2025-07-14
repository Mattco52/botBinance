import pandas as pd
import logging
from binance.client import Client
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from config.settings import API_KEY, SECRET_KEY, TESTNET, PARAMS

client = Client(API_KEY, SECRET_KEY, testnet=TESTNET)

def obtener_datos(symbol, timeframe):
    try:
        klines = client.get_historical_klines(
            symbol=symbol,
            interval=timeframe,
            start_str="24 hours ago UTC"
        )
    except Exception as e:
        logging.error(f"[{symbol}] Error al obtener klines: {e}")
        return None

    df = pd.DataFrame(klines, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base', 'taker_buy_quote', 'ignore'
    ])

    # Validación de columnas clave antes de convertir
    for col in ['close', 'high', 'low']:
        if not pd.to_numeric(df[col], errors='coerce').notnull().all():
            logging.error(f"[{symbol}] ❌ Datos corruptos en columna '{col}': {df[col].to_list()}")
            return None

    # Conversión segura
    df['close'] = pd.to_numeric(df['close'], errors='coerce')
    df['high'] = pd.to_numeric(df['high'], errors='coerce')
    df['low'] = pd.to_numeric(df['low'], errors='coerce')

    # Calcular indicadores
    df['ema_short'] = EMAIndicator(df['close'], window=PARAMS['ema_short']).ema_indicator()
    df['ema_long'] = EMAIndicator(df['close'], window=PARAMS['ema_long']).ema_indicator()
    df['rsi'] = RSIIndicator(df['close'], window=PARAMS['rsi_window']).rsi()

    if df.empty:
        logging.warning(f"[{symbol}] No hay datos en el DataFrame.")
        return None

    return df
