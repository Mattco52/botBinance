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

# --- Cargar API keys --- #
load_dotenv()
api_key = os.getenv("API_KEY")
secret_key = os.getenv("SECRET_KEY")
client = Client(api_key, secret_key, testnet=True)

# --- Parámetros del bot --- #
PARAMS = {
    'symbol': 'BTCUSDT',
    'timeframe': KLINE_INTERVAL_5MINUTE,
    'ema_short': 9,
    'ema_long': 21,
    'rsi_window': 14,
    'take_profit': 1.5,
    'stop_loss': 0.75,
    'quantity': 0.001,
    'sleep_time': 60
}

# --- Flask app --- #
app = Flask(__name__)

@app.route('/')
def status():
    return jsonify({
        'status': 'Bot activo',
        'hora': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }), 200

# --- Función para enviar mensajes a Telegram --- #
def enviar_mensaje_telegram(mensaje):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("CHAT_ID")
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": mensaje
    }

    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"❌ Error enviando mensaje Telegram: {e}", flush=True)

# --- Lógica de trading con estrategia activa --- #
def ejecutar_estrategia():
    try:
        ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{ahora}] Ejecutando estrategia...", flush=True)

        # Obtener los datos históricos recientes
        klines = client.get_historical_klines(
            symbol=PARAMS['symbol'],
            interval=PARAMS['timeframe'],
            start_str="3 hours ago UTC"
        )
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base', 'taker_buy_quote', 'ignore'
        ])
        df['close'] = pd.to_numeric(df['close'])
        df['ema9'] = EMAIndicator(df['close'], window=PARAMS['ema_short']).ema_indicator()
        df['ema21'] = EMAIndicator(df['close'], window=PARAMS['ema_long']).ema_indicator()
        df['rsi'] = RSIIndicator(df['close'], window=PARAMS['rsi_window']).rsi()

        # Filtrar datos más recientes
        prev = df.iloc[-2]
        curr = df.iloc[-1]
        precio_actual = float(client.get_symbol_ticker(symbol=PARAMS['symbol'])['price'])

        # --- Señal de COMPRA --- #
        cruz_ema_up = prev['ema9'] < prev['ema21'] and curr['ema9'] > curr['ema21']
        rsi_up = prev['rsi'] < 50 and curr['rsi'] > 50
        close_above_ema21 = curr['close'] > curr['ema21']

        if cruz_ema_up and rsi_up and close_above_ema21:
            print(f"[{ahora}] 🟢 SEÑAL DE COMPRA", flush=True)
            enviar_mensaje_telegram(f"🟢 COMPRA ejecutada\nPrecio: {precio_actual:.2f}\nRSI: {curr['rsi']:.2f}")
            order = client.create_order(
                symbol=PARAMS['symbol'],
                side=Client.SIDE_BUY,
                type=Client.ORDER_TYPE_MARKET,
                quantity=PARAMS['quantity']
            )
            tp = round(precio_actual * (1 + PARAMS['take_profit'] / 100), 2)
            sl = round(precio_actual * (1 - PARAMS['stop_loss'] / 100), 2)

            client.create_oco_order(
                symbol=PARAMS['symbol'],
                side=Client.SIDE_SELL,
                quantity=PARAMS['quantity'],
                stopPrice=sl,
                stopLimitPrice=sl,
                price=tp
            )
            enviar_mensaje_telegram(f"🔷 OCO configurado\nTP: {tp} | SL: {sl}")

        # --- Señal de VENTA (salida anticipada) --- #
        cruz_ema_down = prev['ema9'] > prev['ema21'] and curr['ema9'] < curr['ema21']
        rsi_down = prev['rsi'] > 55 and curr['rsi'] < 50
        close_below_ema9 = curr['close'] < curr['ema9']

        if cruz_ema_down and rsi_down and close_below_ema9:
            print(f"[{ahora}] 🔻 SEÑAL DE VENTA", flush=True)
            enviar_mensaje_telegram("🔻 VENTA anticipada señalada. Considera cerrar manualmente si tienes posición.")

        # Si no hay señal
        if not (cruz_ema_up and rsi_up and close_above_ema21) and not (cruz_ema_down and rsi_down and close_below_ema9):
            print(f"[{ahora}] 🛌 Sin señal clara | RSI: {curr['rsi']:.2f}", flush=True)

    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ Error: {e}", flush=True)
        enviar_mensaje_telegram(f"❌ Error en bot:\n{str(e)}")

# --- Loop principal del bot --- #
def run_bot():
    while True:
        ejecutar_estrategia()
        time.sleep(PARAMS['sleep_time'])

# --- Lanzar Flask + Bot --- #
if __name__ == '__main__':
    # Iniciar el bot en segundo plano
    threading.Thread(target=run_bot, daemon=True).start()

    # Ejecutar servidor Flask
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
