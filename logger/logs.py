import os
import csv
from datetime import datetime

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "operaciones.csv")

# Asegurar que el directorio exista
os.makedirs(LOG_DIR, exist_ok=True)

# Columnas del CSV
ENCABEZADOS = [
    "timestamp", "symbol", "tipo",
    "precio_compra", "precio_venta",
    "ganancia", "rendimiento", "razon"
]

def log_operacion(symbol, precio_compra, precio_venta, ganancia, rendimiento, razon=""):
    """
    Registra una operación de venta en el archivo CSV con detalle completo.
    """
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    tipo = "VENTA"

    fila = [
        timestamp, symbol, tipo,
        f"{precio_compra:.2f}", f"{precio_venta:.2f}",
        f"{ganancia:.2f}", f"{rendimiento:.2f}%", razon
    ]

    try:
        archivo_nuevo = not os.path.exists(LOG_FILE)
        with open(LOG_FILE, "a", newline="") as f:
            writer = csv.writer(f)
            if archivo_nuevo:
                writer.writerow(ENCABEZADOS)
            writer.writerow(fila)
    except Exception as e:
        print(f"[ERROR] No se pudo guardar la operación: {e}")
