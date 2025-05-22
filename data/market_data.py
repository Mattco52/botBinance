import pandas as pd
from binance.client import Client
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from config.settings import PARAMS, API_KEY, SECRET_KEY, TESTNET
import logging

client = Client(API_KEY, SECRET_KEY, testnet=TESTNET)

def obtener_datos():
    try:
        klines = client.get_historical_klines(
            symbol=PARAMS['symbol'],
            interval=Client.KLINE_INTERVAL_5MINUTE,
            start_str="24 hours ago UTC"
        )
    except Exception as e:
        logging.error(f"Error al obtener klines de Binance: {e}")
        return None, None

    df = pd.DataFrame(klines, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base', 'taker_buy_quote', 'ignore'
    ])
    df['close'] = pd.to_numeric(df['close'])
    df['high'] = pd.to_numeric(df['high'])
    df['low'] = pd.to_numeric(df['low'])

    df['ema9'] = EMAIndicator(df['close'], window=PARAMS['ema_short']).ema_indicator()
    df['ema21'] = EMAIndicator(df['close'], window=PARAMS['ema_long']).ema_indicator()
    df['rsi'] = RSIIndicator(df['close'], window=PARAMS['rsi_window']).rsi()

    return df.iloc[-2], df.iloc[-1]

def obtener_precio_actual():
    return float(client.get_symbol_ticker(symbol=PARAMS['symbol'])['price'])
