"""
Runs every experiment in experiments.py in sequence and prints a short
summary of each. Run from the project root:

    python3 -m src.experiments.runner

Each experiment saves its own CSV (data/generated/), plot
(results/figures/) and JSON summary (results/reports/); this script just
calls them in order and reports what happened.
"""

from src.experiments import experiments as exp


EXPERIMENTS = [
    ("01 - Temperature sensor calibration", exp.experiment_01_temperature_calibration),
    ("02 - Level sensor calibration", exp.experiment_02_level_calibration),
    ("03 - Flow sensor calibration", exp.experiment_03_flow_calibration),
    ("04 - Open-loop temperature response", exp.experiment_04_open_loop_temperature_response),
    ("05 - Closed-loop temperature control", exp.experiment_05_closed_loop_temperature_control),
    ("06 - Controller tuning report", exp.experiment_06_controller_tuning_report),
    ("07 - Temperature disturbance rejection", exp.experiment_07_temperature_disturbance_rejection),
    ("08 - Closed-loop level control", exp.experiment_08_closed_loop_level_control),
    ("09 - Level disturbance rejection", exp.experiment_09_level_disturbance_rejection),
    ("10 - Coupled full-system operation", exp.experiment_10_coupled_full_system),
    ("11 - P vs PI vs PID comparison", exp.experiment_11_p_pi_pid_comparison),
]


def run_all():
    results = {}
    for title, fn in EXPERIMENTS:
        print(f"Running {title} ...")
        result = fn()
        results[title] = result
        for key, value in result["summary"].items():
            if key in ("experiment", "comparison", "temperature_model", "level_model",
                        "temperature_pid_gains_identified", "temperature_pid_gains_in_use",
                        "level_pi_gains_identified", "level_pi_gains_in_use", "note"):
                continue
            if isinstance(value, float):
                print(f"    {key}: {value:.4g}")
            else:
                print(f"    {key}: {value}")
        print(f"    saved: {list(result['paths'].values())}")
        print()
    return results


if __name__ == "__main__":
    run_all()
