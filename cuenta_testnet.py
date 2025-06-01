import os
from binance.client import Client
from config.settings import API_KEY, SECRET_KEY, TESTNET

# Cliente conectado al entorno testnet
client = Client(API_KEY, SECRET_KEY, testnet=TESTNET)

def mostrar_saldo():
    print("\n📊 Saldos disponibles en Testnet:\n")
    balances = client.get_account()["balances"]
    for asset in balances:
        free = float(asset["free"])
        locked = float(asset["locked"])
        if free > 0 or locked > 0:
            print(f"{asset['asset']}: Disponible={free}, Bloqueado={locked}")

def mostrar_trades(symbol):
    print(f"\n📘 Historial de operaciones para {symbol}:\n")
    trades = client.get_my_trades(symbol=symbol)
    if not trades:
        print("Sin operaciones.")
        return

    for t in trades:
        side = "BUY" if t['isBuyer'] else "SELL"
        print(f"• {side} | Cantidad: {t['qty']} | Precio: {t['price']} | Tiempo: {t['time']}")

if __name__ == "__main__":
    mostrar_saldo()

    # Reemplaza o agrega símbolos que te interesan
    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    for sym in symbols:
        mostrar_trades(sym)
