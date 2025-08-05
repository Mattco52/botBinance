import time
from binance.client import Client
from config.settings import API_KEY, SECRET_KEY, TESTNET, PARAMS
from notifier.telegram import enviar_mensaje
from execution.state_manager import guardar_estado
from logger.logs import log_operacion
from logger.sheets_logger import log_operacion_google_sheets
from utils.binance_filters import calcular_cantidad_valida

# Inicializar cliente Binance
client = Client(API_KEY, SECRET_KEY, testnet=TESTNET)

def comprar(precio_actual, rsi_actual, symbol, estado):
    cantidad = calcular_cantidad_valida(symbol, precio_actual)
    
    if not cantidad:
        enviar_mensaje(f"❌ [{symbol}] No se pudo calcular cantidad válida para compra.")
        return

    try:
        orden = client.order_market_buy(symbol=symbol, quantity=cantidad)
        order_id = orden["orderId"]

        estado.update({
            "estado": True,
            "order_id": order_id,
            "cantidad_acumulada": cantidad,
            "precio_entrada_promedio": precio_actual,
            "ultima_compra_timestamp": time.time(),
            "precio_maximo": precio_actual,
        })

        guardar_estado(symbol, estado)

        enviar_mensaje(f"🟢 [{symbol}] COMPRA ejecutada a {precio_actual:.2f} | RSI: {rsi_actual:.2f}")

    except Exception as e:
        enviar_mensaje(f"❌ [{symbol}] Error al ejecutar compra: {e}")
        print(f"[ERROR] [{symbol}] Error al comprar: {e}")

def vender(precio_actual, rsi_actual, symbol, estado, razon="Señal de venta"):
    cantidad = estado.get("cantidad_acumulada", 0.0)
    
    if cantidad <= 0:
        enviar_mensaje(f"❌ [{symbol}] No hay cantidad acumulada para vender.")
        return

    try:
        orden = client.order_market_sell(symbol=symbol, quantity=cantidad)

        precio_entrada = estado.get("precio_entrada_promedio", 0.0)
        ganancia_pct = ((precio_actual - precio_entrada) / precio_entrada) * 100
        ganancia_total = (precio_actual - precio_entrada) * cantidad

        # 🧾 Simular comisiones de compra y venta (0.075% + 0.075%)
        if PARAMS.get("simular_comisiones", False):
            costo_compra = precio_entrada * cantidad
            costo_venta = precio_actual * cantidad
            comision_total = (costo_compra + costo_venta) * 0.00075
            ganancia_total -= comision_total

        log_operacion(symbol, precio_entrada, precio_actual, ganancia_total, ganancia_pct, razon)
        log_operacion_google_sheets(
            symbol=symbol,
            precio_entrada=precio_entrada,
            precio_salida=precio_actual,
            ganancia_total=ganancia_total,
            ganancia_pct=ganancia_pct,
            razon=razon,
            cantidad=cantidad
        )

        mensaje = (
            f"🔴 [{symbol}] VENTA ejecutada a {precio_actual:.2f} | "
            f"RSI: {rsi_actual:.2f} | Razón: {razon} | "
            f"📈 Ganancia estimada: {ganancia_pct:.2f}%"
        )
        enviar_mensaje(mensaje)

        estado.update({
            "estado": False,
            "order_id": None,
            "cantidad_acumulada": 0.0,
            "precio_entrada_promedio": 0.0,
            "ultima_venta_timestamp": time.time(),
            "precio_maximo": 0.0,
        })

        guardar_estado(symbol, estado)

    except Exception as e:
        enviar_mensaje(f"❌ [{symbol}] Error al vender: {e}")
        print(f"[ERROR] [{symbol}] Error al vender: {e}")

def verificar_trailing_stop(symbol, precio_actual, estado, trailing_pct=0.003):
    if not estado.get("estado"):
        return False

    precio_entrada = estado.get("precio_entrada_promedio", 0.0)
    precio_maximo = estado.get("precio_maximo", precio_entrada)

    if precio_actual > precio_maximo:
        estado["precio_maximo"] = precio_actual
        guardar_estado(symbol, estado)

    if symbol == "ETHUSDT":
        break_even_trigger = 0.005
        if precio_actual >= precio_entrada * (1 + break_even_trigger):
            if precio_actual <= precio_entrada:
                return True

    if precio_actual <= precio_maximo * (1 - trailing_pct):
        return True

    return False

def verificar_cierre_oco(symbol, estado):
    if not estado.get("oco_order_ids"):
        return

    for oco_id in estado["oco_order_ids"]:
        try:
            orden = client.get_order(symbol=symbol, orderId=oco_id)
            if orden["status"] == "FILLED":
                precio_entrada = estado.get("precio_entrada_promedio", 0.0)
                precio_venta = float(orden["price"])
                cantidad = estado.get("cantidad_acumulada", 0.0)

                ganancia_pct = ((precio_venta - precio_entrada) / precio_entrada) * 100
                ganancia_total = (precio_venta - precio_entrada) * cantidad

                if PARAMS.get("simular_comisiones", False):
                    costo_compra = precio_entrada * cantidad
                    costo_venta = precio_venta * cantidad
                    comision_total = (costo_compra + costo_venta) * 0.00075
                    ganancia_total -= comision_total

                log_operacion(symbol, precio_entrada, precio_venta, ganancia_total, ganancia_pct, "OCO")
                log_operacion_google_sheets(
                    symbol=symbol,
                    precio_entrada=precio_entrada,
                    precio_salida=precio_venta,
                    ganancia_total=ganancia_total,
                    ganancia_pct=ganancia_pct,
                    razon="OCO",
                    cantidad=cantidad
                )

                mensaje = (
                    f"🔴 [{symbol}] OCO completada a {precio_venta:.2f} | "
                    f"📈 Ganancia estimada: {ganancia_pct:.2f}%"
                )
                enviar_mensaje(mensaje)

                estado.update({
                    "estado": False,
                    "oco_order_ids": [],
                    "cantidad_acumulada": 0.0,
                    "precio_entrada_promedio": 0.0,
                    "ultima_venta_timestamp": time.time(),
                    "precio_maximo": 0.0,
                })

                guardar_estado(symbol, estado)
                break

        except Exception as e:
            enviar_mensaje(f"❌ [{symbol}] Error al verificar OCO: {e}")
            print(f"[ERROR] Fallo al verificar OCO ({symbol}): {e}")
