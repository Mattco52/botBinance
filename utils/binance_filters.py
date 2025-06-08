import logging
import pandas as pd
from decimal import Decimal, ROUND_DOWN
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
        step_size = "0.000001"
        min_qty = "0.000001"

        for f in info["filters"]:
            if f["filterType"] in ["MIN_NOTIONAL", "NOTIONAL"] and not min_notional:
                min_notional = float(f.get("minNotional") or f.get("notional"))
            if f["filterType"] == "LOT_SIZE":
                step_size = f["stepSize"]
                min_qty = f["minQty"]

        # Fallback para BTCUSDT si no tiene notional
        if symbol == "BTCUSDT" and not min_notional:
            min_notional = 10.0

        if not min_notional:
            logging.warning(f"[{symbol}] No se encontró filtro de notional.")
            return None

        factor = Decimal(str(PARAMS.get("quantity_factor", 1.0)))
        step_dec = Decimal(step_size)
        min_qty_dec = Decimal(min_qty)
        precio_dec = Decimal(str(precio_actual))
        min_notional_dec = Decimal(str(min_notional))

        cantidad = (min_notional_dec / precio_dec) * factor
        cantidad = (cantidad // step_dec) * step_dec  # Redondeo seguro hacia abajo

        if cantidad < min_qty_dec:
            cantidad = min_qty_dec

        total = float((cantidad * precio_dec).quantize(Decimal("0.01")))
        cantidad_float = float(cantidad)

        logging.info(f"[DEBUG] {symbol} | Precio: {precio_actual:.2f} | Cantidad: {cantidad_float} | Total: {total} | Mínimo: {min_notional}")

        if total < float(min_notional):
            logging.warning(f"[{symbol}] Total insuficiente: {total} < mínimo {min_notional}")
            return None

        logging.info(f"[{symbol}] Cantidad calculada: {cantidad_float} | Total: {total} USDT")
        return cantidad_float

    except Exception as e:
        logging.error(f"[{symbol}] Error al calcular cantidad mínima: {e}")
        return None