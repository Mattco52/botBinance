import threading
import time
import os
import schedule
from web.server import app
from strategy.strategy import ejecutar_estrategia
from notifier.logger import configurar_logger
from reporter.diario import enviar_resumen_diario  # ✅ NUEVO

# ✅ Lista de símbolos a operar
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT" ] # "AVAXUSDT",  "BNBUSDT" deshabilitados por baja rentabilidad

# ✅ Tiempo entre ciclos de estrategia
SLEEP_TIME = 30

# ✅ Hilo de ejecución del bot por símbolo
def run_bot(symbol):
    while True:
        try:
            ejecutar_estrategia(symbol)
        except Exception as e:
            print(f"[ERROR] {symbol}: {e}")
        time.sleep(SLEEP_TIME)

# ✅ Hilo para enviar resumen diario a las 23:59 UTC
def run_resumen_diario():
    schedule.every().day.at("02:00").do(enviar_resumen_diario, symbols=SYMBOLS)
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    configurar_logger()
    
    # 🔄 Iniciar hilo por cada símbolo
    for sym in SYMBOLS:
        t = threading.Thread(target=run_bot, args=(sym,), daemon=True)
        t.start()

    # 🔁 Iniciar hilo para resumen diario
    threading.Thread(target=run_resumen_diario, daemon=True).start()

    # 🌐 Ejecutar servidor Flask
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
