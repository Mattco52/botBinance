import os
from binance.client import Client
from dotenv import load_dotenv
import pandas as pd

# Cargar las API Keys desde .env
load_dotenv()
api_key = os.getenv("API_KEY")
secret_key = os.getenv("SECRET_KEY")
testnet = os.getenv("TESTNET", "True").lower() == "true"

client = Client(api_key, secret_key, testnet=testnet)

# Cambiar por el símbolo que te interese
symbol = 'BTCUSDT'

# Obtener historial de órdenes
ordenes = client.get_all_orders(symbol=symbol)

# Filtrar solo órdenes ejecutadas (FILLED)
ordenes_ejecutadas = [orden for orden in ordenes if orden['status'] == 'FILLED']

# Convertir a DataFrame para visualizar mejor
df = pd.DataFrame(ordenes_ejecutadas)

# Seleccionar columnas clave
columnas_interes = ['orderId', 'side', 'type', 'status', 'price', 'origQty', 'executedQty', 'time']
df = df[columnas_interes]

# Convertir el tiempo a formato legible
df['time'] = pd.to_datetime(df['time'], unit='ms')

# Mostrar
print(df)
