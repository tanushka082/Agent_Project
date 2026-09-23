# telemetry_adapter.py
import os
import requests
from ecu_database import get_pi_telemetry

# Switch flag: set to True when connected to Raspberry Pi hardware
HARDWARE_MODE = os.getenv("HARDWARE_MODE", "FALSE").upper() == "TRUE"
RASPBERRY_PI_SOVD_URL = "http://192.168.1.101:5001/get_telemetry"

def fetch_telemetry(target_dtc: str, requested_pids: list) -> dict:
    """
    Unified Telemetry Gateway:
    Routes PID queries to physical hardware (Raspberry Pi) or local ECU simulation.
    """
    if HARDWARE_MODE:
        print(f"\n [HARDWARE MODE] Routing SOVD request to Raspberry Pi ({RASPBERRY_PI_SOVD_URL})...")
        try:
            response = requests.post(
                RASPBERRY_PI_SOVD_URL,
                json={"dtc": target_dtc, "requested_pids": requested_pids},
                timeout=3.0
            )
            if response.status_code == 200:
                return response.json().get("telemetry", {})
        except Exception as e:
            print(f" [HARDWARE NETWORK ERROR] Could not reach Raspberry Pi: {e}")
            print(" └─ Falling back to local ECU simulation database...")

    # Default / Local Offline Simulation Mode
    print(f"\n [SIMULATION MODE] Fetching telemetry from local ECU Database...")
    sim_data = get_pi_telemetry(target_dtc, requested_pids)
    return sim_data["telemetry"]