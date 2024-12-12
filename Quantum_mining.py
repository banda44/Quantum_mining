
from flask import Flask, render_template, request, jsonify
import hashlib
import random
import json
import time
from datetime import datetime
from threading import Thread
from ecdsa import SECP256k1, SigningKey
import requests
import logging

app = Flask(__name__)

# Enable logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Files to store data
MINERS_FILE = "miners.json"
QUANTUM_CORE_FILE = "quantum_core.json"
WEATHER_API_KEY = "ab43864527562dbd7373bb821635e60e"  # Replace with your OpenWeather API key
LATITUDE = 41.9028  # Rome latitude
LONGITUDE = 12.4964  # Rome longitude

# Active miners for live mining
active_miners = {}

# Utility functions
def load_json(file_name):
    try:
        with open(file_name, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def save_json(file_name, data):
    with open(file_name, 'w') as file:
        json.dump(data, file, indent=4)

def generate_private_key():
    return ''.join(random.choices('0123456789abcdef', k=64))

def generate_public_key(private_key_hex):
    private_key_bytes = bytes.fromhex(private_key_hex)
    private_key = SigningKey.from_string(private_key_bytes, curve=SECP256k1)
    public_key = private_key.get_verifying_key()
    return public_key.to_string().hex()

def generate_checksum(public_key_hex):
    return hashlib.sha256(bytes.fromhex(public_key_hex)).hexdigest()[:8]

def fetch_weather_data():
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={LATITUDE}&lon={LONGITUDE}&appid={WEATHER_API_KEY}&units=metric"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Error fetching weather data: {e}")
        return None

def calculate_reward(temperature):
    if temperature > 40:
        return 9
    elif temperature > 30:
        return 6
    elif temperature < 0:
        return 1.5
    else:
        return 3

# Mining loop
def mining_loop():
    while True:
        if active_miners:
            logger.info("Distributing rewards to active miners...")
            miners = load_json(MINERS_FILE)

            for miner_id in active_miners.keys():
                miner = miners.get(miner_id)
                if miner:
                    weather_data = fetch_weather_data()
                    if weather_data:
                        temperature = weather_data["main"]["temp"]
                        reward = calculate_reward(temperature)
                        miner["balance"] += reward
                        miner["transactions"].append({
                            "timestamp": datetime.now().isoformat(),
                            "type": "reward",
                            "amount": reward
                        })
                        logger.info(f"Rewarded {reward} Quantum Units to {miner_id}. New balance: {miner['balance']}")

            save_json(MINERS_FILE, miners)
        time.sleep(600)

# Routes
@app.route("/")
def home():
    return render_template("menu.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        private_key_hex = generate_private_key()
        public_key_hex = generate_public_key(private_key_hex)
        quantumgrafic_id = generate_checksum(public_key_hex)

        miners = load_json(MINERS_FILE)
        miner_data = {
            "Quantumgrafic ID": quantumgrafic_id,
            "Public Key (Hex)": public_key_hex,
            "Private Key (Hex)": private_key_hex,
            "balance": 0.0,
            "transactions": []
        }

        miners[quantumgrafic_id] = miner_data
        save_json(MINERS_FILE, miners)

        return jsonify({
            "message": "Registration successful!",
            "Quantumgrafic ID": quantumgrafic_id,
            "Private Key": private_key_hex,
            "Public Key": public_key_hex
        })
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        data = request.get_json()
        quantumgrafic_id = data.get("Quantumgrafic ID")
        miners = load_json(MINERS_FILE)

        if quantumgrafic_id in miners:
            return jsonify({"message": f"Welcome back, {quantumgrafic_id}!"})
        return jsonify({"message": "Quantumgrafic ID not found."}), 400
    return render_template("login.html")

@app.route("/start_mining", methods=["GET", "POST"])
def start_mining():
    if request.method == "POST":
        data = request.get_json()
        quantumgrafic_id = data.get("Quantumgrafic ID")

        miners = load_json(MINERS_FILE)
        if quantumgrafic_id not in miners:
            return jsonify({"message": "Quantumgrafic ID not found."}), 404

        active_miners[quantumgrafic_id] = True
        logger.info(f"Miner {quantumgrafic_id} started mining.")
        return jsonify({"message": f"Mining started for Quantumgrafic ID: {quantumgrafic_id}. Rewards will be paid every 10 minutes."})
    return render_template("mining.html")

@app.route("/check_balance", methods=["GET", "POST"])
def check_balance():
    if request.method == "POST":
        data = request.get_json()
        quantumgrafic_id = data.get("Quantumgrafic ID")

        miners = load_json(MINERS_FILE)
        miner = miners.get(quantumgrafic_id)
        if miner:
            return jsonify({"balance": miner["balance"]})
        return jsonify({"message": "Quantumgrafic ID not found."}), 404
    return render_template("check_balance.html")

@app.route("/make_transaction", methods=["GET", "POST"])
def make_transaction():
    if request.method == "POST":
        data = request.get_json()
        sender_id = data.get("sender_id")
        private_key = data.get("private_key")
        receiver_id = data.get("receiver_id")
        amount = data.get("amount")

        miners = load_json(MINERS_FILE)

        # Check if sender and receiver IDs exist
        if sender_id not in miners or receiver_id not in miners:
            return jsonify({"message": "Invalid sender or receiver Quantumgrafic ID."}), 404

        # Validate sender's private key
        if miners[sender_id]["Private Key (Hex)"] != private_key:
            return jsonify({"message": "Invalid private key for sender."}), 400

        # Check if sender has enough balance
        if miners[sender_id]["balance"] < amount:
            return jsonify({"message": "Insufficient balance."}), 400

        # Perform the transaction
        miners[sender_id]["balance"] -= amount
        miners[receiver_id]["balance"] += amount

        # Create a transaction record
        transaction = {
            "timestamp": datetime.now().isoformat(),
            "from": sender_id,
            "to": receiver_id,
            "amount": amount
        }

        # Append transaction to both sender and receiver
        miners[sender_id]["transactions"].append(transaction)
        miners[receiver_id]["transactions"].append(transaction)

        # Save updated data
        save_json(MINERS_FILE, miners)

        return jsonify({
            "message": f"Transaction successful! Sent {amount} Quantum Units to {receiver_id}.",
            "transaction": transaction
        })
    return render_template("make_transaction.html")

if __name__ == "__main__":
    mining_thread = Thread(target=mining_loop, daemon=True)
    mining_thread.start()
    app.run(debug=True)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

