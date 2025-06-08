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
    "tipo",
    "precio_entrada",
    "precio_salida",
    "usdt_invertido",
    "usdt_recuperado",
    "ganancia",
    "rendimiento",
    "razon"
]

def log_operacion_google_sheets(symbol, precio_entrada, precio_salida=None, ganancia_total=None, ganancia_pct=None, razon="", cantidad=0.0):
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    tipo = "VENTA" if precio_salida else "COMPRA"

    usdt_invertido = round(precio_entrada * cantidad, 2) if tipo == "COMPRA" else ""
    usdt_recuperado = round(precio_salida * cantidad, 2) if tipo == "VENTA" else ""

    fila = [
        timestamp,
        symbol,
        tipo,
        f"{precio_entrada:.2f}" if precio_entrada else "",
        f"{precio_salida:.2f}" if precio_salida else "",
        usdt_invertido,
        usdt_recuperado,
        f"{ganancia_total:.2f}" if ganancia_total is not None else "",
        f"{ganancia_pct:.2f}%" if ganancia_pct is not None else "",
        razon
    ]

    try:
        existing_headers = sheet.row_values(1)
        if existing_headers != ENCABEZADOS:
            sheet.insert_row(ENCABEZADOS, 1)
        sheet.append_row(fila)
        print(f"[GOOGLE SHEETS] Operación registrada: {fila}")
    except Exception as e:
        print(f"[ERROR] No se pudo registrar en Sheets: {e}")