from config.settings import PARAMS
from data.market_data import obtener_datos, obtener_precio_actual
from execution.orders import comprar, vender, verificar_cierre_oco
from execution.state_manager import cargar_estado
import logging
from datetime import datetime

# Ejecutado por cada símbolo individualmente
def ejecutar_estrategia(symbol):
    ahora = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    logging.info(f"[{ahora}] [{symbol}] Ejecutando estrategia...")

    # Cargar estado actual
    estado = cargar_estado(symbol)

    # Verificar si órdenes OCO ya se cerraron
    verificar_cierre_oco(symbol, estado)

    # Obtener datos de mercado e indicadores
    precio_actual = obtener_precio_actual(symbol)
    fila_ant, fila_act = obtener_datos(symbol)

    if fila_act is None:
        logging.warning(f"[{symbol}] ❌ No se pudo obtener fila de indicadores.")
        return

    ema_ok = fila_act['ema9'] > fila_act['ema21']
    rsi = fila_act['rsi']
    rsi_prev = fila_ant['rsi']

    # Timestamp para comparar con última compra
    timestamp_raw = fila_act.name if hasattr(fila_act, 'name') else None
    vela_ts = datetime.utcfromtimestamp(timestamp_raw / 1000) if isinstance(timestamp_raw, int) else timestamp_raw or datetime.utcnow()
    vela_str = vela_ts.strftime('%Y-%m-%d %H:%M:%S')

    ultima_compra = estado.get("ultima_compra_timestamp")

    puede_comprar = (
        not estado["estado"] and ema_ok and rsi < PARAMS["rsi_buy_threshold"]
        and (not ultima_compra or ultima_compra < vela_str)
    )

    if puede_comprar:
        comprar(precio_actual, rsi, symbol, estado)
        return  # Ya compró, esperar próximo ciclo

    # Verificación de venta solo si hay posición activa
    if estado["estado"] and estado["cantidad_acumulada"] > 0:
        entrada = estado["precio_entrada_promedio"]
        cantidad = estado["cantidad_acumulada"]
        tp = entrada * (1 + PARAMS["take_profit"] / 100)
        sl = entrada * (1 - PARAMS["stop_loss"] / 100)

        # ✅ Condiciones de venta
        if rsi > PARAMS["rsi_sell_threshold"]:
            vender(precio_actual, rsi, symbol, estado, "RSI sobre umbral de venta")
            return

        if rsi < 60 and rsi_prev > 60:
            vender(precio_actual, rsi, symbol, estado, "RSI perdió momentum")
            return

        # ✅ Simulación de lógica TP/SL/Trailing (si no se usa OCO)
        if not PARAMS["use_oco"]:
            if PARAMS["use_trailing_stop"]:
                if precio_actual > estado["precio_maximo"]:
                    estado["precio_maximo"] = precio_actual

                trailing_stop = estado["precio_maximo"] * (1 - PARAMS["trailing_stop_pct"] / 100)

                if precio_actual <= trailing_stop:
                    vender(precio_actual, rsi, symbol, estado, "Trailing Stop alcanzado")
                    return
            else:
                if precio_actual <= sl:
                    vender(precio_actual, rsi, symbol, estado, "Stop Loss alcanzado")
                    return

            if precio_actual >= tp:
                vender(precio_actual, rsi, symbol, estado, "Take Profit alcanzado")
                return

    else:
        logging.info(f"[{symbol}] ⚪ Sin señal clara | EMA9 > EMA21: {ema_ok} | RSI: {rsi:.2f}")
