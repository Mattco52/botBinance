import logging
from binance.client import Client
from config.settings import API_KEY, SECRET_KEY, TESTNET, PARAMS
from data.market_data import obtener_datos
from utils.binance_filters import calcular_ema, calcular_rsi, calcular_cantidad_valida
from notifier.telegram import enviar_mensaje
from execution.orders import comprar, vender, verificar_cierre_oco, verificar_trailing_stop
from execution.state_manager import cargar_estado

# Inicializar cliente de Binance
client = Client(API_KEY, SECRET_KEY, testnet=TESTNET)

def ejecutar_estrategia(symbol):
    logging.info(f"[{symbol}] Ejecutando estrategia...")

    # Cargar estado actual de la operación para el símbolo
    estado = cargar_estado(symbol)

    # Verificar si hay una orden OCO abierta que debe cerrarse
    if PARAMS['use_oco']:
        verificar_cierre_oco(symbol, estado)

    try:
        # Obtener datos de mercado
        df = obtener_datos(symbol, PARAMS["timeframe"])
        if df is None or df.empty:
            logging.warning(f"[{symbol}] No se pudieron obtener datos.")
            return

        # Calcular indicadores técnicos
        ema_corta = calcular_ema(df["close"], PARAMS["ema_short"])
        ema_larga = calcular_ema(df["close"], PARAMS["ema_long"])
        rsi = calcular_rsi(df["close"], PARAMS["rsi_window"])

        precio_actual = float(df["close"].iloc[-1])
        ema_ok = ema_corta.iloc[-1] > ema_larga.iloc[-1]
        rsi_actual = rsi.iloc[-1]

        logging.info(f"[{symbol}] ⚪ Sin señal clara | EMA OK: {ema_ok} | RSI: {rsi_actual:.2f}")

        # 🟢 Entrada a mercado
        if not estado["estado"] and ema_ok and rsi_actual < PARAMS["rsi_buy_threshold"]:
            cantidad = calcular_cantidad_valida(symbol, precio_actual)
            if cantidad:
                PARAMS["quantity"] = cantidad
                comprar(precio_actual, rsi_actual, symbol, estado)
            else:
                enviar_mensaje(f"❌ [{symbol}] No se pudo calcular una cantidad válida para la orden.")

        # 🔴 Evaluar si se debe vender
        elif estado["estado"]:
            razon = None
            ganancia_pct = ((precio_actual - estado["precio_entrada_promedio"]) / estado["precio_entrada_promedio"]) * 100

            # ➤ Venta por RSI alto
            if rsi_actual > PARAMS["rsi_sell_threshold"]:
                razon = "RSI alto"

            # ➤ Venta por trailing stop
            elif PARAMS["use_trailing_stop"]:
                # Aplicar trailing más amplio para SOLUSDT
                trailing_pct = 0.25  # default
                if symbol == "SOLUSDT":
                    trailing_pct = 0.5  # más permisivo

                if verificar_trailing_stop(symbol, precio_actual, estado, trailing_pct):
                    vender(precio_actual, rsi_actual, symbol, estado, razon="Trailing Stop / Break-even")
                    return  # cortar ejecución para evitar doble venta

            # ➤ Venta por take profit o stop loss
            else:
                if ganancia_pct >= PARAMS["take_profit"]:
                    razon = "Take Profit alcanzado"
                elif ganancia_pct <= -PARAMS["stop_loss"]:
                    razon = "Stop Loss alcanzado"

            # Ejecutar venta si hay una razón definida
            if razon:
                vender(precio_actual, rsi_actual, symbol, estado, razon=razon)

    except Exception as e:
        logging.error(f"[{symbol}] Error en estrategia: {e}")
