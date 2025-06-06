import os
import gspread
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials

# Ruta al archivo JSON de credenciales
CREDENTIALS_FILE = "credentials.json"  # Asegúrate de subirlo a tu proyecto
SHEET_NAME = "OperacionesBot"      # Cambia al nombre real de tu hoja

def log_operacion_google_sheets(symbol, precio, ganancia, rendimiento, razon=""):
    try:
        # Autenticación con Google Sheets
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME).sheet1

        # Formato de fila
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        tipo = "VENTA" if ganancia is not None else "COMPRA"
        fila = [
            timestamp,
            symbol,
            tipo,
            round(precio, 4),
            f"{ganancia:.2f}" if ganancia is not None else "",
            f"{rendimiento:.2f}%" if rendimiento is not None else "",
            razon
        ]

        sheet.append_row(fila)
        print(f"[SHEETS] {tipo} registrada para {symbol}")

    except Exception as e:
        print(f"[ERROR] No se pudo registrar en Google Sheets: {e}")
