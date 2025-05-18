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

PARAMS = {
    'symbol': 'BTCUSDT',
    'timeframe': KLINE_INTERVAL_5MINUTE,
    'ema_short': 9,
    'ema_long': 21,
    'rsi_window': 14,
    'rsi_buy_threshold': 30,
    'rsi_sell_threshold': 70,
    'rsi_exit_threshold': 60,  # salida por pérdida de momentum
    'take_profit': 1.5,
    'stop_loss': 0.75,
    'quantity': 0.001,
    'sleep_time': 60
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
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": mensaje}
    try:
        requests.post(url, data=payload, timeout=5)
    except Exception as e:
        print(f"❌ Error enviando mensaje Telegram: {e}", flush=True)

def calcular_indicadores():
    klines = client.get_historical_klines(
        symbol=PARAMS['symbol'],
        interval=PARAMS['timeframe'],
        start_str="24 hours ago UTC"
    )
    df = pd.DataFrame(klines, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base', 'taker_buy_quote', 'ignore'
    ])
    df['close'] = pd.to_numeric(df['close'])
    df['high'] = pd.to_numeric(df['high'])

    df['ema9'] = EMAIndicator(df['close'], window=PARAMS['ema_short']).ema_indicator()
    df['ema21'] = EMAIndicator(df['close'], window=PARAMS['ema_long']).ema_indicator()
    df['rsi'] = RSIIndicator(df['close'], window=PARAMS['rsi_window']).rsi()

    return df.iloc[-1]

def hay_orden_abierta():
    """Verifica si hay una orden abierta del lado de compra."""
    try:
        open_orders = client.get_open_orders(symbol=PARAMS['symbol'])
        return len(open_orders) > 0
    except Exception as e:
        print(f"⚠️ Error al verificar órdenes abiertas: {e}")
        return False

posicion_abierta = False

def comprar(precio_actual, rsi):
    global posicion_abierta
    ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n🟢 [{ahora}] EJECUTANDO COMPRA\nPrecio actual: {precio_actual:.2f} | RSI: {rsi:.2f}", flush=True)
    enviar_mensaje_telegram(f"🟢 COMPRA ejecutada\nPrecio: {precio_actual:.2f}\nRSI: {rsi:.2f}")

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
        price=str(tp),
        stopPrice=str(sl),
        stopLimitPrice=str(sl),
        stopLimitTimeInForce='GTC'
    )
    print(f"✅ Orden ejecutada | TP: {tp} | SL: {sl}")
    enviar_mensaje_telegram(f"✅ OCO colocado\nTP: {tp} | SL: {sl}")

    posicion_abierta = True

def vender(precio_actual, rsi, motivo=""):
    global posicion_abierta
    ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n🔴 [{ahora}] EJECUTANDO VENTA\nMotivo: {motivo}\nPrecio actual: {precio_actual:.2f} | RSI: {rsi:.2f}", flush=True)
    enviar_mensaje_telegram(f"🔴 VENTA ejecutada\n{motivo}\nPrecio: {precio_actual:.2f}\nRSI: {rsi:.2f}")

    order = client.create_order(
        symbol=PARAMS['symbol'],
        side=Client.SIDE_SELL,
        type=Client.ORDER_TYPE_MARKET,
        quantity=PARAMS['quantity']
    )
    print("✅ Venta completada.")
    posicion_abierta = False

def ejecutar_estrategia():
    global posicion_abierta
    ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n==============================")
    print(f"⏰ [{ahora}] Ejecutando estrategia...")
    print(f"==============================")

    try:
        precio_actual = float(client.get_symbol_ticker(symbol=PARAMS['symbol'])['price'])
        ind = calcular_indicadores()

        ema9 = ind['ema9']
        ema21 = ind['ema21']
        rsi = ind['rsi']
        ema_ok = ema9 > ema21

        print(f"📊 Indicadores: EMA9 = {ema9:.2f} | EMA21 = {ema21:.2f} | RSI = {rsi:.2f}")

        if not posicion_abierta:
            if ema_ok and rsi < PARAMS['rsi_buy_threshold']:
                comprar(precio_actual, rsi)
            else:
                print(f"⚪ No se cumplen condiciones de compra.")
        else:
            if not hay_orden_abierta():
                print("🟡 No hay órdenes abiertas. Posición asumida como cerrada.")
                posicion_abierta = False
            elif rsi > PARAMS['rsi_sell_threshold']:
                vender(precio_actual, rsi, motivo="RSI > 70 (Sobrecompra)")
            elif rsi < PARAMS['rsi_exit_threshold'] or not ema_ok:
                vender(precio_actual, rsi, motivo="RSI < 60 o EMA9 < EMA21 (salida técnica)")
            else:
                print(f"🟡 Posición abierta, pero sin señal de salida.")

    except Exception as e:
        error_msg = f"❌ ERROR en estrategia: {e}"
        print(error_msg, flush=True)
        enviar_mensaje_telegram(error_msg)

def run_bot():
    while True:
        ejecutar_estrategia()
        time.sleep(PARAMS['sleep_time'])

if __name__ == '__main__':
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
