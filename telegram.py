import os
import requests
import logging
from config.settings import TELEGRAM_TOKEN, CHAT_ID

def enviar_mensaje(texto):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        logging.warning("⚠️ TELEGRAM_TOKEN o CHAT_ID no configurado.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": texto
    }

    try:
        response = requests.post(url, data=payload, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error enviando mensaje a Telegram: {e}")
