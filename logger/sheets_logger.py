import os
import gspread
import json
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials

# Definir el alcance
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Leer las credenciales desde variable de entorno
json_creds = os.getenv("GOOGLE_CREDENTIALS_JSON")
if not json_creds:
    raise Exception("❌ Falta la variable de entorno GOOGLE_CREDENTIALS_JSON")

creds_dict = json.loads(json_creds)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

# Autenticarse con Google Sheets
gc = gspread.authorize(creds)

# Leer nombre de hoja desde variable de entorno (por si se quiere cambiar)
SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME", "TradingBotLogs")
sheet = gc.open(SPREADSHEET_NAME).sheet1

# Encabezados esperados
ENCABEZADOS = [
    "timestamp",
    "symbol",
    "tipo",
    "precio_entrada",
    "precio_salida",
    "ganancia",
    "rendimiento",
    "razon"
]

def log_operacion_google_sheets(symbol, precio_entrada, precio_salida=None, ganancia_total=None, ganancia_pct=None, razon=""):
    """
    Registra una operación en Google Sheets.
    Si es compra, solo se pasa precio_entrada.
    Si es venta, se completa todo lo demás.
    """
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    tipo = "VENTA" if precio_salida else "COMPRA"

    fila = [
        timestamp,
        symbol,
        tipo,
        f"{precio_entrada:.2f}" if precio_entrada else "",
        f"{precio_salida:.2f}" if precio_salida else "",
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