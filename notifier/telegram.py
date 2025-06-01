import os
import requests

# Leer desde variables de entorno
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("CHAT_ID")

def enviar_mensaje(texto):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Faltan variables de entorno para Telegram.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": texto,
        "parse_mode": "MarkdownV2"
    }

    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            print(f"❌ Error al enviar mensaje: {response.text}")
    except Exception as e:
        print(f"❌ Excepción al enviar mensaje: {e}")
