from binance.client import Client
from config.settings import PARAMS, API_KEY, SECRET_KEY, TESTNET
from notifier.telegram import enviar_mensaje
from execution.state_manager import guardar_estado
from logger.logs import log_operacion
from utils.binance_filters import cumple_min_notional  # ✅ NUEVO
from datetime import datetime
import logging

client = Client(API_KEY, SECRET_KEY, testnet=TESTNET)

def comprar(precio_actual, rsi, symbol, estado):
    ahora = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    logging.info(f"[{ahora}] [{symbol}] 🟢 Ejecutando COMPRA | Precio: {precio_actual:.2f} | RSI: {rsi:.2f}")
    enviar_mensaje(f"🟢 [{symbol}] Señal de COMPRA\nPrecio: {precio_actual:.2f}\nRSI: {rsi:.2f}")

    # ✅ Validar si cumple el mínimo NOTIONAL
    if not cumple_min_notional(symbol, precio_actual, PARAMS["quantity"]):
        enviar_mensaje(f"⚠️ [{symbol}] Orden cancelada: No cumple el mínimo NOTIONAL.")
        logging.warning(f"[{symbol}] Orden cancelada: Valor = {precio_actual * PARAMS['quantity']:.2f} < mínimo permitido.")
        return

    try:
        order = client.create_order(
            symbol=symbol,
            side=Client.SIDE_BUY,
            type=Client.ORDER_TYPE_MARKET,
            quantity=PARAMS['quantity']
        )

        estado["order_id"] = order['orderId']
        estado["estado"] = True
        estado["cantidad_acumulada"] += PARAMS['quantity']

        qty = PARAMS['quantity']
        old_qty = estado["cantidad_acumulada"] - qty
        old_avg = estado["precio_entrada_promedio"]
        estado["precio_entrada_promedio"] = (
            (old_avg * old_qty + precio_actual * qty) / estado["cantidad_acumulada"]
        )

        estado["ultima_compra_timestamp"] = ahora
        estado["precio_maximo"] = precio_actual

        enviar_mensaje(f"✅ [{symbol}] Orden de COMPRA ejecutada")

        if PARAMS['use_oco']:
            tp = round(precio_actual * (1 + PARAMS['take_profit'] / 100), 2)
            sl = round(precio_actual * (1 - PARAMS['stop_loss'] / 100), 2)

            oco_order = client.create_oco_order(
                symbol=symbol,
                side=Client.SIDE_SELL,
                quantity=round(estado["cantidad_acumulada"], 6),
                price=str(tp),
                stopPrice=str(sl),
                stopLimitPrice=str(sl),
                stopLimitTimeInForce='GTC'
            )
            estado["oco_order_ids"] = [o['orderId'] for o in oco_order['orderReports']]
            enviar_mensaje(f"🔷 [{symbol}] OCO configurado\nTP: {tp} | SL: {sl}")

        guardar_estado(symbol, estado)

    except Exception as e:
        logging.error(f"[{symbol}] Error al comprar: {e}")
        enviar_mensaje(f"❌ [{symbol}] Error al COMPRAR:\n{str(e)}")

def vender(precio_actual, rsi, symbol, estado, razon="Salida"):
    ahora = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    logging.info(f"[{ahora}] [{symbol}] 🔴 Ejecutando VENTA | Precio: {precio_actual:.2f} | RSI: {rsi:.2f} | Motivo: {razon}")
    enviar_mensaje(f"🔴 [{symbol}] Señal de VENTA\nPrecio: {precio_actual:.2f}\nRSI: {rsi:.2f}\nMotivo: {razon}")

    try:
        cantidad = round(estado["cantidad_acumulada"], 6)
        if cantidad <= 0:
            logging.warning(f"[{symbol}] ⚠️ No hay cantidad acumulada para vender.")
            enviar_mensaje(f"⚠️ [{symbol}] No hay cantidad acumulada para vender.")
            return

        order = client.create_order(
            symbol=symbol,
            side=Client.SIDE_SELL,
            type=Client.ORDER_TYPE_MARKET,
            quantity=cantidad
        )

        precio_entrada = estado["precio_entrada_promedio"]
        ganancia = round((precio_actual - precio_entrada) * cantidad, 2)
        rendimiento = round(((precio_actual - precio_entrada) / precio_entrada) * 100, 2)

        enviar_mensaje(
            f"✅ [{symbol}] Venta ejecutada\n"
            f"💰 Ganancia estimada: {ganancia} USDT\n"
            f"📈 Rendimiento: {rendimiento}%"
        )

        log_operacion(symbol, precio_actual, ganancia, rendimiento, razon)

        estado["estado"] = False
        estado["order_id"] = None
        estado["oco_order_ids"] = []
        estado["cantidad_acumulada"] = 0.0
        estado["precio_entrada_promedio"] = 0.0
        estado["ultima_compra_timestamp"] = None
        estado["ultima_venta_timestamp"] = ahora
        estado["precio_maximo"] = 0.0

        guardar_estado(symbol, estado)
        logging.info(f"[{ahora}] [{symbol}] Estado reseteado tras venta. Estado actual: {estado}")

    except Exception as e:
        logging.error(f"[{symbol}] Error al vender: {e}")
        enviar_mensaje(f"❌ [{symbol}] Error al VENDER:\n{str(e)}")

def verificar_cierre_oco(symbol, estado):
    if not estado["estado"] or not estado["oco_order_ids"]:
        return

    cerradas = 0
    for oid in estado["oco_order_ids"]:
        try:
            order = client.get_order(symbol=symbol, orderId=oid)
            if order['status'] in ['FILLED', 'CANCELED', 'REJECTED', 'EXPIRED']:
                cerradas += 1
        except Exception as e:
            logging.warning(f"[{symbol}] Error al verificar orden {oid}: {e}")

    if cerradas == len(estado["oco_order_ids"]):
        estado["estado"] = False
        estado["oco_order_ids"] = []
        guardar_estado(symbol, estado)
        enviar_mensaje(f"📉 [{symbol}] OCO ejecutado. Posición cerrada.")
