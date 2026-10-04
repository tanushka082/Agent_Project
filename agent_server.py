# event_listener.py
from flask import Flask, request, jsonify

app = Flask(__name__)

# Stores the latest DTC received from Raspberry Pi
LATEST_VEHICLE_EVENT = {}

@app.route("/vehicle_event", methods=["POST"])
def receive_vehicle_event():
    global LATEST_VEHICLE_EVENT
    data = request.get_json() or {}
    dtc = data.get("dtc", "")
    
    print(f"\n[UBUNTU AGENT] Received Live Event from Raspberry Pi!")
    print(f"[UBUNTU AGENT] Active DTC: {dtc} | Source: {data.get('source')}")
    
    LATEST_VEHICLE_EVENT = data
    return jsonify({"status": "acknowledged", "dtc": dtc}), 200

@app.route("/get_latest_event", methods=["GET"])
def get_latest_event():
    return jsonify(LATEST_VEHICLE_EVENT), 200

if __name__ == "__main__":
    # Host 0.0.0.0 allows external incoming connections from Raspberry Pi
    app.run(host="0.0.0.0", port=8000)
