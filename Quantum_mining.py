import hashlib
import random
import json
import time
from datetime import datetime
from ecdsa import SECP256k1, SigningKey
import requests

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

# Start mining for a specific Quantumgrafic ID
def start_mining():
    synchronize_ids()
    miner_id = input("Enter your Quantumgrafic ID to start mining: ")
    if miner_id not in miners:
        print("Quantumgrafic ID not found. Please register first.")
        return

    print(f"Mining started for Quantumgrafic ID: {miner_id}. Rewards will be paid every 10 minutes.")
    try:
        while True:
            time.sleep(600)  # Wait 10 minutes
            weather_data = fetch_weather_data()
            if weather_data:
                temperature = weather_data["current"]["temp"]
                reward = calculate_reward(temperature)
            else:
                reward = 3000  # Default reward if API fails

            miners[miner_id]["balance"] += reward
            miners[miner_id]["transactions"].append({
                "timestamp": datetime.now().isoformat(),
                "type": "reward",
                "amount": reward
            })
            save_json(MINERS_FILE, miners)
            print(f"Reward: {reward} Quantum Units added to Quantumgrafic ID: {miner_id}. Total Balance: {miners[miner_id]['balance']} Quantum Units.")
    except KeyboardInterrupt:
        print("\nMining stopped.")

# Register a new miner
def register_miner():
    private_key_hex = generate_private_key()
    public_key_hex = generate_public_key(private_key_hex)
    quantumgrafic_id = generate_checksum(public_key_hex)
    private_key_hash = hash_data(private_key_hex)

    synchronize_ids()

    if quantumgrafic_id in miners:
        print("Quantumgrafic ID already exists. Registration failed.")
        return

    miner_data = {
        "Quantumgrafic ID": quantumgrafic_id,
        "Public Key (Hex)": public_key_hex,
        "balance": 0.0,
        "transactions": []
    }

    miners[quantumgrafic_id] = miner_data
    register_to_core(quantumgrafic_id, public_key_hex, private_key_hash)
    save_json(MINERS_FILE, miners)

    print(f"Registration successful!")
    print(f"Quantumgrafic ID: {quantumgrafic_id}")
    print(f"Private Key: {private_key_hex} (Keep it safe!)")
    print(f"Public Key: {public_key_hex}")

# Login miner
def login_miner():
    synchronize_ids()
    miner_id = input("Enter your Quantumgrafic ID: ")
    if miner_id in miners:
        print(f"Welcome back, {miner_id}!")
    else:
        print("Quantumgrafic ID not found. Please register first.")

# Check balance
def check_balance():
    synchronize_ids()
    miner_id = input("Enter your Quantumgrafic ID: ")
    if miner_id in miners:
        print(f"Balance: {miners[miner_id]['balance']} Quantum Units")
    else:
        print("Quantumgrafic ID not found.")

# Make a transaction
def make_transaction():
    synchronize_ids()
    sender_id = input("Enter your Quantumgrafic ID: ")
    private_key = input("Enter your private key: ")

    if sender_id not in miners:
        print("Sender Quantumgrafic ID not found.")
        return

    if sender_id not in miners:
        print("Sender Quantumgrafic ID not found.")
        return

    receiver_id = input("Enter receiver's Quantumgrafic ID: ")
    if receiver_id not in miners:
        print("Receiver Quantumgrafic ID not found.")
        return

    try:
        amount = float(input("Enter amount to send: "))
    except ValueError:
        print("Invalid amount entered.")
        return

    if miners[sender_id]["balance"] < amount:
        print("Insufficient balance!")
        return

    miners[sender_id]["balance"] -= amount
    miners[receiver_id]["balance"] += amount

    transaction = {
        "timestamp": datetime.now().isoformat(),
        "from": sender_id,
        "to": receiver_id,
        "amount": amount
    }

    miners[sender_id]["transactions"].append(transaction)
    miners[receiver_id]["transactions"].append(transaction)
    quantum_core.setdefault("transactions", []).append(transaction)

    save_json(MINERS_FILE, miners)
    save_json(QUANTUM_CORE_FILE, quantum_core)

    print(f"Transaction successful. Sent {amount} Quantum Units to {receiver_id}.")

# Main menu
def main():
    while True:
        print("\n1. Log in")
        print("2. New Registration")
        print("3. Start Mining")
        print("4. Make a Transaction")
        print("5. Check Balance")
        print("6. Exit")

        choice = input("Choose an option: ")

        if choice == "1":
            login_miner()
        elif choice == "2":
            register_miner()
        elif choice == "3":
            start_mining()
        elif choice == "4":
            make_transaction()
        elif choice == "5":
            check_balance()
        elif choice == "6":
            exit(0)
        else:
            print("Invalid choice!")

if __name__ == "__main__":
    main()