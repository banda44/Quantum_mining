
        
from flask import Flask, render_template, request, jsonify
import hashlib
import random
import json
import time
from datetime import datetime
from threading import Thread
from ecdsa import SECP256k1, SigningKey
import requests
import hmac
import base64
import logging

app = Flask(__name__)

# Enable logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
MINERS_FILE = "miners.json"
QUANTUM_CORE_FILE = "quantum_core.json"
WEATHER_API_KEY = "ab43864527562dbd7373bb821635e60e"
LATITUDE = 41.9028  # Rome latitude
LONGITUDE = 12.4964  # Rome longitude
HMAC_SECRET_KEY = b"supersecurekey1234567890"  # Secret key for HMAC

# Constants
COINGECKO_API_URL = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
BTC_ADDRESS = "1J4fro3iTHH6XJEYwYqi1xSkoT3BaYoqtD"
BLOCKCHAIN_API_URL = "https://blockchain.info/rawblock/"
miners_source_file = "miners.json"
quantum_core_file = "quantum_core.json"
transactions = {}

# Active miners
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

def sign_reward(reward):
    """Securely sign rewards with HMAC."""
    reward_bytes = str(reward).encode()
    signature = hmac.new(HMAC_SECRET_KEY, reward_bytes, hashlib.sha256).digest()
    return base64.b64encode(signature).decode()


def verify_reward(reward, signature):
    """Verify reward signatures."""
    expected_signature = sign_reward(reward)
    return hmac.compare_digest(expected_signature, signature)

@app.route("/buy", methods=["GET", "POST"])
def buy_page():
    if request.method == "GET":
        return render_template("buy.html")

    elif request.method == "POST":
        quantumgrafic_id = request.form["quantumgrafic_id"]
        amount = float(request.form["amount"])

        # Validate Quantumgrafic ID
        miners_data = load_json(miners_source_file)
        if quantumgrafic_id not in miners_data:
            return jsonify({"error": "Invalid Quantumgrafic ID."})

        # Fetch live BTC price
        btc_price = get_live_btc_price()
        if btc_price is None:
            return jsonify({"error": "Unable to fetch BTC price. Try again later."})

        btc_to_pay = amount  # 1 Quantum Unit = 1 BTC (as per requirement)

        # Save transaction info
        transaction_id = str(int(time.time()))  # Unique transaction ID
        transactions[transaction_id] = {
            "quantumgrafic_id": quantumgrafic_id,
            "amount": amount,
            "btc_to_pay": btc_to_pay,
            "status": "pending"
        }

        return render_template(
            "confirm_buy.html",
            transaction_id=transaction_id,
            quantumgrafic_id=quantumgrafic_id,
            amount=amount,
            btc_price=btc_price,
            btc_to_pay=btc_to_pay,
            btc_address=BTC_ADDRESS
        )

@app.route("/confirm_transaction", methods=["POST"])
def confirm_transaction():
    transaction_id = request.form["transaction_id"]
    btc_transaction_hash = request.form["btc_transaction_hash"]

    # Validate transaction
    if transaction_id not in transactions:
        return jsonify({"error": "Invalid transaction ID."})

    transaction = transactions[transaction_id]
    btc_valid = validate_btc_transaction(btc_transaction_hash, BTC_ADDRESS, transaction["btc_to_pay"])

    if btc_valid:
        transaction["status"] = "completed"
        send_quantum_units(transaction["quantumgrafic_id"], transaction["amount"])
        return jsonify({"success": True, "message": "Quantum Units sent successfully."})
    else:
        return jsonify({"success": False, "message": "BTC transaction not valid or not confirmed."})

def get_live_btc_price():
    try:
        response = requests.get(COINGECKO_API_URL)
        if response.status_code == 200:
            data = response.json()
            return data["bitcoin"]["usd"]
    except Exception as e:
        print("Error fetching BTC price:", e)
    return None

def validate_btc_transaction(transaction_hash, expected_address, expected_amount):
    try:
        response = requests.get(f"{BLOCKCHAIN_API_URL}{transaction_hash}")
        if response.status_code == 200:
            data = response.json()
            for tx in data.get("tx", []):
                for out in tx.get("out", []):
                    if out.get("addr") == expected_address and out.get("value") / 1e8 >= expected_amount:
                        return True
    except Exception as e:
        print("Error validating BTC transaction:", e)
    return False

def send_quantum_units(quantumgrafic_id, amount):
    miners_data = load_json(miners_source_file)
    quantum_core_data = load_json(quantum_core_file)

    # Update miners.json
    if quantumgrafic_id in miners_data:
        miners_data[quantumgrafic_id]["balance"] = miners_data[quantumgrafic_id].get("balance", 0) + amount
        save_json(miners_source_file, miners_data)

    # Update quantum_core.json
    if quantumgrafic_id in quantum_core_data:
        quantum_core_data[quantumgrafic_id]["balance"] = quantum_core_data[quantumgrafic_id].get("balance", 0) + amount
    else:
        quantum_core_data[quantumgrafic_id] = {"balance": amount}

    save_json(quantum_core_file, quantum_core_data)
    print(f"Sent {amount} Quantum Units to Quantumgrafic ID: {quantumgrafic_id}")


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

@app.route("/view_transactions", methods=["GET", "POST"])
def view_transactions():
    miners = load_json(MINERS_FILE)
    quantum_core = load_json(QUANTUM_CORE_FILE)

    # Collect all transactions
    all_transactions = []

    # Get transactions from miners.json
    for miner_id, miner_data in miners.items():
        for tx in miner_data.get("transactions", []):
            all_transactions.append({
                "timestamp": tx.get("timestamp"),
                "miner_id": miner_id,
                "type": tx.get("type", "None"),
                "amount": tx.get("amount", 0),
                "signature": tx.get("signature", "None")
            })

    # Get transactions from quantum_core.json
    for tx in quantum_core.get("transactions", []):
        all_transactions.append({
            "timestamp": tx.get("timestamp"),
            "miner_id": "Quantum Core",
            "type": tx.get("type", "None"),
            "amount": tx.get("amount", 0),
            "signature": tx.get("signature", "None")
        })

    # Sort transactions by timestamp
    all_transactions.sort(key=lambda x: x["timestamp"], reverse=True)

    # Apply filters if POST request
    if request.method == "POST":
        filters = request.form
        miner_id = filters.get("miner_id", "").strip()
        tx_type = filters.get("type", "").strip()
        start_date = filters.get("start_date", "").strip()
        end_date = filters.get("end_date", "").strip()

        # Filter by Miner ID
        if miner_id:
            all_transactions = [tx for tx in all_transactions if tx["miner_id"] == miner_id]

        # Filter by Type
        if tx_type and tx_type.lower() != "all":
            all_transactions = [tx for tx in all_transactions if tx["type"].lower() == tx_type.lower()]

        # Filter by Date Range
        if start_date:
            all_transactions = [tx for tx in all_transactions if tx["timestamp"] >= start_date]
        if end_date:
            all_transactions = [tx for tx in all_transactions if tx["timestamp"] <= end_date]

    return render_template("view_transactions.html", transactions=all_transactions)





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

@app.route('/')
def index():
    return render_template('index.html')  # Ensure this matches your HTML filename


if __name__ == '__main__':
    app.run(debug=True)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)