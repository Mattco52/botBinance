from config.settings import PARAMS
from data.market_data import obtener_datos, obtener_precio_actual
from execution.orders import comprar, vender, verificar_cierre_oco
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

    if not comprar.estado and ema_ok and rsi < PARAMS['rsi_buy_threshold']:
        comprar(precio_actual, rsi)

    elif comprar.estado:
        if rsi > PARAMS['rsi_sell_threshold']:
            vender(precio_actual, rsi, "RSI sobre umbral de venta")
        elif rsi < 60 and rsi_prev > 60:
            vender(precio_actual, rsi, "RSI perdió momentum")
    else:
        logging.info(f"[{ahora}] ⚪ Sin señal clara | EMA9 > EMA21: {ema_ok} | RSI: {rsi:.2f}")

    rsi_anterior = rsi
