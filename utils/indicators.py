# utils/indicators.py

import pandas as pd

def calcular_ema(data, period=9):
    """
    Calcula la Exponential Moving Average (EMA).
    """
    return pd.Series(data).ewm(span=period, adjust=False).mean().tolist()

def calcular_rsi(data, period=14):
    """
    Calcula el Relative Strength Index (RSI).
    """
    series = pd.Series(data)
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi.fillna(0).tolist()