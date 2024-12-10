from flask import Flask, jsonify
import hashlib
import random
import json
import time
from datetime import datetime
from ecdsa import SECP256k1, SigningKey
import requests

# Create Flask app instance
app = Flask(__name__)

# Files to store data
MINERS_FILE = "miners.json"
QUANTUM_CORE_FILE = "quantum_core.json"
WEATHER_API_KEY = "your_weather_api_key_here"  # Replace with your OpenWeather API key
LATITUDE = 41.9028  # Rome latitude
LONGITUDE = 12.4964  # Rome longitude

# Load JSON data from a file
def load_json(file_name):
    try:
        with open(file_name, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

# Save JSON data to a file
def save_json(file_name, data):
    with open(file_name, 'w') as file:
        json.dump(data, file, indent=4)

# Hash data
def hash_data(data):
    return hashlib.sha256(data.encode()).hexdigest()

# Load miners and quantum core data
miners = load_json(MINERS_FILE)
quantum_core = load_json(QUANTUM_CORE_FILE)

# Generate a random private key (in hex)
def generate_private_key():
    return ''.join(random.choices('0123456789abcdef', k=64))

# Generate a public key from the private key
def generate_public_key(private_key_hex):
    private_key_bytes = bytes.fromhex(private_key_hex)
    private_key = SigningKey.from_string(private_key_bytes, curve=SECP256k1)
    public_key = private_key.get_verifying_key()
    return public_key.to_string().hex()

# Generate a checksum for Quantumgrafic ID
def generate_checksum(public_key_hex):
    return hashlib.sha256(bytes.fromhex(public_key_hex)).hexdigest()[:8]

# Register miner to quantum core
def register_to_core(quantumgrafic_id, public_key, private_key_hash):
    miner_data = {
        "Quantumgrafic ID": quantumgrafic_id,
        "Public Key (Hex)": public_key,
        "Private Key Hash": private_key_hash
    }
    quantum_core.setdefault("miners", []).append(miner_data)
    save_json(QUANTUM_CORE_FILE, quantum_core)

# Ensure all registered Quantumgrafic IDs are recognized
def synchronize_ids():
    core_ids = [miner["Quantumgrafic ID"] for miner in quantum_core.get("miners", [])]
    miner_ids = list(miners.keys())

    # Add missing IDs to miners.json
    for quantum_id in core_ids:
        if quantum_id not in miner_ids:
            for miner in quantum_core.get("miners", []):
                if miner["Quantumgrafic ID"] == quantum_id:
                    miners[quantum_id] = {
                        "Quantumgrafic ID": quantum_id,
                        "Public Key (Hex)": miner["Public Key (Hex)"],
                        "balance": 0.0,
                        "transactions": []
                    }
                    save_json(MINERS_FILE, miners)

# Fetch weather data
def fetch_weather_data():
    url = f"https://api.openweathermap.org/data/3.0/onecall?lat={LATITUDE}&lon={LONGITUDE}&exclude=minutely,hourly,daily,alerts&appid={WEATHER_API_KEY}&units=metric"
    response = requests.get(url)
    return response.json() if response.status_code == 200 else None

# Calculate mining reward
def calculate_reward(temperature):
    if temperature > 40:
        return 9
    elif temperature > 30:
        return 6
    elif temperature < 0:
        return 1.5
    else:
        return 3

# Flask Routes
@app.route("/")
def home():
    return "Quantum Mining System is Live!"

@app.route("/menu", methods=["GET"])
def main_menu():
    return jsonify({
        "menu": [
            "1. Log in",
            "2. New Registration",
            "3. Start Mining",
            "4. Make a Transaction",
            "5. Check Balance",
            "6. Exit"
        ]
    })

@app.route("/register", methods=["POST"])
def register_route():
    private_key_hex = generate_private_key()
    public_key_hex = generate_public_key(private_key_hex)
    quantumgrafic_id = generate_checksum(public_key_hex)
    private_key_hash = hash_data(private_key_hex)

    if quantumgrafic_id in miners:
        return jsonify({"message": "Quantumgrafic ID already exists."}), 400

    miner_data = {
        "Quantumgrafic ID": quantumgrafic_id,
        "Public Key (Hex)": public_key_hex,
        "balance": 0.0,
        "transactions": []
    }
    miners[quantumgrafic_id] = miner_data
    register_to_core(quantumgrafic_id, public_key_hex, private_key_hash)
    save_json(MINERS_FILE, miners)

    return jsonify({
        "message": "Registration successful!",
        "Quantumgrafic ID": quantumgrafic_id,
        "Private Key": private_key_hex,
        "Public Key": public_key_hex
    })

if __name__ == "__main__":
    from waitress import serve
    serve(app, host="0.0.0.0", port=8000)
