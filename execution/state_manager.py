import json
import os

BASE_STATE_FILE = "bot_state_{}.json"

default_state = {
    "estado": False,
    "order_id": None,
    "oco_order_ids": [],
    "cantidad_acumulada": 0.0,
    "precio_entrada_promedio": 0.0,
    "ultima_compra_timestamp": None,
    "ultima_venta_timestamp": None,
    "precio_maximo": 0.0
}

def get_state_file(symbol):
    return BASE_STATE_FILE.format(symbol.upper())

def cargar_estado(symbol):
    path = get_state_file(symbol)
    if not os.path.exists(path):
        guardar_estado(symbol, default_state.copy())
        return default_state.copy()

    try:
        with open(path, "r") as f:
            data = json.load(f)

        # Asegurar que todas las claves estén presentes
        for key in default_state:
            if key not in data:
                data[key] = default_state[key]

        return data

    except Exception as e:
        print(f"Error al cargar estado para {symbol}: {e}")
        return default_state.copy()

def guardar_estado(symbol, state):
    path = get_state_file(symbol)
    try:
        with open(path, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"Error al guardar estado para {symbol}: {e}")
