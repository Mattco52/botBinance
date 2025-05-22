from binance.client import Client
from config.settings import PARAMS, API_KEY, SECRET_KEY, TESTNET
from notifier.telegram import enviar_mensaje
from datetime import datetime
import logging

client = Client(API_KEY, SECRET_KEY, testnet=TESTNET)

# Estado de trading
estado = False
order_id = None
oco_order_ids = []
cantidad_acumulada = 0.0
precio_entrada_promedio = 0.0

def comprar(precio_actual, rsi):
    global estado, order_id, oco_order_ids, cantidad_acumulada, precio_entrada_promedio

    ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logging.info(f"[{ahora}] 🟢 Ejecutando COMPRA | Precio: {precio_actual:.2f} | RSI: {rsi:.2f}")
    enviar_mensaje(f"🟢 Señal de COMPRA\nPrecio: {precio_actual:.2f}\nRSI: {rsi:.2f}")

    try:
        order = client.create_order(
            symbol=PARAMS['symbol'],
            side=Client.SIDE_BUY,
            type=Client.ORDER_TYPE_MARKET,
            quantity=PARAMS['quantity']
        )
        order_id = order['orderId']
        estado = True
        cantidad_acumulada += PARAMS['quantity']
        precio_entrada_promedio = ((precio_entrada_promedio * (cantidad_acumulada - PARAMS['quantity'])) + (precio_actual * PARAMS['quantity'])) / cantidad_acumulada

        enviar_mensaje("✅ Orden de COMPRA ejecutada")

        if PARAMS['use_oco']:
            tp = round(precio_actual * (1 + PARAMS['take_profit'] / 100), 2)
            sl = round(precio_actual * (1 - PARAMS['stop_loss'] / 100), 2)

            oco_order = client.create_oco_order(
                symbol=PARAMS['symbol'],
                side=Client.SIDE_SELL,
                quantity=round(cantidad_acumulada, 6),
                price=str(tp),
                stopPrice=str(sl),
                stopLimitPrice=str(sl),
                stopLimitTimeInForce='GTC',
                aboveType='STOP'
            )
            oco_order_ids = [o['orderId'] for o in oco_order['orderReports']]
            enviar_mensaje(f"🔷 OCO configurado\nTP: {tp} | SL: {sl}")

    except Exception as e:
        logging.error(f"Error al comprar: {e}")
        enviar_mensaje(f"❌ Error al COMPRAR:\n{str(e)}")

comprar.estado = lambda: estado  # Exponer estado

def vender(precio_actual, rsi, razon="Salida"):
    global estado, order_id, oco_order_ids, cantidad_acumulada, precio_entrada_promedio

    ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logging.info(f"[{ahora}] 🔴 Ejecutando VENTA | Precio: {precio_actual:.2f} | RSI: {rsi:.2f}")
    enviar_mensaje(f"🔴 Señal de VENTA\nPrecio: {precio_actual:.2f}\nRSI: {rsi:.2f}\nMotivo: {razon}")

    try:
        cantidad = round(cantidad_acumulada, 6)
        if cantidad <= 0:
            enviar_mensaje("⚠️ No hay cantidad acumulada para vender.")
            return

        order = client.create_order(
            symbol=PARAMS['symbol'],
            side=Client.SIDE_SELL,
            type=Client.ORDER_TYPE_MARKET,
            quantity=cantidad
        )
        ganancia = round((precio_actual - precio_entrada_promedio) * cantidad, 2)
        enviar_mensaje(f"✅ Venta ejecutada\n💰 Ganancia estimada: {ganancia} USDT")

        # Reset
        estado = False
        order_id = None
        oco_order_ids = []
        cantidad_acumulada = 0.0
        precio_entrada_promedio = 0.0

    except Exception as e:
        logging.error(f"Error al vender: {e}")
        enviar_mensaje(f"❌ Error al VENDER:\n{str(e)}")

def verificar_cierre_oco():
    global estado, oco_order_ids

    if not estado or not oco_order_ids:
        return

    cerradas = 0
    for oid in oco_order_ids:
        try:
            order = client.get_order(symbol=PARAMS['symbol'], orderId=oid)
            if order['status'] in ['FILLED', 'CANCELED', 'REJECTED', 'EXPIRED']:
                cerradas += 1
        except Exception as e:
            logging.warning(f"Error al verificar orden {oid}: {e}")

    if cerradas == len(oco_order_ids):
        estado = False
        oco_order_ids = []
        enviar_mensaje("📉 OCO ejecutado. Posición cerrada.")
