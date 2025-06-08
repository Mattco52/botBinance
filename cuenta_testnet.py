import os
from binance.client import Client
from config.settings import API_KEY, SECRET_KEY, TESTNET

# Instanciar cliente Binance
client = Client(API_KEY, SECRET_KEY, testnet=TESTNET)

# Monedas que quieres consultar
MONEDAS = ["BTC", "ETH", "BNB", "SOL", "AVAX", "USDT"]

def mostrar_saldos():
    try:
        cuenta = client.get_account()
        balances = cuenta["balances"]

        print("📊 SALDOS DISPONIBLES:\n")
        for moneda in MONEDAS:
            balance = next((b for b in balances if b["asset"] == moneda), None)
            if balance:
                free = float(balance["free"])
                locked = float(balance["locked"])
                total = free + locked
                print(f"🔹 {moneda}: Disponible = {free:.6f} | En uso = {locked:.6f} | Total = {total:.6f}")
            else:
                print(f"⚠️ {moneda}: No encontrado.")

    except Exception as e:
        print(f"❌ Error al obtener saldos: {e}")

if __name__ == "__main__":
    mostrar_saldos()