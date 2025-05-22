from config.settings import PARAMS
from data.market_data import obtener_datos, obtener_precio_actual
from execution.orders import comprar, vender, verificar_cierre_oco, estado as estado_bot
import logging
from datetime import datetime

rsi_anterior = None

def ejecutar_estrategia():
    global rsi_anterior

    ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logging.info(f"[{ahora}] Ejecutando estrategia...")

    verificar_cierre_oco()

    precio_actual = obtener_precio_actual()
    fila_ant, fila_act = obtener_datos()
    if fila_act is None:
        logging.error(f"[{ahora}] No se pudieron obtener los indicadores. Saliendo.")
        return

    ema_ok = fila_act['ema9'] > fila_act['ema21']
    rsi = fila_act['rsi']
    rsi_prev = fila_ant['rsi']

from datetime import datetime

# Obtener timestamp de la vela actual desde el índice o columna
timestamp_raw = fila_act.name if hasattr(fila_act, 'name') else None

# Si es un entero, convertir a datetime
if isinstance(timestamp_raw, int):
    vela_timestamp = datetime.utcfromtimestamp(timestamp_raw / 1000)
else:
    vela_timestamp = timestamp_raw or datetime.utcnow()

vela_actual_str = vela_timestamp.strftime("%Y-%m-%d %H:%M:%S")


    # Obtener timestamp de la última compra
    ultima_compra = estado_bot.get("ultima_compra_timestamp")

    # CONDICIÓN DE COMPRA
    puede_comprar = (
        not comprar.estado()
        and ema_ok
        and rsi < PARAMS['rsi_buy_threshold']
        and (not ultima_compra or ultima_compra < vela_actual_str)
    )

    if puede_comprar:
        comprar(precio_actual, rsi)

    # CONDICIÓN DE VENTA
    elif estado_bot["estado"] and estado_bot["cantidad_acumulada"] > 0:
        if rsi > PARAMS['rsi_sell_threshold']:
            vender(precio_actual, rsi, "RSI sobre umbral de venta")
        elif rsi < 60 and rsi_prev > 60:
            vender(precio_actual, rsi, "RSI perdió momentum")

    else:
        logging.info(
            f"[{ahora}] ⚪ Sin señal clara | EMA9 > EMA21: {ema_ok} | RSI: {rsi:.2f}"
        )

    rsi_anterior = rsi
