from src.simulation.configuration import AqualoopConfig
from src.simulation.engine import build_handles, run_simulation, combine_on_step
from src.simulation.disturbances import Disturbance, DisturbanceSchedule
from src.simulation.faults import Fault, FaultSchedule


def test_ambient_temperature_disturbance_changes_the_plant_and_then_reverts():
    cfg = AqualoopConfig()
    cfg.simulation.duration_s = 400.0
    handles = build_handles(cfg, initial_level_m=0.15, initial_temp_c=25.0)
    base_ambient = cfg.thermal.ambient_temp_c

    schedule = DisturbanceSchedule([
        Disturbance(kind="ambient_temp_step", start_s=100.0, duration_s=100.0, magnitude=10.0),
    ])

    df = run_simulation(cfg, temperature_setpoint=25.0, level_setpoint=0.15, handles=handles,
                         on_step=schedule.apply_on_step, disturbance_state_fn=schedule.state_label)

    assert handles.plant.config.thermal.ambient_temp_c == base_ambient  # reverted after the window
    assert (df["disturbance_state"] == "ambient_temp_step").any()
    assert (df["disturbance_state"] == "none").any()


def test_extra_outflow_disturbance_pulls_the_level_down():
    cfg = AqualoopConfig()
    cfg.simulation.duration_s = 500.0
    handles = build_handles(cfg, initial_level_m=0.15, initial_temp_c=25.0)

    schedule = DisturbanceSchedule([
        Disturbance(kind="extra_outflow", start_s=50.0, duration_s=300.0, magnitude=3.0e-6),
    ])
    df = run_simulation(cfg, temperature_setpoint=25.0, level_setpoint=0.15, handles=handles,
                         on_step=schedule.apply_on_step, disturbance_state_fn=schedule.state_label)

    level_during = df[(df["time_s"] >= 60) & (df["time_s"] < 350)]["true_level_m"].min()
    assert level_during < 0.15


def test_sensor_bias_fault_shifts_measured_temperature_only_while_active():
    cfg = AqualoopConfig()
    cfg.simulation.duration_s = 300.0
    handles = build_handles(cfg, initial_level_m=0.15, initial_temp_c=45.0, use_filters=False)

    schedule = FaultSchedule([
        Fault(kind="sensor_bias", target="temperature", start_s=100.0, duration_s=100.0, magnitude=5.0),
    ])
    df = run_simulation(cfg, temperature_setpoint=45.0, level_setpoint=0.15, handles=handles,
                         on_step=schedule.apply_on_step, fault_state_fn=schedule.state_label)

    before = df[df["time_s"] < 100]
    during = df[(df["time_s"] >= 100) & (df["time_s"] < 200)]
    gap_before = (before["measured_temperature_c"] - before["true_temperature_c"]).abs().mean()
    gap_during = (during["measured_temperature_c"] - during["true_temperature_c"]).mean()

    assert gap_before < 0.5
    assert abs(gap_during - 5.0) < 0.5


def test_heater_effectiveness_fault_reduces_heating():
    cfg = AqualoopConfig()
    handles = build_handles(cfg, initial_level_m=0.15, initial_temp_c=25.0)

    schedule = FaultSchedule([
        Fault(kind="heater_effectiveness", start_s=0.0, duration_s=1000.0, magnitude=0.0),
    ])
    df = run_simulation(cfg, temperature_setpoint=80.0, level_setpoint=0.15, handles=handles,
                         duration_s=1000.0, on_step=schedule.apply_on_step,
                         fault_state_fn=schedule.state_label)

    # with the heater fully disabled the temperature should not rise
    assert df["true_temperature_c"].max() <= 25.5


def test_combine_on_step_runs_both_schedules():
    cfg = AqualoopConfig()
    cfg.simulation.duration_s = 300.0
    handles = build_handles(cfg, initial_level_m=0.15, initial_temp_c=25.0)

    dist = DisturbanceSchedule([Disturbance(kind="ambient_temp_step", start_s=50, duration_s=50, magnitude=5.0)])
    fault = FaultSchedule([Fault(kind="sensor_bias", target="level", start_s=150, duration_s=50, magnitude=0.01)])

    combined = combine_on_step(dist.apply_on_step, fault.apply_on_step)
    df = run_simulation(cfg, temperature_setpoint=25.0, level_setpoint=0.15, handles=handles,
                         on_step=combined,
                         disturbance_state_fn=dist.state_label, fault_state_fn=fault.state_label)

    assert (df["disturbance_state"] == "ambient_temp_step").any()
    assert (df["fault_state"] == "sensor_bias").any()


def test_pump_effectiveness_fault_is_reflected_in_the_logged_flow():
    """Regression: the logged true flow used to ignore the pump fault and report
    the flow the pump would have delivered if healthy."""
    from src.plant.tank import pump_flow

    cfg = AqualoopConfig()
    handles = build_handles(cfg, initial_level_m=0.05, initial_temp_c=25.0)
    schedule = FaultSchedule([
        Fault(kind="pump_effectiveness", start_s=0.0, duration_s=100.0, magnitude=0.5),
    ])
    # Level far below setpoint, so the PI controller saturates the pump at 100%.
    df = run_simulation(cfg, temperature_setpoint=25.0, level_setpoint=0.25, handles=handles,
                         duration_s=30.0, on_step=schedule.apply_on_step,
                         fault_state_fn=schedule.state_label)

    assert df["pump_command_pct"].iloc[10] == 100.0
    expected = pump_flow(50.0, cfg.pump)
    assert abs(df["true_flow_m3s"].iloc[10] - expected) < 1e-12
    assert df["true_flow_m3s"].iloc[10] < pump_flow(100.0, cfg.pump)
