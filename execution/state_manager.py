import json
import os

STATE_FILE = "bot_state.json"

# Estado inicial por defecto
default_state = {
    "posicion_abierta": False,
    "cantidad_acumulada": 0.0,
    "precio_entrada_promedio": 0.0,
    "oco_order_ids": []
}

def cargar_estado():
    if not os.path.exists(STATE_FILE):
        return default_state.copy()
    with open(STATE_FILE, "r") as f:
        return json.load(f)

def guardar_estado(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)
