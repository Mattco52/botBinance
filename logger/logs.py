import csv
import os
from datetime import datetime

LOG_DIR = "logs"

def log_operacion(symbol, precio_venta, ganancia, rendimiento, razon):
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    fecha = datetime.utcnow().strftime('%Y-%m-%d')
    archivo = os.path.join(LOG_DIR, f"{fecha}.csv")

    nueva_fila = {
        "timestamp": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
        "symbol": symbol,
        "precio_venta": precio_venta,
        "ganancia": ganancia,
        "rendimiento_%": rendimiento,
        "motivo": razon
    }

    escribir_cabecera = not os.path.exists(archivo)

    with open(archivo, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=nueva_fila.keys())
        if escribir_cabecera:
            writer.writeheader()
        writer.writerow(nueva_fila)
