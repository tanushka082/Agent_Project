import random
import time
import requests


# ============================================================
# CHANGE THIS TO YOUR LAPTOP IP ADDRESS
# ============================================================

LAPTOP_IP = "192.168.1.10"

AGENT_URL = f"http://{LAPTOP_IP}:8000/vehicle_event"


# ============================================================
# DTCs available in your ecu_database.py
# ============================================================

DTC_LIST = [
    "P0217",
    "P0300",
    "P0101",
    "P0113"
]


# ============================================================
# SEND RANDOM DTC
# ============================================================

def send_random_dtc():

    dtc = random.choice(DTC_LIST)

    payload = {
        "dtc": dtc,
        "source": "raspberry_pi"
    }

    print("\n========================================")
    print("[PI] Sending vehicle DTC")
    print(f"[PI] Selected DTC: {dtc}")
    print(f"[PI] Destination: {AGENT_URL}")

    try:

        response = requests.post(
            AGENT_URL,
            json=payload,
            timeout=5
        )

        print(f"[PI] Response status: {response.status_code}")
        print(f"[PI] Response: {response.text}")

    except requests.exceptions.ConnectionError:

        print("[PI ERROR] Could not connect to Agent.")
        print("[PI ERROR] Check:")
        print("          1. Laptop IP")
        print("          2. Agent server")
        print("          3. Network connection")

    except requests.exceptions.Timeout:

        print("[PI ERROR] Agent request timed out.")

    except Exception as e:

        print(f"[PI ERROR] {e}")

    print("========================================")


# ============================================================
# MAIN LOOP
# ============================================================

if __name__ == "__main__":

    print("========================================")
    print(" Raspberry Pi DTC Sender")
    print("========================================")

    print(f"Agent URL: {AGENT_URL}")
    print(f"DTCs available: {DTC_LIST}")
    print("Sending a random DTC every 10 seconds...")
    print("Press CTRL+C to stop.")
    print("")

    while True:

        send_random_dtc()

        time.sleep(10)