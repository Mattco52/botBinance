import threading
import time
from web.server import app
from strategy.strategy import ejecutar_estrategia
from notifier.logger import configurar_logger
import os

# ✅ Lista de símbolos a operar
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "AVAXUSDT"]

# ✅ Tiempo entre ciclos (se puede personalizar por símbolo si querés)
SLEEP_TIME = 30

# ✅ Hilo por símbolo
def run_bot(symbol):
    while True:
        try:
            ejecutar_estrategia(symbol)
        except Exception as e:
            print(f"[ERROR] {symbol}: {e}")
        time.sleep(SLEEP_TIME)

if __name__ == "__main__":
    configurar_logger()
    
    # ✅ Iniciar un hilo por símbolo
    for sym in SYMBOLS:
        t = threading.Thread(target=run_bot, args=(sym,), daemon=True)
        t.start()

    # ✅ Ejecutar el servidor Flask
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
