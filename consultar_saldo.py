from binance.client import Client
from dotenv import load_dotenv
import os

# Cargar variables del archivo .env
load_dotenv()
api_key = os.getenv("API_KEY")
secret_key = os.getenv("SECRET_KEY")

# Inicializar cliente en modo testnet
client = Client(api_key, secret_key, testnet=True)

def mostrar_saldo(moneda):
    cuenta = client.get_asset_balance(asset=moneda)
    if cuenta:
        disponible = cuenta.get('free')
        bloqueado = cuenta.get('locked')
        print(f"{moneda}: Disponible = {disponible}, Bloqueado = {bloqueado}")
    else:
        print(f"No se pudo obtener saldo para {moneda}.")

if __name__ == "__main__":
    print("📊 Saldos en cuenta TESTNET:")
    mostrar_saldo('BTC')
    mostrar_saldo('USDT')
