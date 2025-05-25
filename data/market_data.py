import pandas as pd
from binance.client import Client
from config.settings import API_KEY, SECRET_KEY, TESTNET, PARAMS
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
import logging

client = Client(API_KEY, SECRET_KEY, testnet=TESTNET)

def obtener_datos(symbol):
    try:
        klines = client.get_historical_klines(
            symbol=symbol,
            interval=PARAMS['timeframe'],
            start_str="24 hours ago UTC"
        )
    except Exception as e:
        logging.error(f"[{symbol}] Error al obtener klines: {e}")
        return None, None

    df = pd.DataFrame(klines, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base', 'taker_buy_quote', 'ignore'
    ])

    df['close'] = pd.to_numeric(df['close'])
    df['high'] = pd.to_numeric(df['high'])
    df['low'] = pd.to_numeric(df['low'])

    # Calcular indicadores técnicos
    df['ema9'] = EMAIndicator(df['close'], window=PARAMS['ema_short']).ema_indicator()
    df['ema21'] = EMAIndicator(df['close'], window=PARAMS['ema_long']).ema_indicator()
    df['rsi'] = RSIIndicator(df['close'], window=PARAMS['rsi_window']).rsi()

    # Asegurar que hay suficientes datos para operar
    if len(df) < 2:
        logging.warning(f"[{symbol}] No hay suficientes datos para operar.")
        return None, None

    return df.iloc[-2], df.iloc[-1]

def obtener_precio_actual(symbol):
    try:
        precio = float(client.get_symbol_ticker(symbol=symbol)['price'])
        return precio
    except Exception as e:
        logging.error(f"[{symbol}] Error al obtener precio actual: {e}")
        return 0.0
