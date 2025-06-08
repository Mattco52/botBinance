import logging
import pandas as pd
from binance.client import Client
from config.settings import API_KEY, SECRET_KEY, TESTNET, PARAMS

# Cliente de Binance
client = Client(API_KEY, SECRET_KEY, testnet=TESTNET)

# EMA con pandas
def calcular_ema(serie: pd.Series, window: int) -> pd.Series:
    return serie.ewm(span=window, adjust=False).mean()

# RSI con pandas
def calcular_rsi(series: pd.Series, window: int) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=window).mean()
    avg_loss = loss.rolling(window=window).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# Verifica si el total cumple con el mínimo notional
def cumple_min_notional(symbol: str, precio: float, cantidad: float) -> bool:
    try:
        info = client.get_symbol_info(symbol)
        min_notional = None
        for f in info["filters"]:
            if f["filterType"] in ["MIN_NOTIONAL", "NOTIONAL"]:
                min_notional = float(f.get("minNotional") or f.get("notional"))
                break

        if not min_notional:
            logging.warning(f"[{symbol}] No se encontró filtro de NOTIONAL.")
            return False

        total = precio * cantidad
        return total >= min_notional

    except Exception as e:
        logging.error(f"[{symbol}] Error al verificar notional: {e}")
        return False

# Calcula la cantidad válida mínima según precio y filtros
def calcular_cantidad_valida(symbol: str, precio_actual: float) -> float | None:
    try:
        info = client.get_symbol_info(symbol)

        min_notional = None
        step_size = 0.000001
        min_qty = 0.000001

        for f in info["filters"]:
            if f["filterType"] in ["MIN_NOTIONAL", "NOTIONAL"] and not min_notional:
                min_notional = float(f.get("minNotional") or f.get("notional"))
            if f["filterType"] == "LOT_SIZE":
                step_size = float(f["stepSize"])
                min_qty = float(f["minQty"])

        # Fallback para BTCUSDT si no tiene notional
        if symbol == "BTCUSDT" and not min_notional:
            min_notional = 10.0

        if not min_notional:
            logging.warning(f"[{symbol}] No se encontró filtro de notional.")
            return None

        # ✅ Calcular cantidad con factor configurado
        cantidad = (min_notional / precio_actual) * PARAMS.get("quantity_factor", 1.0)

        # ✅ Redondear correctamente la cantidad según el step_size
        step_str = f"{step_size:.20f}".rstrip("0")
        precision = len(step_str.split(".")[1]) if "." in step_str else 0
        cantidad = round(cantidad, precision)

        # Validar cantidad mínima
        if cantidad < min_qty:
            cantidad = min_qty

        total = round(cantidad * precio_actual, 2)

        logging.info(f"[DEBUG] {symbol} | Precio: {precio_actual:.2f} | Cantidad: {cantidad} | Total: {total} | Mínimo: {min_notional}")

        # Forzar mínimo para BTCUSDT si sigue siendo bajo
        if symbol == "BTCUSDT" and total < min_notional:
            cantidad = round((min_notional + 1) / precio_actual, precision)
            total = round(cantidad * precio_actual, 2)
            logging.info(f"[BTCUSDT] Forzando cantidad a: {cantidad} | Nuevo total: {total}")

        if total < min_notional:
            logging.warning(f"[{symbol}] Total insuficiente: {total} < mínimo {min_notional}")
            return None

        logging.info(f"[{symbol}] Cantidad calculada: {cantidad} | Total: {total} USDT")
        return cantidad

    except Exception as e:
        logging.error(f"[{symbol}] Error al calcular cantidad mínima: {e}")
        return None