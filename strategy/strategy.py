from config.settings import PARAMS
from data.market_data import obtener_datos, obtener_precio_actual
from execution.orders import comprar, vender, verificar_cierre_oco
from execution.state_manager import cargar_estado, guardar_estado
import logging
from datetime import datetime

rsi_anterior = {}

def ejecutar_estrategia(symbol):
    global rsi_anterior

    ahora = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    logging.info(f"[{ahora}] [{symbol}] Ejecutando estrategia...")

    # ✅ Cargar estado individual del símbolo
    estado = cargar_estado(symbol)

    # ✅ Verificar si alguna orden OCO se cerró
    verificar_cierre_oco(symbol, estado)

    # ✅ Obtener datos del mercado
    precio_actual = obtener_precio_actual(symbol)
    fila_ant, fila_act = obtener_datos(symbol)
    if fila_act is None:
        logging.warning(f"[{symbol}] No se pudieron obtener indicadores.")
        return

    ema_ok = fila_act['ema9'] > fila_act['ema21']
    rsi = fila_act['rsi']
    rsi_prev = fila_ant['rsi']

    # Obtener timestamp de la vela
    vela_timestamp = fila_act.name if hasattr(fila_act, 'name') else datetime.utcnow()
    if isinstance(vela_timestamp, int):
        vela_timestamp = datetime.utcfromtimestamp(vela_timestamp / 1000)
    vela_str = vela_timestamp.strftime('%Y-%m-%d %H:%M:%S')

    ultima_compra = estado.get("ultima_compra_timestamp")

    puede_comprar = (
        not estado["estado"]
        and ema_ok
        and rsi < PARAMS["rsi_buy_threshold"]
        and (not ultima_compra or ultima_compra < vela_str)
    )

    if puede_comprar:
        logging.info(f"[{symbol}] Condición de COMPRA detectada (RSI {rsi:.2f}, EMA OK)")
        comprar(precio_actual, rsi, symbol, estado)
        return

    # ✅ Condiciones de venta si ya hay posición
    if estado["estado"] and estado["cantidad_acumulada"] > 0:
        logging.info(f"[{symbol}] Evaluando condiciones de VENTA...")

        if rsi > PARAMS["rsi_sell_threshold"]:
            logging.info(f"[{symbol}] RSI > umbral de venta ({rsi:.2f} > {PARAMS['rsi_sell_threshold']})")
            vender(precio_actual, rsi, symbol, estado, "RSI sobre umbral de venta")
            return

        if rsi < 60 and rsi_prev > 60:
            logging.info(f"[{symbol}] RSI perdió momentum (de {rsi_prev:.2f} a {rsi:.2f})")
            vender(precio_actual, rsi, symbol, estado, "RSI perdió momentum")
            return

        # ✅ Take Profit o Trailing Stop si no es OCO
        if not PARAMS["use_oco"]:
            entrada = estado["precio_entrada_promedio"]
            cantidad = estado["cantidad_acumulada"]
            tp = entrada * (1 + PARAMS["take_profit"] / 100)

            if PARAMS["use_trailing_stop"]:
                if precio_actual > estado["precio_maximo"]:
                    estado["precio_maximo"] = precio_actual
                    guardar_estado(symbol, estado)

                trailing_stop = estado["precio_maximo"] * (1 - PARAMS["trailing_stop_pct"] / 100)
                if precio_actual <= trailing_stop:
                    logging.info(f"[{symbol}] Trailing Stop alcanzado: {precio_actual:.2f} <= {trailing_stop:.2f}")
                    vender(precio_actual, rsi, symbol, estado, "Trailing Stop alcanzado")
                    return
            else:
                sl = entrada * (1 - PARAMS["stop_loss"] / 100)
                if precio_actual <= sl:
                    logging.info(f"[{symbol}] Stop Loss alcanzado: {precio_actual:.2f} <= {sl:.2f}")
                    vender(precio_actual, rsi, symbol, estado, "Stop Loss alcanzado")
                    return

            if precio_actual >= tp:
                logging.info(f"[{symbol}] Take Profit alcanzado: {precio_actual:.2f} >= {tp:.2f}")
                vender(precio_actual, rsi, symbol, estado, "Take Profit alcanzado")
                return

    logging.info(f"[{symbol}] ⚪ Sin señal clara | EMA OK: {ema_ok} | RSI: {rsi:.2f}")
    rsi_anterior[symbol] = rsi