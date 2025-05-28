from binance.client import Client
from config.settings import API_KEY, SECRET_KEY, TESTNET, PARAMS
import logging

client = Client(API_KEY, SECRET_KEY, testnet=TESTNET)

def cumple_min_notional(symbol, precio, cantidad):
    """
    Verifica si el valor total de una orden cumple con el mínimo requerido por Binance.
    """
    try:
        info = client.get_symbol_info(symbol)
        min_notional = None

        for f in info["filters"]:
            if f["filterType"] in ["MIN_NOTIONAL", "NOTIONAL"]:
                if "minNotional" in f:
                    min_notional = float(f["minNotional"])
                elif "notional" in f:
                    min_notional = float(f["notional"])
                break

        if not min_notional:
            logging.warning(f"[{symbol}] No se encontró filtro de NOTIONAL.")
            return False

        total = precio * cantidad
        return total >= min_notional

    except Exception as e:
        logging.error(f"[{symbol}] Error al verificar notional: {e}")
        return False

def calcular_cantidad_valida(symbol, precio_actual):
    """
    Calcula una cantidad válida basada en el filtro NOTIONAL y LOT_SIZE del símbolo.
    """
    try:
        info = client.get_symbol_info(symbol)
        min_notional = None
        step_size = 0.000001  # valor por defecto
        min_qty = 0.000001    # valor por defecto

        for f in info["filters"]:
            if f["filterType"] in ["MIN_NOTIONAL", "NOTIONAL"]:
                if "minNotional" in f:
                    min_notional = float(f["minNotional"])
                elif "notional" in f:
                    min_notional = float(f["notional"])
            if f["filterType"] == "LOT_SIZE":
                step_size = float(f["stepSize"])
                min_qty = float(f["minQty"])

        # Seguridad para BTC si no se encuentra el notional
        if symbol == "BTCUSDT" and not min_notional:
            min_notional = 10.0

        if not min_notional:
            logging.warning(f"[{symbol}] No se encontró filtro de notional.")
            return None

        # Factor personalizado (ajustable en PARAMS)
        cantidad = (min_notional / precio_actual) * PARAMS.get("quantity_factor", 1.0)

        # Redondeo al step_size del símbolo
        precision = len(str(step_size).split(".")[1])
        cantidad = round(cantidad, precision)

        # Asegurar mínimo de cantidad
        if cantidad < min_qty:
            cantidad = min_qty

        # Verificación final
        total = round(cantidad * precio_actual, 2)
        if total < min_notional:
            logging.warning(f"[{symbol}] Total insuficiente: {total} < mínimo {min_notional}")
            return None

        logging.info(f"[{symbol}] Cantidad calculada: {cantidad} | Total: {total} USDT")
        return cantidad

    except Exception as e:
        logging.error(f"[{symbol}] Error al calcular cantidad mínima: {e}")
        return None
