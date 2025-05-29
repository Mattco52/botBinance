from config.settings import PARAMS
from data.market_data import obtener_datos, obtener_precio_actual
from execution.orders import comprar, vender, verificar_cierre_oco
from execution.state_manager import cargar_estado
from utils.binance_quantity import calcular_cantidad_valida
import logging
from datetime import datetime

def ejecutar_estrategia(symbol):
    ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logging.info(f"[{ahora}] [{symbol}] Ejecutando estrategia...")

    estado = cargar_estado(symbol)
    verificar_cierre_oco(symbol, estado)

    # Obtener datos de mercado e indicadores
    precio_actual = obtener_precio_actual(symbol)
    fila_ant, fila_act = obtener_datos(symbol)

    if fila_act is None or precio_actual is None:
        logging.warning(f"[{symbol}] No se obtuvieron datos de mercado o indicadores.")
        return

    ema_ok = fila_act['ema9'] > fila_act['ema21']
    rsi = fila_act['rsi']
    rsi_prev = fila_ant['rsi']

    # Timestamp de la vela
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
        cantidad = calcular_cantidad_valida(symbol, precio_actual)
        if cantidad:
            PARAMS['quantity'] = cantidad  # actualizar cantidad dinámica
            comprar(precio_actual, rsi, symbol, estado)
        else:
            logging.warning(f"[{symbol}] ❌ No se pudo calcular una cantidad válida para la orden.")
            return

    elif estado["estado"] and estado["cantidad_acumulada"] > 0:
        # VENTA por RSI
        if rsi > PARAMS['rsi_sell_threshold']:
            vender(precio_actual, rsi, symbol, estado, "RSI sobre umbral de venta")
        elif rsi < 60 and rsi_prev > 60:
            vender(precio_actual, rsi, symbol, estado, "RSI perdió momentum")

        # Simulación de Take Profit / Trailing Stop
        if not PARAMS['use_oco']:
            entrada = estado["precio_entrada_promedio"]
            cantidad = estado["cantidad_acumulada"]

            tp = entrada * (1 + PARAMS['take_profit'] / 100)
            sl = entrada * (1 - PARAMS['stop_loss'] / 100)

            if PARAMS['use_trailing_stop']:
                if precio_actual > estado["precio_maximo"]:
                    estado["precio_maximo"] = precio_actual

                trailing_stop = estado["precio_maximo"] * (1 - PARAMS['trailing_stop_pct'] / 100)

                if precio_actual <= trailing_stop:
                    vender(precio_actual, rsi, symbol, estado, "Trailing Stop alcanzado")
            else:
                if precio_actual <= sl:
                    vender(precio_actual, rsi, symbol, estado, "Stop Loss alcanzado")

            if precio_actual >= tp:
                vender(precio_actual, rsi, symbol, estado, "Take Profit alcanzado")

    else:
        logging.info(f"[{ahora}] [{symbol}] ⚪ Sin señal clara | EMA OK: {ema_ok} | RSI: {rsi:.2f}")