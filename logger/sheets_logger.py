import os
import gspread
import json
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials

# Alcance de permisos
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Leer las credenciales desde variable de entorno
json_creds = os.getenv("GOOGLE_CREDENTIALS_JSON")
if not json_creds:
    raise Exception("Falta la variable de entorno GOOGLE_CREDENTIALS_JSON")

# Convertir JSON a diccionario y crear credenciales
creds_dict = json.loads(json_creds)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gc = gspread.authorize(creds)

# Nombre del spreadsheet (debe existir y estar compartido con el service account)
SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME", "TradingBotLogs")
sheet = gc.open(SPREADSHEET_NAME).sheet1

# Encabezados
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

# Función para registrar operación
def log_operacion_google_sheets(symbol, precio_salida, ganancia_total, ganancia_pct, razon=""):
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    # Buscar última fila con compra si no hay salida
    tipo = "COMPRA" if ganancia_total is None else "VENTA"
    fila = [
        timestamp,
        symbol,
        tipo,
        f"{precio_salida:.2f}" if tipo == "COMPRA" else "",
        f"{precio_salida:.2f}" if tipo == "VENTA" else "",
        f"{ganancia_total:.2f}" if ganancia_total is not None else "",
        f"{ganancia_pct:.2f}%" if ganancia_pct is not None else "",
        razon or ""
    ]

    try:
        # Si la hoja está vacía, escribir encabezados
        if sheet.row_count == 0 or not sheet.row_values(1):
            sheet.insert_row(ENCABEZADOS, 1)

        sheet.append_row(fila)
        print(f"[GOOGLE SHEETS] Operación registrada: {fila}")
    except Exception as e:
        print(f"[ERROR] No se pudo registrar en Sheets: {e}")
