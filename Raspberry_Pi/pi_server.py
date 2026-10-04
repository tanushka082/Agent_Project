# pi_server.py (on Raspberry Pi)
from flask import Flask, request, jsonify
import random
from ecu_database import ENGINE_DTC_DATABASE, get_ecu_data_for_dtc

app = Flask(__name__)

# Global active fault registered on the Pi ECU
ACTIVE_HARDWARE_DTC = "P0300"

@app.route("/get_telemetry", methods=["POST"])
def get_telemetry():
    global ACTIVE_HARDWARE_DTC
    data = request.get_json() or {}
    
    # Target DTC from request or default active fault
    dtc = data.get("dtc") or ACTIVE_HARDWARE_DTC
    requested_pids = data.get("requested_pids", [])
    
    print(f"\n==========================================")
    print(f"[PI ECU] Telemetry Request Received")
    print(f"[PI ECU] Active DTC: {dtc}")
    print(f"[PI ECU] Requested PIDs: {requested_pids}")
    
    # Retrieve ground-truth entry directly from ecu_database
    ecu_entry = get_ecu_data_for_dtc(dtc)
    available_telemetry = ecu_entry.get("telemetry", {})
    
    # Filter requested PIDs against ecu_database telemetry
    returned_telemetry = {}
    for pid in requested_pids:
        # Fuzzy match key lookup against database
        clean_pid = str(pid).lower().replace("_", "").replace(" ", "")
        matched_val = None
        for db_key, db_val in available_telemetry.items():
            clean_db_key = str(db_key).lower().replace("_", "").replace(" ", "")
            if clean_pid in clean_db_key or clean_db_key in clean_pid:
                matched_val = db_val
                break
        returned_telemetry[pid] = matched_val if matched_val is not None else "PID_NOT_AVAILABLE"

    print(f"[PI ECU] Returning Telemetry: {returned_telemetry}")
    print(f"==========================================")
    
    return jsonify({
        "status": "success",
        "dtc": dtc,
        "is_safety_critical": ecu_entry.get("is_safety_critical", False),
        "telemetry": returned_telemetry
    }), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
