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

        # Validar que cada kline tenga al menos 6 valores necesarios
        klines_filtrados = [k for k in klines if len(k) >= 6]

        df = pd.DataFrame(klines_filtrados, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base', 'taker_buy_quote', 'ignore'
        ])

    except Exception as e:
        logging.error(f"[{symbol}] Error al obtener klines: {e}")
        return None

    # Convertir a numéricos solo las columnas necesarias
    for col in ['close', 'high', 'low']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    df.dropna(subset=['close', 'high', 'low'], inplace=True)

    # Validar que haya suficientes datos para indicadores
    min_required = max(PARAMS['ema_short'], PARAMS['ema_long'], PARAMS['rsi_window']) + 1
    if len(df) < min_required:
        logging.error(f"[{symbol}] ❌ Insuficientes datos válidos tras limpieza: {len(df)} filas")
        return None

    # Calcular indicadores técnicos
    df['ema_short'] = EMAIndicator(df['close'], window=PARAMS['ema_short']).ema_indicator()
    df['ema_long'] = EMAIndicator(df['close'], window=PARAMS['ema_long']).ema_indicator()
    df['rsi'] = RSIIndicator(df['close'], window=PARAMS['rsi_window']).rsi()

    return df
