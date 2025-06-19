import threading
import time
import os
import schedule
from web.server import app
from strategy.strategy import ejecutar_estrategia
from notifier.logger import configurar_logger
from reporter.diario import enviar_resumen_diario  # ✅ Envío de resumen diario

# ✅ Lista de símbolos a operar (AVAXUSDT y BNBUSDT deshabilitados por bajo rendimiento) , "ETHUSDT", "SOLUSDT"
SYMBOLS = ["BTCUSDT"]

# ✅ Tiempo entre ciclos de ejecución por símbolo (en segundos)
SLEEP_TIME = 30

# ✅ Hilo de ejecución del bot por símbolo
def run_bot(symbol):
    while True:
        try:
            ejecutar_estrategia(symbol)
        except Exception as e:
            print(f"[ERROR] {symbol}: {e}")
        time.sleep(SLEEP_TIME)

# ✅ Hilo para enviar resumen diario a las 02:00 UTC
def run_resumen_diario():
    schedule.every().day.at("02:00").do(enviar_resumen_diario)
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    configurar_logger()
    
    # 🔄 Iniciar un hilo por cada símbolo
    for sym in SYMBOLS:
        t = threading.Thread(target=run_bot, args=(sym,), daemon=True)
        t.start()

    # 🗓 Iniciar hilo para enviar resumen diario automático
    threading.Thread(target=run_resumen_diario, daemon=True).start()

    # 🌐 Iniciar servidor Flask para interfaz web (si aplica)
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
