import time
from binance.client import Client
from config.settings import API_KEY, SECRET_KEY, TESTNET, PARAMS
from notifier.telegram import enviar_mensaje
from execution.state_manager import guardar_estado
from logger.logs import log_operacion  # CSV
from logger.sheets_logger import log_operacion_google_sheets  # Google Sheets

client = Client(API_KEY, SECRET_KEY, testnet=TESTNET)

def comprar(precio_actual, rsi_actual, symbol, estado):
    cantidad = PARAMS["quantity"]
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
    
    # ✅ Registrar solo entrada en Google Sheets con valores vacíos coherentes
    log_operacion_google_sheets(
        symbol=symbol,
        precio_entrada=precio_actual,
        precio_salida="",
        ganancia_total="",
        ganancia_pct="",
        razon="COMPRA"
    )

def vender(precio_actual, rsi_actual, symbol, estado, razon="Señal de venta"):
    cantidad = estado["cantidad_acumulada"]
    if cantidad <= 0:
        enviar_mensaje(f"❌ [{symbol}] No hay cantidad acumulada para vender.")
        return

    try:
        orden = client.order_market_sell(symbol=symbol, quantity=cantidad)

        precio_entrada = estado["precio_entrada_promedio"]
        ganancia_pct = ((precio_actual - precio_entrada) / precio_entrada) * 100
        ganancia_total = (precio_actual - precio_entrada) * cantidad

        # ✅ Registro en CSV y Google Sheets
        log_operacion(symbol, precio_entrada, precio_actual, ganancia_total, ganancia_pct, razon)
        log_operacion_google_sheets(symbol, precio_entrada, precio_actual, ganancia_total, ganancia_pct, razon)

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
        print(f"[ERROR] [{symbol}] Error al vender: {e}")
        enviar_mensaje(f"❌ [{symbol}] Error al vender: {e}")

def verificar_cierre_oco(symbol, estado):
    if not estado["oco_order_ids"]:
        return

    for oco_id in estado["oco_order_ids"]:
        try:
            orden = client.get_order(symbol=symbol, orderId=oco_id)
            if orden["status"] == "FILLED":
                precio_entrada = estado["precio_entrada_promedio"]
                precio_venta = float(orden["price"])
                ganancia_pct = ((precio_venta - precio_entrada) / precio_entrada) * 100
                ganancia_total = (precio_venta - precio_entrada) * estado["cantidad_acumulada"]

                # ✅ Registro en CSV y Sheets
                log_operacion(symbol, precio_entrada, precio_venta, ganancia_total, ganancia_pct, "OCO")
                log_operacion_google_sheets(symbol, precio_entrada, precio_venta, ganancia_total, ganancia_pct, "OCO")

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
            print(f"[ERROR] Fallo al verificar OCO ({symbol}): {e}")
            enviar_mensaje(f"❌ [{symbol}] Error al verificar OCO: {e}")