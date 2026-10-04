# telemetry_adapter.py
import os
import requests
from Raspberry_Pi.ecu_database import ENGINE_DTC_DATABASE

HARDWARE_MODE = os.getenv("HARDWARE_MODE", "FALSE").upper() == "TRUE"
RASPBERRY_PI_BASE_URL = "http://172.20.10.2:5001" # Adjust IP/Port to match your Pi

def set_hardware_mode(enable: bool):
    global HARDWARE_MODE
    HARDWARE_MODE = enable



def fetch_active_dtc_from_rpi() -> str:
    """Queries Raspberry Pi Flask server (/get_telemetry) to fetch active DTC."""
    try:
        # Request active DTC via POST to /get_telemetry
        payload = {"dtc": "P0300", "requested_pids": []}
        response = requests.post(
            f"{RASPBERRY_PI_BASE_URL}/get_telemetry",
            json=payload,
            timeout=3.0
        )
        if response.status_code == 200:
            data = response.json()
            # Extract DTC returned by pi_server.py
            active_dtc = data.get("dtc", data.get("active_dtc", "P0300")).upper()
            return active_dtc
    except Exception as e:
        print(f" [HARDWARE ERROR] Failed to fetch active DTC from Raspberry Pi: {e}")
    return "NONE"


def fetch_telemetry(target_dtc: str, requested_pids: list) -> dict:
    if HARDWARE_MODE:
        try:
            response = requests.post(
                f"{RASPBERRY_PI_BASE_URL}/get_telemetry",
                json={"dtc": target_dtc, "requested_pids": requested_pids},
                timeout=3.0
            )
            if response.status_code == 200:
                return response.json().get("telemetry", {})
        except Exception as e:
            print(f" [HARDWARE WARNING] RPi SOVD Gateway unreachable ({e}). Falling back to ECU simulation.")

    dtc_entry = get_ecu_data_for_dtc(target_dtc)
    raw_telemetry = dtc_entry.get("telemetry", {})
    
    if not raw_telemetry:
        return {pid: "PID_NOT_AVAILABLE" for pid in requested_pids}
        
    result_telemetry = {}
    for pid in requested_pids:
        matched_val = None
        clean_pid = str(pid).lower().replace(" ", "").replace("_", "").replace("-", "").replace("/", "")
        
        for db_key, db_val in raw_telemetry.items():
            clean_db_key = str(db_key).lower().replace(" ", "").replace("_", "").replace("-", "").replace("/", "")
            if clean_pid in clean_db_key or clean_db_key in clean_pid:
                matched_val = db_val
                break
                
        result_telemetry[pid] = matched_val if matched_val is not None else "PID_NOT_AVAILABLE"
        
    return result_telemetry
