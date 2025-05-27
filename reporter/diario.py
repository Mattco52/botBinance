import os
import csv
from datetime import datetime
from notifier.telegram import enviar_mensaje

def enviar_resumen_diario(symbols):
    total_usdt = 0.0
    resumen = "📊 Resumen Diario de Ganancias:\n\n"

    for symbol in symbols:
        archivo = f"logs/operaciones_{symbol}.csv"
        ganancia_total = 0.0
        rendimiento_total = 0.0
        cantidad = 0

        if not os.path.exists(archivo):
            continue

        with open(archivo, "r") as f:
            reader = csv.DictReader(f)
            for fila in reader:
                fecha = fila["timestamp"][:10]
                hoy = datetime.utcnow().strftime("%Y-%m-%d")
                if fecha == hoy:
                    try:
                        ganancia_total += float(fila["ganancia"])
                        rendimiento_total += float(fila["rendimiento_pct"])
                        cantidad += 1
                    except:
                        continue

        if cantidad > 0:
            promedio_rend = rendimiento_total / cantidad
            resumen += f"{symbol}: {ganancia_total:.2f} USDT ({promedio_rend:.2f}%)\n"
            total_usdt += ganancia_total

    resumen += "\nTOTAL: {:.2f} USDT".format(total_usdt)
    enviar_mensaje(resumen)
