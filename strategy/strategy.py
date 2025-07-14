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

def detectar_impulso_fuerte(df):
    if len(df) < 21:
        return False

    cierre_actual = df['close'].iloc[-1]
    maximo_20_velas = df['high'].iloc[-20:].max()
    volumen_actual = df['volume'].iloc[-1]
    volumen_promedio = df['volume'].iloc[-20:].mean()
    
    cruza_ema = df['ema9'].iloc[-1] > df['ema21'].iloc[-1] and df['ema9'].iloc[-2] <= df['ema21'].iloc[-2]
    rompe_resistencia = cierre_actual > maximo_20_velas
    volumen_ok = volumen_actual > volumen_promedio * 1.3

    return cruza_ema and rompe_resistencia and volumen_ok

def ejecutar_estrategia(symbol):
    logging.info(f"[{symbol}] Ejecutando estrategia...")

    estado = cargar_estado(symbol)

    if PARAMS['use_oco']:
        verificar_cierre_oco(symbol, estado)

    try:
        df = obtener_datos(symbol, PARAMS["timeframe"])
        if df is None or df.empty:
            logging.warning(f"[{symbol}] No se pudieron obtener datos.")
            return

        df["ema9"] = calcular_ema(df["close"], PARAMS["ema_short"])
        df["ema21"] = calcular_ema(df["close"], PARAMS["ema_long"])
        df["rsi"] = calcular_rsi(df["close"], PARAMS["rsi_window"])

        precio_actual = float(df["close"].iloc[-1])
        ema_ok = df["ema9"].iloc[-1] > df["ema21"].iloc[-1]
        rsi_actual = df["rsi"].iloc[-1]

        # 🚀 Modo turbo: impulso fuerte
        if not estado["estado"] and detectar_impulso_fuerte(df):
            cantidad_turbo = round(calcular_cantidad_valida(symbol, precio_actual) * 3, 6)
            if cantidad_turbo:
                PARAMS["quantity"] = cantidad_turbo
                enviar_mensaje(f"🚀 [{symbol}] Impulso fuerte detectado. Activando Modo Turbo con {cantidad_turbo} BTC")
                comprar(precio_actual, rsi_actual, symbol, estado)
                return

        logging.info(f"[{symbol}] ⚪ Sin señal clara | EMA OK: {ema_ok} | RSI: {rsi_actual:.2f}")

        # 🟢 Entrada normal
        if not estado["estado"] and ema_ok and rsi_actual < PARAMS["rsi_buy_threshold"]:
            cantidad = calcular_cantidad_valida(symbol, precio_actual)
            if cantidad:
                PARAMS["quantity"] = cantidad
                comprar(precio_actual, rsi_actual, symbol, estado)
            else:
                enviar_mensaje(f"❌ [{symbol}] No se pudo calcular una cantidad válida para la orden.")

        # 🔴 Salida (venta)
        elif estado["estado"]:
            razon = None
            ganancia_pct = ((precio_actual - estado["precio_entrada_promedio"]) / estado["precio_entrada_promedio"]) * 100

            if rsi_actual > PARAMS["rsi_sell_threshold"]:
                razon = "RSI alto"
            elif PARAMS["use_trailing_stop"]:
                trailing_pct = 0.25
                if symbol == "SOLUSDT":
                    trailing_pct = 0.5
                if verificar_trailing_stop(symbol, precio_actual, estado, trailing_pct):
                    vender(precio_actual, rsi_actual, symbol, estado, razon="Trailing Stop / Break-even")
                    return
            else:
                if ganancia_pct >= PARAMS["take_profit"]:
                    razon = "Take Profit alcanzado"
                elif ganancia_pct <= -PARAMS["stop_loss"]:
                    razon = "Stop Loss alcanzado"

            if razon:
                vender(precio_actual, rsi_actual, symbol, estado, razon=razon)

    except Exception as e:
        logging.error(f"[{symbol}] Error en estrategia: {e}")
