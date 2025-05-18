from dotenv import load_dotenv
import os
import requests

load_dotenv()

def enviar_mensaje_telegram(mensaje):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("CHAT_ID")
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": mensaje
    }

    try:
        response = requests.post(url, data=payload)
        print("✅ Mensaje enviado:", response.json())
    except Exception as e:
        print(f"❌ Error enviando mensaje Telegram: {e}")

# --- PRUEBA --- #
enviar_mensaje_telegram("🚀 Hola Matt")
