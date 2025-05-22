import threading
import time
from web.server import app
from strategy.strategy import ejecutar_estrategia
from notifier.logger import configurar_logger
from config.settings import PARAMS
import os

def run_bot():
    while True:
        ejecutar_estrategia()
        time.sleep(PARAMS['sleep_time'])

if __name__ == "__main__":
    configurar_logger()
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
