from binance.client import Client
from config.settings import API_KEY, SECRET_KEY, TESTNET

client = Client(API_KEY, SECRET_KEY, testnet=TESTNET)

def calcular_cantidad_valida(symbol, precio_actual):
    try:
        info = client.get_symbol_info(symbol)
        min_notional = None
        step_size = 0.000001  # valor por defecto

        for f in info["filters"]:
            if f["filterType"] == "MIN_NOTIONAL":
                min_notional = float(f["notional"])
            if f["filterType"] == "LOT_SIZE":
                step_size = float(f["stepSize"])

        if not min_notional:
            return None

        cantidad = min_notional / precio_actual

        # Redondear a múltiplo de step_size
        precision = len(str(step_size).split(".")[1])
        cantidad = round(cantidad, precision)

        return cantidad

    except Exception as e:
        print(f"[{symbol}] Error al calcular cantidad mínima: {e}")
        return None
