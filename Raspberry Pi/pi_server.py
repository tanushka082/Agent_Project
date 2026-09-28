
from flask import Flask, request, jsonify
from ecu_database import ENGINE_DTC_DATABASE

app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    """Check whether Raspberry Pi ECU server is running."""
    return jsonify({
        "status": "online",
        "device": "Raspberry Pi ECU Gateway"
    })


@app.route("/get_telemetry", methods=["POST"])
def get_telemetry():
    """
    Receive a DTC + requested PIDs from the Agent
    and return the corresponding simulated ECU telemetry.
    """

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "No JSON data received"
        }), 400

    dtc = data.get("dtc")
    requested_pids = data.get("requested_pids", [])

    print("\n========================================")
    print("[PI ECU] Telemetry request received")
    print(f"[PI ECU] DTC: {dtc}")
    print(f"[PI ECU] Requested PIDs: {requested_pids}")

    # Check whether DTC exists
    if dtc not in ENGINE_DTC_DATABASE:

        print(f"[PI ECU] ERROR: DTC {dtc} not found")

        return jsonify({
            "error": f"DTC {dtc} not found in ECU database"
        }), 404

    # Get telemetry stored for this DTC
    available_telemetry = ENGINE_DTC_DATABASE[dtc]["telemetry"]

    # Return only the PIDs requested by the Data Planning Agent
    telemetry = {}

    for pid in requested_pids:

        if pid in available_telemetry:
            telemetry[pid] = available_telemetry[pid]

    print(f"[PI ECU] Returning telemetry:")
    print(telemetry)

    print("========================================\n")

    return jsonify({
        "dtc": dtc,
        "telemetry": telemetry
    })


if __name__ == "__main__":

    print("========================================")
    print(" Raspberry Pi ECU Telemetry Gateway")
    print("========================================")
    print("Server starting on port 5001...")
    print("Waiting for telemetry requests...")
    print("")

    app.run(
        host="0.0.0.0",
        port=5001,
        debug=False
    )