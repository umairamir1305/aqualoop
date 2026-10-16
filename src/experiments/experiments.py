"""
The Aqualoop experiment suite.

Each function here is one self-contained experiment: it configures the
plant and instruments it needs, runs the simulation, computes metrics
from the actual output, and saves a CSV, a plot and a JSON summary
through src/experiments/saving.py. Nothing here is hand-drawn; every
number and every curve comes out of src/simulation/engine.py or the
sensor/calibration/control modules it calls.

All data produced here is SIMULATED DATA. See src/instrumentation/calibration.py
for why that label matters for the calibration experiments in particular.
"""

import numpy as np
import matplotlib.pyplot as plt

from src.simulation.configuration import AqualoopConfig
from src.simulation.engine import build_handles, run_simulation, combine_on_step
from src.simulation.disturbances import Disturbance, DisturbanceSchedule
from src.simulation.faults import Fault, FaultSchedule
from src.instrumentation.calibration import calibrate_linear, generate_simulated_calibration_data
from src.instrumentation.temperature_sensor import TemperatureSensor
from src.instrumentation.level_sensor import LevelSensor
from src.instrumentation.flow_sensor import FlowSensor
from src.control.tuning import identify_foprd, pid_from_foprd, pi_from_foprd
from src.control.pid import PIDController
from src.control.pi import PIController
from src.analysis.metrics import compute_step_metrics, disturbance_recovery_time
from src.experiments.saving import save_outputs


# ---------------------------------------------------------------------------
# 1-3: sensor calibration
# ---------------------------------------------------------------------------

def _run_calibration_experiment(name, sensor, reference_values, unit_label, display_name):
    reference, measured = generate_simulated_calibration_data(sensor, reference_values)
    result = calibrate_linear(reference, measured)

    fig, ax = plt.subplots(figsize=(6, 5))
    ax.scatter(reference, measured, s=14, label="simulated sensor reading")
    fit_x = np.linspace(reference.min(), reference.max(), 50)
    ax.plot(fit_x, result.slope * fit_x + result.intercept, "r--",
            label=f"fit: y = {result.slope:.4f}x + {result.intercept:.4f}")
    ax.plot(fit_x, fit_x, "k:", alpha=0.5, label="ideal (y = x)")
    ax.set_xlabel(f"reference value ({unit_label}), SIMULATED")
    ax.set_ylabel(f"sensor reading ({unit_label}), SIMULATED")
    ax.set_title(f"{display_name}: simulated calibration")
    ax.legend()
    fig.tight_layout()

    df = _pd().DataFrame({"reference": reference, "measured": measured})
    summary = {
        "experiment": name,
        "slope": result.slope,
        "intercept": result.intercept,
        "rmse": result.rmse,
        "max_abs_error": result.max_abs_error,
        "mean_pct_error": result.mean_pct_error,
        "n_points": len(reference_values),
    }
    paths = save_outputs(name, df=df, fig=fig, summary=summary)
    plt.close(fig)
    return {"summary": summary, "paths": paths, "calibration": result, "df": df}


def _pd():
    import pandas as pd
    return pd


def experiment_01_temperature_calibration():
    cfg = AqualoopConfig()
    rng = np.random.default_rng(cfg.simulation.random_seed)
    sensor = TemperatureSensor(cfg.temperature_sensor, rng, initial_true_value_c=25.0)
    reference_values = np.linspace(20.0, 70.0, 21)
    return _run_calibration_experiment("experiment_01_temperature_calibration", sensor,
                                        reference_values, "degC", "Temperature sensor")


def experiment_02_level_calibration():
    cfg = AqualoopConfig()
    rng = np.random.default_rng(cfg.simulation.random_seed)
    sensor = LevelSensor(cfg.level_sensor, rng, initial_true_value_m=0.15)
    reference_values = np.linspace(0.02, 0.28, 21)
    return _run_calibration_experiment("experiment_02_level_calibration", sensor,
                                        reference_values, "m", "Level sensor")


def experiment_03_flow_calibration():
    cfg = AqualoopConfig()
    rng = np.random.default_rng(cfg.simulation.random_seed)
    sensor = FlowSensor(cfg.flow_sensor, rng)
    reference_values = np.linspace(0.0, 6.0e-6, 21)
    return _run_calibration_experiment("experiment_03_flow_calibration", sensor,
                                        reference_values, "m3/s", "Flow sensor")


# ---------------------------------------------------------------------------
# 4: open-loop temperature response (also used to identify the FOPDT model)
# ---------------------------------------------------------------------------

def experiment_04_open_loop_temperature_response():
    name = "experiment_04_open_loop_temperature_response"
    cfg = AqualoopConfig()
    dt = cfg.simulation.dt_s
    handles = build_handles(cfg, initial_level_m=0.15, initial_temp_c=25.0)
    handles.temperature_pid.set_manual(20.0)
    handles.level_pi.set_auto()

    baseline_steps = 6000
    step_time = baseline_steps * dt
    step_heater = 60.0

    def on_step(k, t, h):
        if k == baseline_steps:
            h.temperature_pid.set_manual(step_heater)

    df = run_simulation(cfg, temperature_setpoint=45.0, level_setpoint=0.15, handles=handles,
                         duration_s=(baseline_steps + 12000) * dt, on_step=on_step)

    baseline_value = df["true_temperature_c"].iloc[baseline_steps - 1]
    model = identify_foprd(df["time_s"].values, df["true_temperature_c"].values,
                            step_time_s=step_time, step_size=(step_heater - 20.0),
                            baseline_value=baseline_value)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(df["time_s"], df["true_temperature_c"], label="true temperature")
    ax.axvline(step_time, color="gray", linestyle="--", label="heater step: 20% -> 60%")
    ax.set_xlabel("time (s)")
    ax.set_ylabel("temperature (C)")
    ax.set_title("Open-loop temperature step response")
    ax.legend()
    fig.tight_layout()

    summary = {
        "experiment": name,
        "step_size_pct": step_heater - 20.0,
        "identified_gain_c_per_pct": model.gain,
        "identified_tau_s": model.tau_s,
        "identified_theta_s": model.theta_s,
    }
    paths = save_outputs(name, df=df, fig=fig, summary=summary)
    plt.close(fig)
    return {"summary": summary, "paths": paths, "model": model, "df": df}


# ---------------------------------------------------------------------------
# 5: closed-loop temperature control
# ---------------------------------------------------------------------------

def experiment_05_closed_loop_temperature_control():
    name = "experiment_05_closed_loop_temperature_control"
    cfg = AqualoopConfig()
    cfg.simulation.duration_s = 20000.0
    handles = build_handles(cfg, initial_level_m=0.15, initial_temp_c=25.0)
    df = run_simulation(cfg, temperature_setpoint=45.0, level_setpoint=0.15, handles=handles)

    metrics = compute_step_metrics(df["time_s"].values, df["true_temperature_c"].values,
                                    setpoint=45.0, initial_value=25.0)

    fig, axes = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
    axes[0].plot(df["time_s"], df["true_temperature_c"], label="true temperature")
    axes[0].plot(df["time_s"], df["temperature_setpoint_c"], "--", label="setpoint")
    axes[0].set_ylabel("temperature (C)")
    axes[0].legend()
    axes[0].set_title("Closed-loop temperature control, cold start")
    axes[1].plot(df["time_s"], df["heater_command_pct"], label="heater command")
    axes[1].set_ylabel("command (%)")
    axes[1].set_xlabel("time (s)")
    axes[1].legend()
    fig.tight_layout()

    summary = {"experiment": name, **vars(metrics)}
    paths = save_outputs(name, df=df, fig=fig, summary=summary)
    plt.close(fig)
    return {"summary": summary, "paths": paths, "metrics": metrics, "df": df}


# ---------------------------------------------------------------------------
# 6: controller tuning report (temperature and level)
# ---------------------------------------------------------------------------

def experiment_06_controller_tuning_report():
    name = "experiment_06_controller_tuning_report"
    temp_result = experiment_04_open_loop_temperature_response()
    temp_model = temp_result["model"]
    pid_gains = pid_from_foprd(temp_model)

    cfg = AqualoopConfig()
    dt = cfg.simulation.dt_s
    handles = build_handles(cfg, initial_level_m=0.10, initial_temp_c=25.0)
    handles.temperature_pid.set_manual(0.0)
    handles.level_pi.set_manual(20.0)
    baseline_steps = 2000
    step_time = baseline_steps * dt
    step_pump = 40.0

    def on_step(k, t, h):
        if k == baseline_steps:
            h.level_pi.set_manual(step_pump)

    df = run_simulation(cfg, temperature_setpoint=25.0, level_setpoint=0.15, handles=handles,
                         duration_s=(baseline_steps + 6000) * dt, on_step=on_step)
    baseline_value = df["true_level_m"].iloc[baseline_steps - 1]
    level_model = identify_foprd(df["time_s"].values, df["true_level_m"].values,
                                  step_time_s=step_time, step_size=(step_pump - 20.0),
                                  baseline_value=baseline_value)
    pi_gains = pi_from_foprd(level_model)

    summary = {
        "experiment": name,
        "temperature_model": vars(temp_model),
        "temperature_pid_gains_identified": pid_gains,
        "temperature_pid_gains_in_use": {
            "kp": cfg.temperature_pid.kp, "ki": cfg.temperature_pid.ki, "kd": cfg.temperature_pid.kd},
        "level_model": vars(level_model),
        "level_pi_gains_identified": pi_gains,
        "level_pi_gains_in_use": {"kp": cfg.level_pi.kp, "ki": cfg.level_pi.ki},
        "note": ("Gains in use match the identified gains in this project; "
                 "they were not hand-adjusted after identification."),
    }
    paths = save_outputs(name, df=None, fig=None, summary=summary)
    return {"summary": summary, "paths": paths, "df": df}


# ---------------------------------------------------------------------------
# 7: temperature disturbance rejection
# ---------------------------------------------------------------------------

def experiment_07_temperature_disturbance_rejection():
    name = "experiment_07_temperature_disturbance_rejection"
    cfg = AqualoopConfig()
    cfg.simulation.duration_s = 20000.0
    handles = build_handles(cfg, initial_level_m=0.15, initial_temp_c=45.0)
    handles.temperature_pid.reset(measurement=45.0)

    dist_start, dist_duration = 4000.0, 2000.0
    schedule = DisturbanceSchedule([
        Disturbance(kind="inflow_temp_step", start_s=dist_start, duration_s=dist_duration,
                    magnitude=-15.0, label="cold water surge"),
    ])

    df = run_simulation(cfg, temperature_setpoint=45.0, level_setpoint=0.15, handles=handles,
                         on_step=schedule.apply_on_step, disturbance_state_fn=schedule.state_label)

    recovery = disturbance_recovery_time(df["time_s"].values, df["true_temperature_c"].values,
                                          setpoint=45.0, disturbance_end_s=dist_start + dist_duration)
    dip = 45.0 - df[(df["time_s"] >= dist_start) & (df["time_s"] < dist_start + dist_duration + 500)][
        "true_temperature_c"].min()

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(df["time_s"], df["true_temperature_c"], label="true temperature")
    ax.plot(df["time_s"], df["temperature_setpoint_c"], "--", label="setpoint")
    ax.axvspan(dist_start, dist_start + dist_duration, color="orange", alpha=0.2,
               label="reservoir runs 15 C colder")
    ax.set_xlabel("time (s)")
    ax.set_ylabel("temperature (C)")
    ax.set_title("Temperature disturbance rejection: cold-water surge")
    ax.legend()
    fig.tight_layout()

    summary = {
        "experiment": name,
        "disturbance_kind": "inflow_temp_step",
        "disturbance_magnitude_c": -15.0,
        "max_dip_c": float(dip),
        "recovery_time_s": recovery,
    }
    paths = save_outputs(name, df=df, fig=fig, summary=summary)
    plt.close(fig)
    return {"summary": summary, "paths": paths, "df": df}


# ---------------------------------------------------------------------------
# 8: closed-loop level control
# ---------------------------------------------------------------------------

def experiment_08_closed_loop_level_control():
    name = "experiment_08_closed_loop_level_control"
    cfg = AqualoopConfig()
    cfg.simulation.duration_s = 5000.0
    handles = build_handles(cfg, initial_level_m=0.08, initial_temp_c=25.0)
    df = run_simulation(cfg, temperature_setpoint=25.0, level_setpoint=0.20, handles=handles)

    metrics = compute_step_metrics(df["time_s"].values, df["true_level_m"].values,
                                    setpoint=0.20, initial_value=0.08)

    fig, axes = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
    axes[0].plot(df["time_s"], df["true_level_m"], label="true level")
    axes[0].plot(df["time_s"], df["level_setpoint_m"], "--", label="setpoint")
    axes[0].set_ylabel("level (m)")
    axes[0].legend()
    axes[0].set_title("Closed-loop level control, setpoint step 0.08 m -> 0.20 m")
    axes[1].plot(df["time_s"], df["pump_command_pct"], label="pump command")
    axes[1].set_ylabel("command (%)")
    axes[1].set_xlabel("time (s)")
    axes[1].legend()
    fig.tight_layout()

    summary = {"experiment": name, **vars(metrics)}
    paths = save_outputs(name, df=df, fig=fig, summary=summary)
    plt.close(fig)
    return {"summary": summary, "paths": paths, "metrics": metrics, "df": df}


# ---------------------------------------------------------------------------
# 9: level disturbance rejection
# ---------------------------------------------------------------------------

def experiment_09_level_disturbance_rejection():
    name = "experiment_09_level_disturbance_rejection"
    cfg = AqualoopConfig()
    cfg.simulation.duration_s = 9000.0
    handles = build_handles(cfg, initial_level_m=0.15, initial_temp_c=25.0)

    dist_start, dist_duration = 1000.0, 800.0
    schedule = DisturbanceSchedule([
        Disturbance(kind="extra_outflow", start_s=dist_start, duration_s=dist_duration,
                    magnitude=2.5e-6, label="manual water draw-off"),
    ])
    df = run_simulation(cfg, temperature_setpoint=25.0, level_setpoint=0.15, handles=handles,
                         on_step=schedule.apply_on_step, disturbance_state_fn=schedule.state_label)

    recovery = disturbance_recovery_time(df["time_s"].values, df["true_level_m"].values,
                                          setpoint=0.15, disturbance_end_s=dist_start + dist_duration,
                                          band_fraction=0.03)
    dip = 0.15 - df[(df["time_s"] >= dist_start) & (df["time_s"] < dist_start + dist_duration + 500)][
        "true_level_m"].min()

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(df["time_s"], df["true_level_m"], label="true level")
    ax.plot(df["time_s"], df["level_setpoint_m"], "--", label="setpoint")
    ax.axvspan(dist_start, dist_start + dist_duration, color="orange", alpha=0.2, label="extra draw-off active")
    ax.set_xlabel("time (s)")
    ax.set_ylabel("level (m)")
    ax.set_title("Level disturbance rejection: manual water draw-off")
    ax.legend()
    fig.tight_layout()

    summary = {
        "experiment": name,
        "disturbance_kind": "extra_outflow",
        "disturbance_magnitude_m3s": 2.5e-6,
        "max_dip_m": float(dip),
        "recovery_time_s": recovery,
    }
    paths = save_outputs(name, df=df, fig=fig, summary=summary)
    plt.close(fig)
    return {"summary": summary, "paths": paths, "df": df}


# ---------------------------------------------------------------------------
# 10: coupled full-system operation
# ---------------------------------------------------------------------------

def experiment_10_coupled_full_system():
    """Holds temperature at setpoint, then moves the level setpoint up.
    The extra pump flow needed to reach the new level pulls in more
    reservoir-temperature water, which shows up as a genuine dip in
    temperature even though the temperature setpoint never changed. That
    dip, and the PID pulling the temperature back afterward, is the
    coupling this project is built around, not a scripted event."""
    name = "experiment_10_coupled_full_system"
    cfg = AqualoopConfig()
    cfg.simulation.duration_s = 15000.0
    handles = build_handles(cfg, initial_level_m=0.10, initial_temp_c=25.0)
    handles.level_pi.reset()

    level_setpoint_change_s = 7000.0

    def level_setpoint_fn(t):
        return 0.10 if t < level_setpoint_change_s else 0.20

    df = run_simulation(cfg, temperature_setpoint=45.0, level_setpoint=level_setpoint_fn, handles=handles)

    temp_before = df[df["time_s"] < level_setpoint_change_s]["true_temperature_c"].tail(500).mean()
    temp_dip = temp_before - df[(df["time_s"] >= level_setpoint_change_s)
                                 & (df["time_s"] < level_setpoint_change_s + 2000)]["true_temperature_c"].min()

    fig, axes = plt.subplots(3, 1, figsize=(8, 8), sharex=True)
    axes[0].plot(df["time_s"], df["true_temperature_c"], label="true temperature")
    axes[0].plot(df["time_s"], df["temperature_setpoint_c"], "--", label="temperature setpoint")
    axes[0].set_ylabel("temperature (C)")
    axes[0].legend()
    axes[0].set_title("Coupled operation: level setpoint step disturbs temperature")
    axes[1].plot(df["time_s"], df["true_level_m"], label="true level")
    axes[1].plot(df["time_s"], df["level_setpoint_m"], "--", label="level setpoint")
    axes[1].set_ylabel("level (m)")
    axes[1].legend()
    axes[2].plot(df["time_s"], df["heater_command_pct"], label="heater command")
    axes[2].plot(df["time_s"], df["pump_command_pct"], label="pump command")
    axes[2].set_ylabel("command (%)")
    axes[2].set_xlabel("time (s)")
    axes[2].legend()
    fig.tight_layout()

    summary = {
        "experiment": name,
        "level_setpoint_change_s": level_setpoint_change_s,
        "level_setpoint_before_m": 0.10,
        "level_setpoint_after_m": 0.20,
        "temperature_before_c": float(temp_before),
        "temperature_dip_from_level_change_c": float(temp_dip),
    }
    paths = save_outputs(name, df=df, fig=fig, summary=summary)
    plt.close(fig)
    return {"summary": summary, "paths": paths, "df": df}


# ---------------------------------------------------------------------------
# Bonus: P vs PI vs PID controller comparison for the temperature loop
# ---------------------------------------------------------------------------

def experiment_11_p_pi_pid_comparison():
    name = "experiment_11_p_pi_pid_comparison"
    cfg = AqualoopConfig()
    cfg.simulation.duration_s = 20000.0
    base_kp, base_ki, base_kd = cfg.temperature_pid.kp, cfg.temperature_pid.ki, cfg.temperature_pid.kd

    variants = {
        "P": dict(kp=base_kp, ki=0.0, kd=0.0),
        "PI": dict(kp=base_kp, ki=base_ki, kd=0.0),
        "PID": dict(kp=base_kp, ki=base_ki, kd=base_kd),
    }

    fig, ax = plt.subplots(figsize=(8, 5))
    rows = []
    all_dfs = {}
    for label, gains in variants.items():
        run_cfg = AqualoopConfig()
        run_cfg.simulation.duration_s = cfg.simulation.duration_s
        run_cfg.temperature_pid.kp = gains["kp"]
        run_cfg.temperature_pid.ki = gains["ki"]
        run_cfg.temperature_pid.kd = gains["kd"]
        handles = build_handles(run_cfg, initial_level_m=0.15, initial_temp_c=25.0)
        df = run_simulation(run_cfg, temperature_setpoint=45.0, level_setpoint=0.15, handles=handles)
        all_dfs[label] = df
        metrics = compute_step_metrics(df["time_s"].values, df["true_temperature_c"].values,
                                        setpoint=45.0, initial_value=25.0)
        rows.append({"controller": label, **vars(metrics)})
        ax.plot(df["time_s"], df["true_temperature_c"], label=label)

    ax.plot(all_dfs["PID"]["time_s"], all_dfs["PID"]["temperature_setpoint_c"], "k--", label="setpoint")
    ax.set_xlabel("time (s)")
    ax.set_ylabel("temperature (C)")
    ax.set_title("P vs PI vs PID: same plant, same starting conditions")
    ax.legend()
    fig.tight_layout()

    df_summary = _pd().DataFrame(rows)
    summary = {"experiment": name, "comparison": rows}
    paths = save_outputs(name, df=df_summary, fig=fig, summary=summary)
    plt.close(fig)
    return {"summary": summary, "paths": paths, "comparison_table": df_summary, "all_dfs": all_dfs}
