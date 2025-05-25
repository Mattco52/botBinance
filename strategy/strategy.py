from config.settings import PARAMS
from data.market_data import obtener_datos, obtener_precio_actual
from execution.orders import comprar, vender, verificar_cierre_oco
from execution.state_manager import cargar_estado, guardar_estado
import logging
from datetime import datetime, timedelta

# Almacena el RSI anterior por símbolo
rsi_anterior_dict = {}

def ejecutar_estrategia(symbol):
    estado = cargar_estado(symbol)
    rsi_anterior = rsi_anterior_dict.get(symbol, None)

    ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logging.info(f"[{ahora}] [{symbol}] Ejecutando estrategia...")

    verificar_cierre_oco(symbol, estado)

    precio_actual = obtener_precio_actual(symbol)
    fila_ant, fila_act = obtener_datos(symbol)
    if fila_act is None:
        logging.error(f"[{ahora}] [{symbol}] No se pudieron obtener los indicadores.")
        return

    ema_ok = fila_act['ema9'] > fila_act['ema21']
    rsi = fila_act['rsi']
    rsi_prev = fila_ant['rsi']

    timestamp_raw = fila_act.name if hasattr(fila_act, 'name') else None
    if isinstance(timestamp_raw, int):
        vela_timestamp = datetime.utcfromtimestamp(timestamp_raw / 1000)
    else:
        vela_timestamp = timestamp_raw or datetime.utcnow()
    vela_actual_str = vela_timestamp.strftime("%Y-%m-%d %H:%M:%S")

    ultima_compra = estado.get("ultima_compra_timestamp")
    ultima_venta = estado.get("ultima_venta_timestamp")

    cooldown_termina = None
    if ultima_venta:
        try:
            cooldown_termina = datetime.strptime(ultima_venta, "%Y-%m-%d %H:%M:%S") + timedelta(minutes=3)
        except Exception:
            cooldown_termina = None

    ahora_dt = datetime.utcnow()

    puede_comprar = (
        not estado["estado"]
        and ema_ok
        and rsi < PARAMS['rsi_buy_threshold']
        and (not ultima_compra or ultima_compra < vela_actual_str)
        and (not cooldown_termina or ahora_dt >= cooldown_termina)
    )

    if puede_comprar:
        comprar(precio_actual, rsi, symbol, estado)

    elif estado["estado"] and estado["cantidad_acumulada"] > 0:
        ganancia = round((precio_actual - estado["precio_entrada_promedio"]) * estado["cantidad_acumulada"], 2)
        if rsi > PARAMS['rsi_sell_threshold'] and ganancia >= 0.2:
            vender(precio_actual, rsi, symbol, estado, "RSI sobre umbral con ganancia")
        elif rsi < 60 and rsi_prev > 60 and ganancia >= 0.2:
            vender(precio_actual, rsi, symbol, estado, "RSI perdió momentum con ganancia")

    if estado["estado"] and not PARAMS['use_oco']:
        entrada = estado["precio_entrada_promedio"]
        cantidad = estado["cantidad_acumulada"]

        tp = entrada * (1 + PARAMS['take_profit'] / 100)

        if PARAMS.get('use_trailing_stop', False):
            if precio_actual > estado["precio_maximo"]:
                estado["precio_maximo"] = precio_actual

            trailing_stop = estado["precio_maximo"] * (1 - PARAMS['trailing_stop_pct'] / 100)

            if precio_actual <= trailing_stop:
                vender(precio_actual, rsi, symbol, estado, "Trailing Stop alcanzado")

        else:
            sl = entrada * (1 - PARAMS['stop_loss'] / 100)
            if precio_actual <= sl:
                vender(precio_actual, rsi, symbol, estado, "Stop Loss alcanzado")

        if precio_actual >= tp:
            vender(precio_actual, rsi, symbol, estado, "Take Profit alcanzado")

    else:
        logging.info(f"[{ahora}] [{symbol}] ⚪ Sin señal clara | EMA OK: {ema_ok} | RSI: {rsi:.2f}")

    rsi_anterior_dict[symbol] = rsi
    guardar_estado(symbol, estado)
