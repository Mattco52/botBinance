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

        # Validar que cada kline tenga exactamente 12 elementos
        klines_validos = [k for k in klines if isinstance(k, list) and len(k) == 12]

        df = pd.DataFrame(klines_validos, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base', 'taker_buy_quote', 'ignore'
        ])

    except Exception as e:
        logging.error(f"[{symbol}] Error al obtener klines: {e}")
        return None

    # Convertir columnas a numérico y eliminar NaNs
    for col in ['close', 'high', 'low']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    df.dropna(subset=['close', 'high', 'low'], inplace=True)

    # Validar cantidad mínima de datos
    min_req = max(PARAMS['ema_short'], PARAMS['ema_long'], PARAMS['rsi_window']) + 1
    if len(df) < min_req:
        logging.warning(f"[{symbol}] No hay suficientes datos después del filtrado.")
        return None

    # Calcular indicadores
    df['ema_short'] = EMAIndicator(df['close'], window=PARAMS['ema_short']).ema_indicator()
    df['ema_long'] = EMAIndicator(df['close'], window=PARAMS['ema_long']).ema_indicator()
    df['rsi'] = RSIIndicator(df['close'], window=PARAMS['rsi_window']).rsi()

    return df
