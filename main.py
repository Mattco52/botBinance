import os
import time
import threading
from datetime import datetime
import pandas as pd
from binance.client import Client
from binance.enums import *
from binance import ThreadedWebsocketManager
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
    'rsi_buy_threshold': 30,   # RSI para comprar (sobreventa)
    'rsi_sell_threshold': 70,  # RSI para vender (sobrecompra)
    'take_profit': 1.5,  # porcentaje
    'stop_loss': 0.75,   # porcentaje
    'quantity': 0.001,
    'sleep_time': 60
}

# --- Flask app --- #
app = Flask(__name__)

@app.route('/')
def status():
    return jsonify({
        'status': 'Bot activo',
        'hora': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'posicion_abierta': posicion_abierta
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

# --- Indicadores técnicos --- #
def calcular_indicadores():
    klines = client.get_historical_klines(
        symbol=PARAMS['symbol'],
        interval=PARAMS['timeframe'],
        start_str="48 hours ago UTC"  # Más historial para mejor cálculo
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

# --- Estado global para controlar posiciones --- #
posicion_abierta = False
lock_posicion = threading.Lock()  # Para manejar acceso seguro a la variable global

# --- Manejo de eventos de órdenes vía WebSocket --- #
def handle_order_event(msg):
    global posicion_abierta
    # msg contiene datos del evento de orden
    if 'e' in msg and msg['e'] == 'ORDER_TRADE_UPDATE':
        o = msg['o']
        symbol = o['s']
        status = o['X']  # Status de la orden
        side = o['S']    # 'BUY' o 'SELL'
        order_type = o['o']
        order_id = o['i']
        # print para debugging:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Evento orden: symbol={symbol} side={side} status={status} type={order_type} orderId={order_id}", flush=True)

        # Solo nos importa el símbolo que estamos operando
        if symbol != PARAMS['symbol']:
            return
        
        # Detectar cierre de posición (orden OCO ejecutada o venta de mercado)
        # Status 'FILLED' significa ejecutada
        if status == 'FILLED':
            if side == 'SELL':
                # Cuando se vende (take profit o stop loss o venta manual), cerramos la posición
                with lock_posicion:
                    if posicion_abierta:
                        posicion_abierta = False
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⚠️ Posición cerrada por orden SELL ejecutada", flush=True)
                        enviar_mensaje_telegram("⚠️ Posición cerrada (TP, SL o venta manual). Bot listo para nueva operación.")

            elif side == 'BUY':
                # Confirmar que posición está abierta tras compra
                with lock_posicion:
                    if not posicion_abierta:
                        posicion_abierta = True
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⚠️ Posición abierta por orden BUY ejecutada", flush=True)
                        enviar_mensaje_telegram("⚠️ Posición abierta (compra ejecutada).")

# --- Lógica de trading --- #
def ejecutar_estrategia():
    global posicion_abierta

    try:
        ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{ahora}] Ejecutando estrategia...", flush=True)

        precio_actual = float(client.get_symbol_ticker(symbol=PARAMS['symbol'])['price'])
        ind = calcular_indicadores()

        ema_ok = ind['ema9'] > ind['ema21']
        rsi = ind['rsi']

        with lock_posicion:
            posicion = posicion_abierta

        # Condición de compra
        if not posicion and ema_ok and rsi < PARAMS['rsi_buy_threshold']:
            print(f"[{ahora}] 🟢 Señal de COMPRA | Precio: {precio_actual:.2f} | RSI: {rsi:.2f}", flush=True)
            enviar_mensaje_telegram(f"🟢 Señal de COMPRA\nPrecio: {precio_actual:.2f}\nRSI: {rsi:.2f}")

            order = client.create_order(
                symbol=PARAMS['symbol'],
                side=Client.SIDE_BUY,
                type=Client.ORDER_TYPE_MARKET,
                quantity=PARAMS['quantity']
            )
            print(f"[{ahora}] ✅ Orden de COMPRA ejecutada ID: {order['orderId']}", flush=True)
            enviar_mensaje_telegram(f"✅ Orden de COMPRA ejecutada")

            # Configurar OCO para tomar ganancias y limitar pérdidas
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
            print(f"[{ahora}] 🔷 OCO configurado | TP: {tp} | SL: {sl}", flush=True)
            enviar_mensaje_telegram(f"🔷 OCO configurado\nTP: {tp} | SL: {sl}")

            with lock_posicion:
                posicion_abierta = True

        # Condición de venta manual si RSI está alto (sobrecompra)
        elif posicion and rsi > PARAMS['rsi_sell_threshold']:
            print(f"[{ahora}] 🔴 Señal de VENTA | Precio: {precio_actual:.2f} | RSI: {rsi:.2f}", flush=True)
            enviar_mensaje_telegram(f"🔴 Señal de VENTA\nPrecio: {precio_actual:.2f}\nRSI: {rsi:.2f}")

            order = client.create_order(
                symbol=PARAMS['symbol'],
                side=Client.SIDE_SELL,
                type=Client.ORDER_TYPE_MARKET,
                quantity=PARAMS['quantity']
            )
            print(f"[{ahora}] ✅ Orden de VENTA ejecutada ID: {order['orderId']}", flush=True)
            enviar_mensaje_telegram(f"✅ Orden de VENTA ejecutada")

            with lock_posicion:
                posicion_abierta = False

        else:
            print(f"[{ahora}] ⚪ Sin señal clara | EMA9: {ind['ema9']:.2f} > EMA21: {ind['ema21']:.2f}={ema_ok} | RSI: {rsi:.2f}", flush=True)

    except Exception as e:
        error_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ Error: {e}"
        print(error_msg, flush=True)
        enviar_mensaje_telegram(f"❌ Error en bot:\n{str(e)}")

# --- Loop principal del bot --- #
def run_bot():
    while True:
        ejecutar_estrategia()
        time.sleep(PARAMS['sleep_time'])

# --- Inicializar WebSocket para user data stream --- #
def start_user_stream():
    twm = ThreadedWebsocketManager(api_key=api_key, api_secret=secret_key, testnet=True)
    twm.start()

    # Obtener listen_key para el user data stream
    listen_key = client.stream_get_listen_key()

    # Iniciar el user socket SIN pasar listen_key (no se acepta ese argumento)
    twm.start_user_socket(callback=handle_order_event)

    # Función para renovar el listen_key cada 30 minutos y mantener vivo el stream
    def keep_alive():
        while True:
            try:
                client.stream_keepalive(listen_key=listen_key)
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Listen key renovado correctamente.", flush=True)
            except Exception as e:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error renovando listen key: {e}", flush=True)
            time.sleep(30 * 60)  # renovar cada 30 minutos

    # Hilo en segundo plano para renovar el listen_key periódicamente
    threading.Thread(target=keep_alive, daemon=True).start()

    return twm


# --- Lanzar Flask + Bot + WebSocket --- #
if __name__ == '__main__':
    twm = start_user_stream()  # Iniciar WebSocket para escuchar eventos orden

    # Iniciar el bot en segundo plano
    threading.Thread(target=run_bot, daemon=True).start()

    # Ejecutar servidor Flask
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
