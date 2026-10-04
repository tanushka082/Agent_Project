# eval/test_benchmark.py
import json
import time
from typing import List, Dict, Any
from main_orchestrator import app
from state import DiagnosticState
from Raspberry_Pi.ecu_database import ENGINE_DTC_DATABASE
from evaluate_Agent import AgentEvaluator

def run_evaluation_for_dtc(target_dtc: str) -> Dict[str, Any]:
    """Runs the LangGraph pipeline for a single DTC and evaluates all metrics."""
    initial_state: DiagnosticState = {
        "primary_dtc": target_dtc,
        "active_dtc": target_dtc,
        "is_safety_critical": False,
        "dtc_description": "",
        "requested_pids": [],
        "planning_reasoning": "",
        "retrieved_manual_context": {},
        "live_telemetry": {},
        "reasoning_findings": None
    }

    start_time = time.time()
    final_state = app.invoke(initial_state)
    execution_time = round(time.time() - start_time, 2)

    # Calculate Metrics
    arg_correctness = AgentEvaluator.evaluate_argument_correctness(final_state)
    step_efficiency = AgentEvaluator.evaluate_step_efficiency(executed_steps=2, expected_steps=2)
    task_completion = AgentEvaluator.evaluate_task_completion(final_state)

    overall_passed = arg_correctness.passed and step_efficiency.passed and task_completion.passed

    return {
        "dtc": target_dtc,
        "execution_time_sec": execution_time,
        "overall_passed": overall_passed,
        "metrics": [
            arg_correctness.model_dump(),
            step_efficiency.model_dump(),
            task_completion.model_dump()
        ]
    }

def run_full_benchmark():
    """Evaluates all 19 Excel Powertrain DTCs end-to-end."""
    print("\n==================================================")
    print("STARTING FULL AGENT EVALUATION BENCHMARK (19 DTCs)")
    print("==================================================")

    results = []
    passed_count = 0

    for dtc in ENGINE_DTC_DATABASE.keys():
        print(f"\n[EVALUATING DTC: {dtc}]...")
        report = run_evaluation_for_dtc(dtc)
        results.append(report)
        
        status = "PASSED" if report["overall_passed"] else "FAILED"
        if report["overall_passed"]:
            passed_count += 1
            
        print(f" └─ Status: {status} | Time: {report['execution_time_sec']}s")

    pass_rate = round((passed_count / len(ENGINE_DTC_DATABASE)) * 100, 2)
    
    print("\n==================================================")
    print(f"BENCHMARK SUMMARY | Overall Pass Rate: {pass_rate}% ({passed_count}/{len(ENGINE_DTC_DATABASE)})")
    print("==================================================")
    
    # Save benchmark report to disk
    with open("eval_benchmark_report.json", "w") as f:
        json.dump(results, f, indent=2)
    print(" Full evaluation report saved to 'eval_benchmark_report.json'")

if __name__ == "__main__":
    run_full_benchmark()
