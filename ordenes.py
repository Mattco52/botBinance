import os
from binance.client import Client
from dotenv import load_dotenv

# Cargar claves API desde .env
load_dotenv()
api_key = os.getenv("API_KEY")
secret_key = os.getenv("SECRET_KEY")
testnet = os.getenv("TESTNET", "True").lower() == "true"

# Conexión con Binance
client = Client(api_key, secret_key, testnet=testnet)

# === Configura tus parámetros aquí === #
symbol = "BTCUSDT"
base_asset = "BTC"
quote_asset = "USDT"

# Obtener balances
def obtener_saldo(asset):
    cuenta = client.get_account()
    for balance in cuenta['balances']:
        if balance['asset'] == asset:
            return float(balance['free']) + float(balance['locked'])
    return 0.0

# Obtener precio actual del par
def obtener_precio_actual():
    ticker = client.get_symbol_ticker(symbol=symbol)
    return float(ticker['price'])

# Guardar saldos iniciales en un archivo la primera vez
archivo_saldos = "saldos_iniciales.txt"

def guardar_saldo_inicial(btc, usdt):
    with open(archivo_saldos, 'w') as f:
        f.write(f"{btc},{usdt}")

def cargar_saldo_inicial():
    if not os.path.exists(archivo_saldos):
        return None, None
    with open(archivo_saldos, 'r') as f:
        contenido = f.read()
        btc, usdt = contenido.strip().split(",")
        return float(btc), float(usdt)

# === PROCESO === #
btc_actual = obtener_saldo(base_asset)
usdt_actual = obtener_saldo(quote_asset)
precio_actual = obtener_precio_actual()

btc_ini, usdt_ini = cargar_saldo_inicial()

if btc_ini is None or usdt_ini is None:
    print("Primera ejecución: guardando saldos iniciales...")
    guardar_saldo_inicial(btc_actual, usdt_actual)
    print(f"Saldos guardados:\nBTC: {btc_actual:.6f}\nUSDT: {usdt_actual:.2f}")
else:
    print("=== SALDO INICIAL ===")
    print(f"BTC: {btc_ini:.6f}")
    print(f"USDT: {usdt_ini:.2f}")

    print("\n=== SALDO ACTUAL ===")
    print(f"BTC: {btc_actual:.6f}")
    print(f"USDT: {usdt_actual:.2f}")

    # Valor inicial y actual en USDT
    valor_inicial = btc_ini * precio_actual + usdt_ini
    valor_actual = btc_actual * precio_actual + usdt_actual
    ganancia = valor_actual - valor_inicial
    porcentaje = (ganancia / valor_inicial) * 100

    print("\n=== RESULTADO ESTIMADO ===")
    print(f"Precio BTC actual: {precio_actual:.2f} USDT")
    print(f"Valor inicial: {valor_inicial:.2f} USDT")
    print(f"Valor actual: {valor_actual:.2f} USDT")
    print(f"Ganancia/Pérdida: {ganancia:.2f} USDT ({porcentaje:.2f}%)")
