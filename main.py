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
    'timeframe': KLINE_INTERVAL_15MINUTE,  # Podrías probar con 15 o 30 minutos
    'ema_short': 9,
    'ema_long': 21,
    'rsi_window': 14,
    'rsi_buy_threshold': 40,  # Aumentar para comprar antes
    'rsi_sell_threshold': 60, # Disminuir para vender antes
    'take_profit': 1.0,      # Reducir el TP para operaciones más frecuentes
    'stop_loss': 0.5,        # Reducir el SL para operaciones más frecuentes
    'quantity': 0.001,
    'sleep_time': 60,
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
    """
    Función para enviar mensajes a través de Telegram.
    Utiliza reintentos con retroceso exponencial para manejar errores de conexión.
    """
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
                logging.error("Maximo de reintentos alcanzado. No se pudo enviar el mensaje de Telegram.")
                return

def calcular_indicadores():
    """
    Calcula los indicadores técnicos EMA y RSI.

    Retorna:
        pandas.Series: La última fila del DataFrame con los indicadores calculados.
    """
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

    return df.iloc[-1]

posicion_abierta = False
order_id = None

def comprar(precio_actual, rsi):
    """
    Ejecuta una orden de compra y, si está habilitado, configura una orden OCO para Take Profit y Stop Loss.
    """
    global posicion_abierta, order_id
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
        enviar_mensaje_telegram(f"✅ Orden de COMPRA ejecutada")
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
                )
                logging.info(f"[{ahora}] 🔷 OCO configurado | TP: {tp} | SL: {sl} | OCO ID: {oco_order['orderId']}")
                enviar_mensaje_telegram(f"🔷 OCO configurado\nTP: {tp} | SL: {sl}")
            except Exception as e:
                logging.error(f"Error al crear orden OCO: {e}")
                enviar_mensaje_telegram(f"❌ Error al crear orden OCO:\n{str(e)}")

    except Exception as e:
        logging.error(f"Error al ejecutar orden de compra: {e}")
        enviar_mensaje_telegram(f"❌ Error al COMPRAR:\n{str(e)}")

def vender(precio_actual, rsi):
    """
    Ejecuta una orden de venta y resetea el estado de la posición.
    """
    global posicion_abierta, order_id
    ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logging.info(f"[{ahora}] 🔴 Ejecutando VENTA | Precio: {precio_actual:.2f} | RSI: {rsi:.2f}")
    enviar_mensaje_telegram(f"🔴 Señal de VENTA\nPrecio: {precio_actual:.2f}\nRSI: {rsi:.2f}")

    try:
        order = client.create_order(
            symbol=PARAMS['symbol'],
            side=Client.SIDE_SELL,
            type=Client.ORDER_TYPE_MARKET,
            quantity=PARAMS['quantity']
        )
        logging.info(f"[{ahora}] ✅ Orden VENTA ejecutada ID: {order['orderId']}")
        enviar_mensaje_telegram(f"✅ Orden de VENTA ejecutada")
        posicion_abierta = False
        order_id = None
    except Exception as e:
        logging.error(f"Error al ejecutar orden de venta: {e}")
        enviar_mensaje_telegram(f"❌ Error al VENDER:\n{str(e)}")

def ejecutar_estrategia():
    """
    Ejecuta la lógica de la estrategia de trading.
    """
    global posicion_abierta
    try:
        ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logging.info(f"[{ahora}] Ejecutando estrategia...")

        precio_actual = float(client.get_symbol_ticker(symbol=PARAMS['symbol'])['price'])
        ind = calcular_indicadores()
        if ind is None:
            logging.error(f"[{ahora}] No se pudieron obtener los indicadores. Saliendo de la ejecución de la estrategia.")
            return

        ema_ok = ind['ema9'] > ind['ema21']
        rsi = ind['rsi']

        if not posicion_abierta and ema_ok and rsi < PARAMS['rsi_buy_threshold']:
            comprar(precio_actual, rsi)
        elif posicion_abierta and rsi > PARAMS['rsi_sell_threshold']:
            vender(precio_actual, rsi)
        else:
            logging.info(f"[{ahora}] ⚪ Sin señal clara | EMA9: {ind['ema9']:.2f} > EMA21: {ind['ema21']:.2f} = {ema_ok} | RSI: {rsi:.2f}")

    except Exception as e:
        error_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ Error: {e}"
        logging.error(error_msg)
        enviar_mensaje_telegram(f"❌ Error en bot:\n{str(e)}")

def run_bot():
    """
    Función principal que ejecuta el bot en un bucle continuo.
    """
    while True:
        ejecutar_estrategia()
        time.sleep(PARAMS['sleep_time'])

if __name__ == '__main__':
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
