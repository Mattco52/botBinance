# utils/data_fetcher.py
from binance.client import Client
from config.settings import API_KEY, SECRET_KEY, TESTNET

client = Client(API_KEY, SECRET_KEY, testnet=TESTNET)

def obtener_datos(symbol, interval, limit=100):
    """
    Descarga datos OHLCV de Binance y devuelve una lista de cierres.
    """
    klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
    cierres = [float(k[4]) for k in klines]  # k[4] es el precio de cierre
    return cierres