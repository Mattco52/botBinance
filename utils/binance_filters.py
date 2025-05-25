from binance.client import Client
from config.settings import API_KEY, SECRET_KEY, TESTNET

client = Client(API_KEY, SECRET_KEY, testnet=TESTNET)

def cumple_min_notional(symbol, precio, cantidad):
    try:
        info = client.get_symbol_info(symbol)
        for f in info["filters"]:
            if f["filterType"] == "MIN_NOTIONAL":
                min_notional = float(f["notional"])
                valor_orden = precio * cantidad
                return valor_orden >= min_notional
    except Exception as e:
        print(f"[{symbol}] Error al validar NOTIONAL: {e}")
    return False
