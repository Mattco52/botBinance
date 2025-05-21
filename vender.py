from binance.client import Client
from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv("API_KEY")
secret_key = os.getenv("SECRET_KEY")
testnet = os.getenv("TESTNET", "True").lower() == "true"
client = Client(api_key, secret_key, testnet=testnet)

# Ejecutar venta de BTC
def vender_btc_testnet():
    try:
        cantidad = 1.009
        orden = client.create_order(
            symbol='BTCUSDT',
            side=Client.SIDE_SELL,
            type=Client.ORDER_TYPE_MARKET,
            quantity=cantidad
        )
        print(f"✅ Venta exitosa de {cantidad} BTC")
        print("Orden ID:", orden['orderId'])
    except Exception as e:
        print(f"❌ Error al vender BTC: {e}")

vender_btc_testnet()
