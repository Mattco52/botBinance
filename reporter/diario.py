import os
import json
import gspread
from datetime import datetime
from collections import defaultdict
from tempfile import NamedTemporaryFile
from oauth2client.service_account import ServiceAccountCredentials
from notifier.telegram import enviar_mensaje

# 📌 Configuración del archivo y hoja
SHEET_NAME = "OperacionesBot"
TABLA_LOGS = "TradingBotLogs"

# Columnas en tu hoja de cálculo
COL_TIMESTAMP = 0
COL_SYMBOL = 1
COL_GANANCIA = 6

# 🛡️ Autenticación segura desde entorno
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_json_str = os.getenv("GOOGLE_CREDS_JSON")

if not creds_json_str:
    raise ValueError("❌ Falta la variable de entorno GOOGLE_CREDS_JSON")

with NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as tmp_file:
    tmp_file.write(creds_json_str)
    tmp_file.flush()
    tmp_file_path = tmp_file.name

creds = ServiceAccountCredentials.from_json_keyfile_name(tmp_file_path, scope)
client = gspread.authorize(creds)

def enviar_resumen_diario():
    try:
        hoja = client.open(SHEET_NAME).worksheet(TABLA_LOGS)
        registros = hoja.get_all_values()[1:]  # saltar encabezado

        hoy = datetime.utcnow().date()
        resumen = defaultdict(lambda: {"ganancia": 0.0, "operaciones": 0})
        operaciones_hoy = False

        for fila in registros:
            try:
                ts = datetime.strptime(fila[COL_TIMESTAMP], "%Y-%m-%d %H:%M:%S").date()
                if ts != hoy:
                    continue

                symbol = fila[COL_SYMBOL]
                ganancia = float(fila[COL_GANANCIA])
                resumen[symbol]["ganancia"] += ganancia
                resumen[symbol]["operaciones"] += 1
                operaciones_hoy = True
            except:
                continue

        if not operaciones_hoy:
            enviar_mensaje("📊 Resumen Diario: No hubo operaciones hoy.")
            return

        mensaje = f"📈 *Resumen Diario de Operaciones*\n🗓 {hoy.strftime('%Y-%m-%d')}\n"
        total = 0.0

        for symbol, data in resumen.items():
            mensaje += (
                f"\n• {symbol}: {data['operaciones']} ops | "
                f"Ganancia: {'🟢' if data['ganancia'] >= 0 else '🔴'} {data['ganancia']:.2f} USDT"
            )
            total += data["ganancia"]

        mensaje += f"\n\n💵 *Ganancia Total:* {'🟢' if total >= 0 else '🔴'} {total:.2f} USDT"
        enviar_mensaje(mensaje)

    except Exception as e:
        enviar_mensaje(f"❌ Error en resumen diario:\n{str(e)}")

# 🧪 Permite ejecutar manualmente
if __name__ == "__main__":
    enviar_resumen_diario()
