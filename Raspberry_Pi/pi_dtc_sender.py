# pi_dtc_sender.py (on Raspberry Pi)
import random
import time
import requests
# Import your central database directly
from ecu_database import ENGINE_DTC_DATABASE 

LAPTOP_IP = "172.20.10.3"  # Update with your laptop IP
AGENT_URL = f"http://{LAPTOP_IP}:8000/vehicle_event"

def send_active_dtc():
    # Dynamically grab all DTC keys directly from ecu_database
    available_dtcs = list(ENGINE_DTC_DATABASE.keys())
    
    if not available_dtcs:
        print("[PI ERROR] No DTCs found in ENGINE_DTC_DATABASE")
        return
        
    selected_dtc = random.choice(available_dtcs)
    
    payload = {
        "dtc": selected_dtc,
        "source": "raspberry_pi",
        "is_safety_critical": ENGINE_DTC_DATABASE[selected_dtc].get("is_safety_critical", False)
    }
    
    print(f"\n==========================================")
    print(f"[PI ECU] Transmitting Ground-Truth DTC: {selected_dtc}")
    print(f"==========================================")
    
    try:
        response = requests.post(AGENT_URL, json=payload, timeout=3.0)
        print(f"[PI ECU] Transmission Status: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("[PI ERROR] Could not connect to Laptop Agent.")
    except Exception as e:
        print(f"[PI ERROR] {e}")

if __name__ == "__main__":
    print("==========================================")
    print(" Raspberry Pi ECU DTC Broadcaster Active")
    print("==========================================")
    
    while True:
        send_active_dtc()
        time.sleep(10)  # Sends a new DTC from ecu_database every 10s
