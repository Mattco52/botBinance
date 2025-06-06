import os
import json
import gspread
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials

# Alcance para Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Leer JSON de credenciales desde variable de entorno
json_creds = os.getenv("GOOGLE_CREDENTIALS_JSON")
if not json_creds:
    raise Exception("Falta GOOGLE_CREDENTIALS_JSON en las variables de entorno")

creds_dict = json.loads(json_creds)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gc = gspread.authorize(creds)

# Nombre de la hoja de cálculo desde variable de entorno
SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME", "OperacionesBot")
sheet = gc.open(SPREADSHEET_NAME).sheet1

# Encabezados esperados
ENCABEZADOS = ["timestamp", "symbol", "tipo", "precio_entrada", "precio_salida", "ganancia", "rendimiento", "razon"]

# Fila de prueba
def enviar_fila_test():
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    fila = [timestamp, "BTCUSDT", "VENTA", "10000.00", "10500.00", "500.00", "5.00%", "Test manual"]

    try:
        valores = sheet.row_values(1)
        if valores != ENCABEZADOS:
            sheet.insert_row(ENCABEZADOS, 1)

        sheet.append_row(fila)
        print("✅ Test exitoso: fila registrada en Google Sheets.")
    except Exception as e:
        print(f"❌ Error al registrar fila de test: {e}")

# Ejecutar test
enviar_fila_test()
