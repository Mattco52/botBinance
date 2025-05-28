import os
import json

STATE_DIR = "state"

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

def ruta_estado(symbol):
    if not os.path.exists(STATE_DIR):
        os.makedirs(STATE_DIR)
    return os.path.join(STATE_DIR, f"{symbol}_estado.json")

def cargar_estado(symbol):
    path = ruta_estado(symbol)
    if not os.path.exists(path):
        guardar_estado(symbol, default_state.copy())
        return default_state.copy()
    try:
        with open(path, "r") as f:
            estado = json.load(f)
        for key in default_state:
            if key not in estado:
                estado[key] = default_state[key]
        return estado
    except Exception as e:
        print(f"[ERROR] No se pudo cargar el estado de {symbol}: {e}")
        return default_state.copy()

def guardar_estado(symbol, estado):
    path = ruta_estado(symbol)
    try:
        with open(path, "w") as f:
            json.dump(estado, f, indent=4)
    except Exception as e:
        print(f"[ERROR] No se pudo guardar el estado de {symbol}: {e}")
