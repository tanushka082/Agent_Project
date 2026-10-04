# ecu_database.py
"""
Virtual ECU Database covering all 19 Powertrain DTCs from the Engine Excel dataset.
Categorized by ISO 26262 Safety Critical Status with telemetry keys aligned 
directly to OEM Nissan Service Manual abbreviations and PID nomenclature.
"""

ENGINE_DTC_DATABASE = {
    # =========================================================================
    # SAFETY CRITICAL FAULT CODES (Driveability, Torque Control, Engine Shutdown)
    # =========================================================================
    "P0217": {
        "description": "Engine Coolant Overtemperature Condition",
        "is_safety_critical": True,
        "telemetry": {
            "ECT_Voltage": 0.22,
            "Engine_Coolant_Temp": 118.0,
            "Coolant_Temperature": 118.0,
            "Cooling_Fan_Status": "HIGH",
            "Engine_RPM": 850
        }
    },
    "P0300": {
        "description": "Random/Multiple Cylinder Misfire Detected",
        "is_safety_critical": True,
        "telemetry": {
            "Engine_RPM": 720,
            "Misfire_Count_Total": 48,
            "CKP_Signal": "IRREGULAR",
            "Crank_Signal_Voltage": 2.1,
            "Vehicle_Speed": 0
        }
    },
    "P0301": {
        "description": "Cylinder 1 Misfire Detected",
        "is_safety_critical": True,
        "telemetry": {
            "Engine_RPM": 740,
            "Misfire_Cyl_1_Count": 35,
            "Ignition_Timing_Cyl1": 5.0,
            "Fuel_Injector_1_Pulse": 0.0
        }
    },
    "P0335": {
        "description": "Crankshaft Position Sensor (POS) Circuit",
        "is_safety_critical": True,
        "telemetry": {
            "Engine_RPM": 0,
            "POS_Signal": "NO_SIGNAL",
            "CKP_Sensor_V": 0.22,
            "Crank_Signal_Voltage": 0.22,
            "Battery_Voltage": 12.4
        }
    },
    "P0340": {
        "description": "Camshaft Position Sensor (PHASE) Circuit",
        "is_safety_critical": True,
        "telemetry": {
            "Engine_RPM": 680,
            "PHASE_Signal": "NO_SIGNAL",
            "CMP_Sensor_V": 0.18,
            "Cam_Signal_Voltage": 0.18,
            "Battery_Voltage": 12.5
        }
    },
    "P0500": {
        "description": "Vehicle Speed Sensor 'A' Circuit Malfunction",
        "is_safety_critical": True,
        "telemetry": {
            "VSS_Signal": 0,
            "Vehicle_Speed": 0,
            "Wheel_Speed_FL": 45.0,
            "Wheel_Speed_FR": 45.0,
            "Engine_RPM": 2200
        }
    },
    "P0605": {
        "description": "Internal Control Module Read Only Memory (ROM) Error",
        "is_safety_critical": True,
        "telemetry": {
            "ECM_ROM_Check": "FAILED",
            "ECM_Voltage": 12.5,
            "Battery_Voltage": 12.5,
            "Engine_RPM": 0
        }
    },
    "P2101": {
        "description": "Electric Throttle Control Function / Actuator Performance",
        "is_safety_critical": True,
        "telemetry": {
            "Engine_RPM": 0,
            "Throttle control motor_V": 0.45,
            "Throttle_Motor_Voltage": 0.45,
            "TP_Sensor_1_V": 0.80,
            "TP_Sensor_2_V": 4.20,
            "Throttle_Position": 5.0,
            "Battery_Voltage": 12.2
        }
    },

    # =========================================================================
    # NON-SAFETY CRITICAL FAULT CODES (Emissions, Fuel Trim, EVAP)
    # =========================================================================
    "P0101": {
        "description": "Mass Air Flow (MAF) Sensor Circuit Range/Performance",
        "is_safety_critical": False,
        "telemetry": {
            "Engine_RPM": 1200,
            "MAF_Voltage": 0.85,
            "MAF_Sensor_V": 0.85,
            "Mass_Air_Flow_Voltage": 0.85,
            "Air_Flow_Rate": 1.2,
            "Throttle_Position": 12.0
        }
    },
    "P0113": {
        "description": "Intake Air Temperature (IAT) Sensor Circuit High Input",
        "is_safety_critical": False,
        "telemetry": {
            "IAT_Voltage": 4.85,
            "IAT_Sensor_V": 4.85,
            "Intake_Air_Temp": -40.0,
            "Battery_Voltage": 12.6
        }
    },
    "P0117": {
        "description": "Engine Coolant Temperature (ECT) Sensor Circuit Low Input",
        "is_safety_critical": False,
        "telemetry": {
            "ECT_Voltage": 0.15,
            "ECT_Sensor_V": 0.15,
            "Engine_Coolant_Temp": 130.0,
            "Coolant_Temperature": 130.0
        }
    },
    "P0122": {
        "description": "Throttle/Pedal Position Sensor/Switch 'A' Circuit Low Input",
        "is_safety_critical": False,
        "telemetry": {
            "TP_Sensor_1_V": 0.20,
            "Throttle_Position_V": 0.20,
            "TPS_Voltage": 0.20,
            "Throttle_Position": 0.0,
            "Battery_Voltage": 12.4
        }
    },
    "P0132": {
        "description": "O2 Sensor Circuit High Voltage (Bank 1, Sensor 1)",
        "is_safety_critical": False,
        "telemetry": {
            "HO2S11_Voltage": 1.15,
            "O2_Sensor_Bank1_Sensor1": 1.15,
            "A/F_Sensor_Voltage": 1.15,
            "Engine_RPM": 2100
        }
    },
    "P0138": {
        "description": "O2 Sensor Circuit High Voltage (Bank 1, Sensor 2)",
        "is_safety_critical": False,
        "telemetry": {
            "HO2S12_Voltage": 1.22,
            "O2_Sensor_Bank1_Sensor2": 1.22,
            "Rear_O2_Voltage": 1.22,
            "Engine_RPM": 2000
        }
    },
    "P0171": {
        "description": "Fuel Trim System Too Lean (Bank 1)",
        "is_safety_critical": False,
        "telemetry": {
            "A/F_Alpha_B1": 135.0,
            "Short_Term_Fuel_Trim": 22.5,
            "Long_Term_Fuel_Trim": 18.0,
            "MAF_Voltage": 1.45,
            "Fuel_Pressure": 3.2
        }
    },
    "P0420": {
        "description": "Catalyst System Efficiency Below Threshold (Bank 1)",
        "is_safety_critical": False,
        "telemetry": {
            "HO2S11_Voltage": 0.45,
            "HO2S12_Voltage": 0.44,
            "O2_Sensor_Bank1_Sensor1": 0.45,
            "O2_Sensor_Bank1_Sensor2": 0.44,
            "Catalyst_Temp": 420.0
        }
    },
    "P0442": {
        "description": "EVAP Control System Leak Detected (Small Leak)",
        "is_safety_critical": False,
        "telemetry": {
            "EVAP_Pressure": -0.8,
            "Fuel_Tank_Pressure_V": 2.1,
            "Fuel_Pressure": 3.2,
            "Throttle_Position": 18.5,
            "Purge_Valve_Status": "CLOSED",
            "EVAP_Purge_Flow": 0.0
        }
    },
    "P0455": {
        "description": "EVAP Control System Leak Detected (Gross Leak)",
        "is_safety_critical": False,
        "telemetry": {
            "EVAP_Pressure": 0.0,
            "Fuel_Tank_Pressure_V": 3.8,
            "Fuel_Pressure": 3.1,
            "EVAP_Vent_Valve": "OPEN",
            "Purge_Volume_Control_V": 0.0
        }
    },
    "P0456": {
        "description": "EVAP Control System Leak Detected (Very Small Leak)",
        "is_safety_critical": False,
        "telemetry": {
            "EVAP_Pressure": -1.1,
            "Fuel_Tank_Pressure_V": 2.3,
            "Fuel_Pressure": 3.3,
            "Canister_Purge_Flow": 0.0,
            "Throttle_Position": 15.0
        }
    }
}


def _normalize_key(key: str) -> str:
    """Normalizes string keys for fuzzy matching (removes underscores, spaces, casing)."""
    return key.lower().replace("_", "").replace(" ", "").replace("-", "")

GLOBAL_BASELINE_TELEMETRY = {
    "Battery_Voltage": 12.4,
    "Engine_RPM": 750,
    "Vehicle_Speed": 0,
    "Coolant_Temperature": 90.0,
    "Throttle_Position": 0.0
}

def get_pi_telemetry(dtc_code: str, requested_pids: list = None) -> dict:
    dtc_info = ENGINE_DTC_DATABASE.get(dtc_code.upper(), {})
    telemetry_data = dtc_info.get("telemetry", {})

    if requested_pids:
        filtered_telemetry = {}
        for req_pid in requested_pids:
            # 1. Check exact DTC telemetry
            if req_pid in telemetry_data:
                filtered_telemetry[req_pid] = telemetry_data[req_pid]
            else:
                # 2. Fuzzy match inside DTC telemetry
                norm_req = _normalize_key(req_pid)
                match_found = False
                for db_pid, value in telemetry_data.items():
                    norm_db = _normalize_key(db_pid)
                    if norm_req == norm_db or norm_req in norm_db or norm_db in norm_req:
                        filtered_telemetry[req_pid] = value
                        match_found = True
                        break

                # 3. Check Global ECU Baselines (e.g. Battery_Voltage, Engine_RPM)
                if not match_found:
                    for base_pid, base_val in GLOBAL_BASELINE_TELEMETRY.items():
                        if norm_req == _normalize_key(base_pid):
                            filtered_telemetry[req_pid] = base_val
                            match_found = True
                            break

                # 4. Fallback if completely unmapped
                if not match_found:
                    filtered_telemetry[req_pid] = "PID_NOT_AVAILABLE"

        return {"telemetry": filtered_telemetry}

    return {"telemetry": telemetry_data}
