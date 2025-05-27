from binance.client import Client
from config.settings import API_KEY, SECRET_KEY, TESTNET, PARAMS
import logging

client = Client(API_KEY, SECRET_KEY, testnet=TESTNET)

def calcular_cantidad_valida(symbol, precio_actual):
    try:
        info = client.get_symbol_info(symbol)
        min_notional = None
        step_size = 0.000001  # valor por defecto

        for f in info["filters"]:
            if f["filterType"] in ["MIN_NOTIONAL", "NOTIONAL"]:
                if "minNotional" in f:
                    min_notional = float(f["minNotional"])
                elif "notional" in f:
                    min_notional = float(f["notional"])
            if f["filterType"] == "LOT_SIZE":
                step_size = float(f["stepSize"])

        # 🚨 Fallback manual para BTC si no se encuentra el filtro
        if symbol == "BTCUSDT" and not min_notional:
            min_notional = 10.0  # forzamos un mínimo de $10

        if not min_notional:
            logging.warning(f"[{symbol}] No se encontró filtro de notional.")
            return None

        # Calcular cantidad con factor
        cantidad = (min_notional / precio_actual) * PARAMS.get("quantity_factor", 1.0)

        # Redondear a múltiplo de step_size
        precision = len(str(step_size).split(".")[1])
        cantidad = round(cantidad, precision)

        total = round(cantidad * precio_actual, 2)
        logging.info(f"[{symbol}] Cantidad calculada: {cantidad} | Valor estimado: {total} USDT")

        return cantidad

    except Exception as e:
        logging.error(f"[{symbol}] Error al calcular cantidad mínima: {e}")
        return None
