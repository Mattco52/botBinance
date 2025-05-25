from config.settings import PARAMS
from data.market_data import obtener_datos, obtener_precio_actual
from execution.orders import comprar, vender, verificar_cierre_oco, estado as estado_bot
import logging
from datetime import datetime, timedelta

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

    # Obtener timestamp de la vela
    timestamp_raw = fila_act.name if hasattr(fila_act, 'name') else None
    if isinstance(timestamp_raw, int):
        vela_timestamp = datetime.utcfromtimestamp(timestamp_raw / 1000)
    else:
        vela_timestamp = timestamp_raw or datetime.utcnow()
    vela_actual_str = vela_timestamp.strftime("%Y-%m-%d %H:%M:%S")

    ultima_compra = estado_bot.get("ultima_compra_timestamp")
    ultima_venta = estado_bot.get("ultima_venta_timestamp")

    cooldown_termina = None
    if ultima_venta:
        try:
            cooldown_termina = datetime.strptime(ultima_venta, "%Y-%m-%d %H:%M:%S") + timedelta(minutes=3)
        except Exception:
            cooldown_termina = None

    ahora_dt = datetime.utcnow()

    puede_comprar = (
        not comprar.estado()
        and ema_ok
        and rsi < PARAMS['rsi_buy_threshold']
        and (not ultima_compra or ultima_compra < vela_actual_str)
        and (not cooldown_termina or ahora_dt >= cooldown_termina)
    )

    if puede_comprar:
        comprar(precio_actual, rsi)

    # VENTA por RSI con ganancia mínima
    elif estado_bot["estado"] and estado_bot["cantidad_acumulada"] > 0:
        ganancia = round((precio_actual - estado_bot["precio_entrada_promedio"]) * estado_bot["cantidad_acumulada"], 2)
        if rsi > PARAMS['rsi_sell_threshold'] and ganancia >= 0.2:
            vender(precio_actual, rsi, "RSI sobre umbral de venta con ganancia")
        elif rsi < 60 and rsi_prev > 60 and ganancia >= 0.2:
            vender(precio_actual, rsi, "RSI perdió momentum con ganancia")

    # SIMULACIÓN TP / SL / TRAILING
    if estado_bot["estado"] and not PARAMS['use_oco']:
        entrada = estado_bot["precio_entrada_promedio"]
        cantidad = estado_bot["cantidad_acumulada"]

        tp = entrada * (1 + PARAMS['take_profit'] / 100)

        if PARAMS.get('use_trailing_stop', False):
            if precio_actual > estado_bot["precio_maximo"]:
                estado_bot["precio_maximo"] = precio_actual

            trailing_stop = estado_bot["precio_maximo"] * (1 - PARAMS['trailing_stop_pct'] / 100)

            if precio_actual <= trailing_stop:
                vender(precio_actual, rsi, "Trailing Stop alcanzado")

        else:
            sl = entrada * (1 - PARAMS['stop_loss'] / 100)
            if precio_actual <= sl:
                vender(precio_actual, rsi, "Stop Loss alcanzado")

        if precio_actual >= tp:
            vender(precio_actual, rsi, "Take Profit alcanzado")

    else:
        logging.info(f"[{ahora}] ⚪ Sin señal clara | EMA9 > EMA21: {ema_ok} | RSI: {rsi:.2f}")

    rsi_anterior = rsi
