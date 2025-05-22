from flask import Flask, jsonify
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        "status": "Bot activo",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

@app.route('/status')
def status():
    return jsonify({
        "ok": True,
        "message": "Bot funcionando correctamente",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
