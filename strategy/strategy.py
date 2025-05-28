from config.settings import PARAMS
from data.market_data import obtener_datos, obtener_precio_actual
from execution.orders import comprar, vender, verificar_cierre_oco
from execution.state_manager import cargar_estado
import logging
from datetime import datetime

# Memoria temporal para RSI anterior por símbolo
rsi_anterior = {}

def ejecutar_estrategia(symbol):
    global rsi_anterior

    ahora = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    logging.info(f"[{ahora}] [{symbol}] Ejecutando estrategia...")

    estado = cargar_estado(symbol)

    verificar_cierre_oco(symbol, estado)

    precio_actual = obtener_precio_actual(symbol)
    fila_ant, fila_act = obtener_datos(symbol)
    if fila_act is None:
        logging.error(f"[{ahora}] [{symbol}] No se pudieron obtener los indicadores.")
        return

    ema_ok = fila_act['ema9'] > fila_act['ema21']
    rsi = fila_act['rsi']
    rsi_prev = fila_ant['rsi']

    # Timestamp de la vela actual
    timestamp_raw = fila_act.name if hasattr(fila_act, 'name') else None
    if isinstance(timestamp_raw, int):
        vela_timestamp = datetime.utcfromtimestamp(timestamp_raw / 1000)
    else:
        vela_timestamp = timestamp_raw or datetime.utcnow()
    vela_actual_str = vela_timestamp.strftime("%Y-%m-%d %H:%M:%S")

    ultima_compra = estado.get("ultima_compra_timestamp")

    puede_comprar = (
        not estado["estado"]
        and ema_ok
        and rsi < PARAMS['rsi_buy_threshold']
        and (not ultima_compra or ultima_compra < vela_actual_str)
    )

    if puede_comprar:
        comprar(precio_actual, rsi, symbol, estado)

    elif estado["estado"] and estado["cantidad_acumulada"] > 0:
        entrada = estado["precio_entrada_promedio"]
        ganancia_pct = ((precio_actual - entrada) / entrada) * 100

        if rsi > PARAMS['rsi_sell_threshold'] or ganancia_pct >= 0.3:
            vender(precio_actual, rsi, symbol, estado, "Condiciones de venta cumplidas")

        elif rsi < 60 and rsi_prev > 60:
            vender(precio_actual, rsi, symbol, estado, "RSI perdió momentum")

        # Take profit y trailing stop solo si no se está usando OCO
        if not PARAMS['use_oco']:
            tp = entrada * (1 + PARAMS['take_profit'] / 100)

            if PARAMS['use_trailing_stop']:
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

    elif estado["estado"]:
        logging.info(f"[{ahora}] [{symbol}] Posición abierta sin condiciones de venta | RSI: {rsi:.2f}")

    else:
        logging.info(f"[{ahora}] [{symbol}] ⚪ Sin señal clara | EMA9 > EMA21: {ema_ok} | RSI: {rsi:.2f}")

    # Guardar el RSI anterior por símbolo
    rsi_anterior[symbol] = rsi
