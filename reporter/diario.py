import os
import csv
from datetime import datetime
from collections import defaultdict
from notifier.telegram import enviar_mensaje

LOG_FILE = "logs/operaciones.csv"

def enviar_resumen_diario():
    if not os.path.exists(LOG_FILE):
        enviar_mensaje("📊 Resumen Diario: No hubo operaciones hoy.")
        return

    resumen = defaultdict(lambda: {"ganancia": 0.0, "operaciones": 0})
    hoy = datetime.utcnow().date()
    operaciones_hoy = False

    try:
        with open(LOG_FILE, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                timestamp = datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S")
                if timestamp.date() == hoy:
                    operaciones_hoy = True
                    symbol = row["symbol"]
                    ganancia = float(row["ganancia"])
                    resumen[symbol]["ganancia"] += ganancia
                    resumen[symbol]["operaciones"] += 1

        if not operaciones_hoy:
            enviar_mensaje("📊 Resumen Diario: No hubo operaciones hoy.")
            return

        mensaje = "📈 *Resumen Diario de Operaciones*\n"
        total = 0.0
        for symbol, data in resumen.items():
            mensaje += f"\n• {symbol}: {data['operaciones']} ops | Ganancia: {data['ganancia']:.2f} USDT"
            total += data["ganancia"]

        mensaje += f"\n\n💵 *Ganancia Total:* {total:.2f} USDT"
        enviar_mensaje(mensaje)

    except Exception as e:
        enviar_mensaje(f"❌ Error al generar resumen diario:\n{str(e)}")
