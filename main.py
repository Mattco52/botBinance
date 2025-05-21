import os
import time
import threading
from datetime import datetime
import pandas as pd
from binance.client import Client
from binance.enums import *
from dotenv import load_dotenv
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from flask import Flask, jsonify
import requests
import logging

# --- Configuración de Logging --- #
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Cargar API keys --- #
load_dotenv()
api_key = os.getenv("API_KEY")
secret_key = os.getenv("SECRET_KEY")
testnet = os.getenv("TESTNET", "True").lower() == "true"
client = Client(api_key, secret_key, testnet=testnet)

# --- Parámetros del Bot --- #
PARAMS = {
    'symbol': 'BTCUSDT',
    'timeframe': KLINE_INTERVAL_5MINUTE,
    'ema_short': 9,
    'ema_long': 21,
    'rsi_window': 14,
    'rsi_buy_threshold': 45, #40
    'rsi_sell_threshold': 55, #60
    'take_profit': 0.3, #1.0
    'stop_loss': 0.2, #0.5
    'quantity': 0.001,
    'sleep_time': 30,
    'use_oco': True,
}

app = Flask(__name__)

@app.route('/')
def status():
    return jsonify({
        'status': 'Bot activo',
        'hora': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }), 200

def enviar_mensaje_telegram(mensaje):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("CHAT_ID")
    if not token or not chat_id:
        logging.warning("Telegram token o chat ID no configurados. No se enviarán mensajes.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": mensaje}
    retries = 3
    delay = 1

    for i in range(retries):
        try:
            response = requests.post(url, data=payload, timeout=10)
            response.raise_for_status()
            break
        except requests.exceptions.RequestException as e:
            logging.error(f"Error al enviar mensaje a Telegram (intento {i + 1}/{retries}): {e}")
            if i < retries - 1:
                time.sleep(delay)
                delay *= 2
            else:
                logging.error("Máximo de reintentos alcanzado. No se pudo enviar el mensaje.")
                return

def calcular_indicadores():
    try:
        klines = client.get_historical_klines(
            symbol=PARAMS['symbol'],
            interval=PARAMS['timeframe'],
            start_str="24 hours ago UTC"
        )
    except Exception as e:
        logging.error(f"Error al obtener klines de Binance: {e}")
        return None

    df = pd.DataFrame(klines, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base', 'taker_buy_quote', 'ignore'
    ])
    df['close'] = pd.to_numeric(df['close'])
    df['high'] = pd.to_numeric(df['high'])
    df['low'] = pd.to_numeric(df['low'])

    df['ema9'] = EMAIndicator(df['close'], window=PARAMS['ema_short']).ema_indicator()
    df['ema21'] = EMAIndicator(df['close'], window=PARAMS['ema_long']).ema_indicator()
    df['rsi'] = RSIIndicator(df['close'], window=PARAMS['rsi_window']).rsi()

    return df.iloc[-2], df.iloc[-1]  # fila anterior, fila actual

# --- Estado de trading --- #
posicion_abierta = False
order_id = None
oco_order_ids = []  # guardaremos los IDs de las órdenes OCO
rsi_anterior = None

def comprar(precio_actual, rsi):
    global posicion_abierta, order_id, oco_order_ids
    ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logging.info(f"[{ahora}] 🟢 Ejecutando COMPRA | Precio: {precio_actual:.2f} | RSI: {rsi:.2f}")
    enviar_mensaje_telegram(f"🟢 Señal de COMPRA\nPrecio: {precio_actual:.2f}\nRSI: {rsi:.2f}")

    try:
        order = client.create_order(
            symbol=PARAMS['symbol'],
            side=Client.SIDE_BUY,
            type=Client.ORDER_TYPE_MARKET,
            quantity=PARAMS['quantity']
        )
        order_id = order['orderId']
        logging.info(f"[{ahora}] ✅ Orden COMPRA ejecutada ID: {order_id}")
        enviar_mensaje_telegram("✅ Orden de COMPRA ejecutada")
        posicion_abierta = True

        if PARAMS['use_oco']:
            tp = round(precio_actual * (1 + PARAMS['take_profit'] / 100), 2)
            sl = round(precio_actual * (1 - PARAMS['stop_loss'] / 100), 2)
            try:
                oco_order = client.create_oco_order(
                    symbol=PARAMS['symbol'],
                    side=Client.SIDE_SELL,
                    quantity=PARAMS['quantity'],
                    price=str(tp),
                    stopPrice=str(sl),
                    stopLimitPrice=str(sl),
                    stopLimitTimeInForce='GTC'
                    aboveType='STOP'
                )
                oco_order_ids = [o['orderId'] for o in oco_order['orderReports']]
                logging.info(f"[{ahora}] 🔷 OCO configurado | TP: {tp} | SL: {sl} | IDs: {oco_order_ids}")
                enviar_mensaje_telegram(f"🔷 OCO configurado\nTP: {tp} | SL: {sl}")
            except Exception as e:
                logging.error(f"Error al crear orden OCO: {e}")
                enviar_mensaje_telegram(f"❌ Error al crear orden OCO:\n{str(e)}")

    except Exception as e:
        logging.error(f"Error al ejecutar orden de compra: {e}")
        enviar_mensaje_telegram(f"❌ Error al COMPRAR:\n{str(e)}")

def vender(precio_actual, rsi, razon="Señal de salida"):
    global posicion_abierta, order_id, oco_order_ids
    ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logging.info(f"[{ahora}] 🔴 Ejecutando VENTA | Precio: {precio_actual:.2f} | RSI: {rsi:.2f} | Motivo: {razon}")
    enviar_mensaje_telegram(f"🔴 Señal de VENTA\nPrecio: {precio_actual:.2f}\nRSI: {rsi:.2f}\nMotivo: {razon}")

    try:
        order = client.create_order(
            symbol=PARAMS['symbol'],
            side=Client.SIDE_SELL,
            type=Client.ORDER_TYPE_MARKET,
            quantity=PARAMS['quantity']
        )
        logging.info(f"[{ahora}] ✅ Orden VENTA ejecutada ID: {order['orderId']}")
        enviar_mensaje_telegram("✅ Orden de VENTA ejecutada")
        posicion_abierta = False
        order_id = None
        oco_order_ids = []
    except Exception as e:
        logging.error(f"Error al ejecutar orden de venta: {e}")
        enviar_mensaje_telegram(f"❌ Error al VENDER:\n{str(e)}")

def verificar_cierre_oco():
    global posicion_abierta, oco_order_ids
    if not posicion_abierta or not oco_order_ids:
        return

    cerradas = 0
    for oid in oco_order_ids:
        try:
            order = client.get_order(symbol=PARAMS['symbol'], orderId=oid)
            if order['status'] in ['FILLED', 'CANCELED', 'REJECTED', 'EXPIRED']:
                cerradas += 1
        except Exception as e:
            logging.warning(f"No se pudo verificar el estado de la orden OCO ID {oid}: {e}")

    if cerradas == len(oco_order_ids):
        posicion_abierta = False
        oco_order_ids = []
        ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logging.info(f"[{ahora}] 📉 Orden OCO ejecutada, cerrando posición.")
        enviar_mensaje_telegram("📉 Una de las órdenes OCO fue ejecutada. Posición cerrada.")

def ejecutar_estrategia():
    global posicion_abierta, rsi_anterior
    try:
        ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logging.info(f"[{ahora}] Ejecutando estrategia...")

        verificar_cierre_oco()

        precio_actual = float(client.get_symbol_ticker(symbol=PARAMS['symbol'])['price'])
        fila_ant, fila_act = calcular_indicadores()
        if fila_act is None:
            logging.error(f"[{ahora}] No se pudieron obtener los indicadores. Saliendo.")
            return

        ema_ok = fila_act['ema9'] > fila_act['ema21']
        rsi = fila_act['rsi']
        rsi_prev = fila_ant['rsi']

        if not posicion_abierta and ema_ok and rsi < PARAMS['rsi_buy_threshold']:
            comprar(precio_actual, rsi)

        elif posicion_abierta:
            if rsi > PARAMS['rsi_sell_threshold']:
                vender(precio_actual, rsi, "RSI sobre umbral de venta")
            elif rsi < 60 and rsi_prev > 60:
                vender(precio_actual, rsi, "RSI perdió momentum")

        else:
            logging.info(f"[{ahora}] ⚪ Sin señal clara | EMA9 > EMA21: {ema_ok} | RSI: {rsi:.2f}")

        rsi_anterior = rsi

    except Exception as e:
        logging.error(f"❌ Error en ejecución: {e}")
        enviar_mensaje_telegram(f"❌ Error en bot:\n{str(e)}")

def run_bot():
    while True:
        ejecutar_estrategia()
        time.sleep(PARAMS['sleep_time'])

if __name__ == '__main__':
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
