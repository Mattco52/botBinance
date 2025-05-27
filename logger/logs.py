import os
import csv
from datetime import datetime
import logging

def log_operacion(symbol, precio, ganancia, rendimiento, razon):
    try:
        # Crear carpeta logs si no existe
        os.makedirs("logs", exist_ok=True)

        # Ruta del archivo CSV
        archivo = f"logs/operaciones_{symbol.upper()}.csv"

        # Fila a registrar
        nueva_fila = [
            datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
            round(precio, 2),
            round(ganancia, 2),
            round(rendimiento, 2),
            razon
        ]

        # Encabezados
        encabezado = ["timestamp", "precio", "ganancia", "rendimiento_pct", "razon"]

        # Verificar si el archivo ya existe
        archivo_existe = os.path.exists(archivo)

        # Escribir en el archivo
        with open(archivo, mode="a", newline="") as f:
            writer = csv.writer(f)
            if not archivo_existe:
                writer.writerow(encabezado)
            writer.writerow(nueva_fila)

        logging.info(f"[{symbol}] Log guardado: {nueva_fila}")

    except Exception as e:
        logging.error(f"[{symbol}] Error al guardar log: {e}")
