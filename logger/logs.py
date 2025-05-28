import os
import csv
from datetime import datetime

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "operaciones.csv")

# Asegurar que el directorio exista
os.makedirs(LOG_DIR, exist_ok=True)

# Columnas del CSV
ENCABEZADOS = ["timestamp", "symbol", "tipo", "precio", "ganancia", "rendimiento", "razon"]

def log_operacion(symbol, precio, ganancia, rendimiento, razon=""):
    """
    Registra una operación en el archivo CSV (logs/operaciones.csv)
    """
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    tipo = "VENTA"

    fila = [timestamp, symbol, tipo, precio, ganancia, f"{rendimiento}%", razon]

    try:
        archivo_nuevo = not os.path.exists(LOG_FILE)
        with open(LOG_FILE, "a", newline="") as f:
            writer = csv.writer(f)
            if archivo_nuevo:
                writer.writerow(ENCABEZADOS)
            writer.writerow(fila)
    except Exception as e:
        print(f"[ERROR] No se pudo guardar la operación: {e}")
