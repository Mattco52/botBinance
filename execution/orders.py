from binance.client import Client
from config.settings import PARAMS, API_KEY, SECRET_KEY, TESTNET
from notifier.telegram import enviar_mensaje
from execution.state_manager import cargar_estado, guardar_estado
from datetime import datetime
import logging

client = Client(API_KEY, SECRET_KEY, testnet=TESTNET)

# Cargar estado persistente
estado = cargar_estado()

def comprar(precio_actual, rsi):
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
        estado["order_id"] = order['orderId']
        estado["estado"] = True
        estado["cantidad_acumulada"] += PARAMS['quantity']

        # Recalcular promedio
        qty = PARAMS['quantity']
        old_qty = estado["cantidad_acumulada"] - qty
        old_avg = estado["precio_entrada_promedio"]
        estado["precio_entrada_promedio"] = (
            (old_avg * old_qty) + (precio_actual * qty)
        ) / estado["cantidad_acumulada"]

        enviar_mensaje("✅ Orden de COMPRA ejecutada")

        if PARAMS['use_oco']:
            tp = round(precio_actual * (1 + PARAMS['take_profit'] / 100), 2)
            sl = round(precio_actual * (1 - PARAMS['stop_loss'] / 100), 2)

            oco_order = client.create_oco_order(
                symbol=PARAMS['symbol'],
                side=Client.SIDE_SELL,
                quantity=round(estado["cantidad_acumulada"], 6),
                price=str(tp),
                stopPrice=str(sl),
                stopLimitPrice=str(sl),
                stopLimitTimeInForce='GTC',
                aboveType='STOP'
            )
            estado["oco_order_ids"] = [o['orderId'] for o in oco_order['orderReports']]
            enviar_mensaje(f"🔷 OCO configurado\nTP: {tp} | SL: {sl}")

        guardar_estado(estado)

    except Exception as e:
        logging.error(f"Error al comprar: {e}")
        enviar_mensaje(f"❌ Error al COMPRAR:\n{str(e)}")

comprar.estado = lambda: estado["estado"]  # Exponer estado actual

def vender(precio_actual, rsi, razon="Salida"):
    ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logging.info(f"[{ahora}] 🔴 Ejecutando VENTA | Precio: {precio_actual:.2f} | RSI: {rsi:.2f} | Motivo: {razon}")
    enviar_mensaje(f"🔴 Señal de VENTA\nPrecio: {precio_actual:.2f}\nRSI: {rsi:.2f}\nMotivo: {razon}")

    try:
        cantidad = round(estado["cantidad_acumulada"], 6)
        if cantidad <= 0:
            logging.warning("⚠️ No hay cantidad acumulada para vender. Cancelando venta.")
            enviar_mensaje("⚠️ No hay cantidad acumulada para vender. Venta cancelada.")
            return

        order = client.create_order(
            symbol=PARAMS['symbol'],
            side=Client.SIDE_SELL,
            type=Client.ORDER_TYPE_MARKET,
            quantity=cantidad
        )

        ganancia = round((precio_actual - estado["precio_entrada_promedio"]) * cantidad, 2)
        enviar_mensaje(f"✅ Venta ejecutada\n💰 Ganancia estimada: {ganancia} USDT")

        # 🔁 Reset del estado
        estado["estado"] = False
        estado["order_id"] = None
        estado["oco_order_ids"] = []
        estado["cantidad_acumulada"] = 0.0
        estado["precio_entrada_promedio"] = 0.0

        guardar_estado(estado)
        logging.info(f"[{ahora}] Estado reseteado tras venta. Estado actual: {estado}")

    except Exception as e:
        logging.error(f"Error al vender: {e}")
        enviar_mensaje(f"❌ Error al VENDER:\n{str(e)}")

def verificar_cierre_oco():
    if not estado["estado"] or not estado["oco_order_ids"]:
        return

    cerradas = 0
    for oid in estado["oco_order_ids"]:
        try:
            order = client.get_order(symbol=PARAMS['symbol'], orderId=oid)
            if order['status'] in ['FILLED', 'CANCELED', 'REJECTED', 'EXPIRED']:
                cerradas += 1
        except Exception as e:
            logging.warning(f"Error al verificar orden {oid}: {e}")

    if cerradas == len(estado["oco_order_ids"]):
        estado["estado"] = False
        estado["oco_order_ids"] = []
        guardar_estado(estado)
        enviar_mensaje("📉 OCO ejecutado. Posición cerrada.")
