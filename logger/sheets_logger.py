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
    raise Exception("Falta la variable de entorno GOOGLE_CREDENTIALS_JSON")

creds_dict = json.loads(json_creds)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

# Autenticarse con Google Sheets
gc = gspread.authorize(creds)

# Abrir hoja por nombre (asegúrate de haber compartido con el correo del servicio)
SPREADSHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "TradingBotLogs")
sheet = gc.open(SPREADSHEET_NAME).sheet1

# Encabezados si es hoja nueva
ENCABEZADOS = ["timestamp", "symbol", "tipo", "precio_entrada", "precio_salida", "ganancia", "rendimiento", "razon"]

def log_to_sheets(symbol, precio_entrada, precio_salida, ganancia_total, ganancia_pct, razon=""):
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    fila = [timestamp, symbol, "VENTA", f"{precio_entrada:.2f}", f"{precio_salida:.2f}", f"{ganancia_total:.2f}", f"{ganancia_pct:.2f}%", razon]
    
    try:
        if sheet.row_count == 0 or sheet.row_values(1) != ENCABEZADOS:
            sheet.insert_row(ENCABEZADOS, 1)
        sheet.append_row(fila)
        print(f"[GOOGLE SHEETS] Operación registrada: {fila}")
    except Exception as e:
        print(f"[ERROR] No se pudo registrar en Sheets: {e}")
