import logging
from binance.client import Client
from config.settings import API_KEY, SECRET_KEY, TESTNET, PARAMS
from utils.indicators import calcular_ema, calcular_rsi
from utils.data_fetcher import obtener_datos
from utils.binance_filters import calcular_cantidad_valida, cumple_min_notional
from notifier.telegram import enviar_mensaje
from execution.operations import comprar, vender, verificar_cierre_oco
from execution.state_manager import cargar_estado

client = Client(API_KEY, SECRET_KEY, testnet=TESTNET)

def ejecutar_estrategia(symbol):
    ahora = Client().get_server_time()
    logging.info(f"[{symbol}] Ejecutando estrategia...")

    # ✅ Cargar estado actual
    estado = cargar_estado(symbol)

    # ✅ Verificar si alguna orden OCO fue cerrada
    if PARAMS['use_oco']:
        verificar_cierre_oco(symbol, estado)

    try:
        df = obtener_datos(symbol, PARAMS["timeframe"])
        if df is None or df.empty:
            logging.warning(f"[{symbol}] No se pudieron obtener datos.")
            return

        ema_corta = calcular_ema(df["close"], PARAMS["ema_short"])
        ema_larga = calcular_ema(df["close"], PARAMS["ema_long"])
        rsi = calcular_rsi(df["close"], PARAMS["rsi_window"])

        precio_actual = float(df["close"].iloc[-1])
        ema_ok = ema_corta.iloc[-1] > ema_larga.iloc[-1]
        rsi_actual = rsi.iloc[-1]

        logging.info(f"[{symbol}] ⚪ Sin señal clara | EMA OK: {ema_ok} | RSI: {rsi_actual:.2f}")

        # ✅ Señal de compra
        if not estado["estado"] and ema_ok and rsi_actual < PARAMS["rsi_buy_threshold"]:
            cantidad = calcular_cantidad_valida(symbol, precio_actual)
            if cantidad:
                PARAMS["quantity"] = cantidad
                comprar(precio_actual, rsi_actual, symbol, estado)
            else:
                enviar_mensaje(f"❌ [{symbol}] No se pudo calcular una cantidad válida para la orden.")

        # ✅ Señal de venta
        elif estado["estado"]:
            razon = None
            ganancia_pct = ((precio_actual - estado["precio_entrada_promedio"]) / estado["precio_entrada_promedio"]) * 100
            if rsi_actual > PARAMS["rsi_sell_threshold"]:
                razon = "RSI alto"
            elif PARAMS["use_trailing_stop"]:
                if precio_actual > estado["precio_maximo"]:
                    estado["precio_maximo"] = precio_actual
                limite_stop = estado["precio_maximo"] * (1 - PARAMS["trailing_stop_pct"] / 100)
                if precio_actual < limite_stop:
                    razon = "Trailing Stop alcanzado"
            else:
                if ganancia_pct >= PARAMS["take_profit"]:
                    razon = "Take Profit alcanzado"
                elif ganancia_pct <= -PARAMS["stop_loss"]:
                    razon = "Stop Loss alcanzado"

            if razon:
                vender(precio_actual, rsi_actual, symbol, estado, razon=razon)

    except Exception as e:
        logging.error(f"[{symbol}] Error en estrategia: {e}")