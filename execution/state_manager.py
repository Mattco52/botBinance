import json
import os

STATE_FILE = "bot_state.json"

default_state = {
    "estado": False,
    "order_id": None,
    "oco_order_ids": [],
    "cantidad_acumulada": 0.0,
    'precio_maximo': 0.0,
    "precio_entrada_promedio": 0.0,
    "ultima_compra_timestamp": None  # Nueva clave para evitar doble compra por vela
}

def cargar_estado():
    if not os.path.exists(STATE_FILE):
        guardar_estado(default_state.copy())
        return default_state.copy()

    try:
        with open(STATE_FILE, "r") as f:
            data = json.load(f)

        # Validar que tenga todas las claves necesarias
        for key in default_state:
            if key not in data:
                data[key] = default_state[key]
        return data

    except Exception as e:
        print(f"Error al cargar estado: {e}")
        return default_state.copy()

def guardar_estado(state):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f)
    except Exception as e:
        print(f"Error al guardar estado: {e}")
