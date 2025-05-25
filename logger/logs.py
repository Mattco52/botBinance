import os
import csv
from datetime import datetime

def log_operacion(symbol, precio, ganancia, rendimiento, razon):
    os.makedirs("logs", exist_ok=True)
    archivo = f"logs/operaciones_{symbol.upper()}.csv"
    nueva_fila = [
        datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
        round(precio, 2),
        round(ganancia, 2),
        round(rendimiento, 2),
        razon
    ]
    
    encabezado = ["timestamp", "precio", "ganancia", "rendimiento_pct", "razon"]

    archivo_existe = os.path.exists(archivo)
    
    with open(archivo, mode="a", newline="") as f:
        writer = csv.writer(f)
        if not archivo_existe:
            writer.writerow(encabezado)
        writer.writerow(nueva_fila)
