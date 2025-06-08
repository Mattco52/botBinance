import os
import gspread
import json
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials

# Autenticación con Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
json_creds = os.getenv("GOOGLE_CREDENTIALS_JSON")

if not json_creds:
    raise Exception("❌ Falta la variable de entorno GOOGLE_CREDENTIALS_JSON")

creds_dict = json.loads(json_creds)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gc = gspread.authorize(creds)

SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME", "TradingBotLogs")
sheet = gc.open(SPREADSHEET_NAME).sheet1

# Encabezados esperados
ENCABEZADOS = [
    "timestamp",
    "symbol",
    "precio_entrada",
    "precio_salida",
    "usdt_invertido",
    "usdt_recuperado",
    "ganancia",
    "rendimiento",
    "razon"
]

def log_operacion_google_sheets(symbol, precio_entrada, precio_salida, ganancia_total, ganancia_pct, razon="", cantidad=0.0):
    """
    Registra solo operaciones de VENTA en Google Sheets.
    """
    try:
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        usdt_invertido = round(precio_entrada * cantidad, 2)
        usdt_recuperado = round(precio_salida * cantidad, 2)

        fila = [
            timestamp,
            symbol,
            f"{precio_entrada:.2f}",
            f"{precio_salida:.2f}",
            usdt_invertido,
            usdt_recuperado,
            f"{ganancia_total:.2f}",
            f"{ganancia_pct:.2f}%",
            razon
        ]

        existing_headers = sheet.row_values(1)
        if existing_headers != ENCABEZADOS:
            sheet.insert_row(ENCABEZADOS, 1)

        sheet.append_row(fila)
        print(f"[GOOGLE SHEETS] ✅ VENTA registrada: {fila}")

    except Exception as e:
        print(f"[ERROR] ❌ No se pudo registrar en Sheets: {e}")