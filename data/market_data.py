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

        # Convertir y validar cada línea de datos
        datos_limpios = []
        for k in klines:
            if isinstance(k, list) and len(k) == 12:
                try:
                    fila = [
                        int(k[0]), float(k[1]), float(k[2]), float(k[3]),
                        float(k[4]), float(k[5]), int(k[6]), float(k[7]),
                        int(k[8]), float(k[9]), float(k[10]), str(k[11])
                    ]
                    datos_limpios.append(fila)
                except (ValueError, TypeError):
                    continue

        df = pd.DataFrame(datos_limpios, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base', 'taker_buy_quote', 'ignore'
        ])

    except Exception as e:
        logging.error(f"[{symbol}] Error al obtener klines: {e}")
        return None

    if df.empty:
        logging.warning(f"[{symbol}] No hay datos válidos para {symbol}.")
        return None

    # Calcular indicadores
    df['ema_short'] = EMAIndicator(df['close'], window=PARAMS['ema_short']).ema_indicator()
    df['ema_long'] = EMAIndicator(df['close'], window=PARAMS['ema_long']).ema_indicator()
    df['rsi'] = RSIIndicator(df['close'], window=PARAMS['rsi_window']).rsi()

    return df
