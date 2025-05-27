import os
import csv
from datetime import datetime
from notifier.telegram import enviar_mensaje

def enviar_resumen_diario(symbols):
    resumen = []
    total_usdt = 0.0

    for symbol in symbols:
        path = f"logs/operaciones_{symbol}.csv"
        if not os.path.exists(path):
            continue

        ganancia_total = 0.0
        rendimiento_total = 0.0
        operaciones = 0

        with open(path, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                timestamp = datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S")
                hoy = datetime.utcnow().date()
                if timestamp.date() == hoy:
                    ganancia_total += float(row["ganancia"])
                    rendimiento_total += float(row["rendimiento_pct"])
                    operaciones += 1

        if operaciones > 0:
            prom_rendimiento = rendimiento_total / operaciones
            total_usdt += ganancia_total
            resumen.append(f"{symbol}: {ganancia_total:+.2f} USDT ({prom_rendimiento:+.2f}%)")

    if not resumen:
        enviar_mensaje("📊 Resumen Diario: No hubo operaciones hoy.")
        return

    mensaje = "📊 Resumen Diario de Ganancias:\n\n"
    mensaje += "\n".join(resumen)
    mensaje += f"\n---------------------------\nTOTAL: {total_usdt:+.2f} USDT"
    enviar_mensaje(mensaje)
