from src.simulation.configuration import AqualoopConfig
from src.simulation.engine import run_simulation, build_handles


def test_closed_loop_temperature_reaches_setpoint_band():
    # The thermal loop's identified time constant is roughly 4200 s, so the
    # closed loop needs several thousand simulated seconds (not real
    # seconds: this is still a fast, non-blocking computation) to settle.
    cfg = AqualoopConfig()
    cfg.simulation.dt_s = 1.0
    cfg.simulation.duration_s = 18000.0
    handles = build_handles(cfg, initial_level_m=0.15, initial_temp_c=25.0)
    df = run_simulation(cfg, temperature_setpoint=45.0, level_setpoint=0.15, handles=handles)

    tail = df.tail(500)
    assert (tail["true_temperature_c"] - 45.0).abs().mean() < 1.0


def test_closed_loop_level_reaches_setpoint_band():
    cfg = AqualoopConfig()
    cfg.simulation.dt_s = 1.0
    cfg.simulation.duration_s = 6000.0
    handles = build_handles(cfg, initial_level_m=0.05, initial_temp_c=25.0)
    df = run_simulation(cfg, temperature_setpoint=25.0, level_setpoint=0.18, handles=handles)

    tail = df.tail(500)
    assert (tail["true_level_m"] - 0.18).abs().mean() < 0.01


def test_simulation_dataframe_has_the_expected_columns():
    cfg = AqualoopConfig()
    cfg.simulation.duration_s = 50.0
    df = run_simulation(cfg, temperature_setpoint=40.0, level_setpoint=0.15)
    expected = {
        "time_s", "true_temperature_c", "measured_temperature_c", "filtered_temperature_c",
        "temperature_setpoint_c", "heater_command_pct", "true_level_m", "measured_level_m",
        "filtered_level_m", "level_setpoint_m", "pump_command_pct", "true_flow_m3s",
        "measured_flow_m3s", "dry_run_interlock", "disturbance_state", "fault_state",
        "controller_mode",
    }
    assert expected.issubset(set(df.columns))


def test_same_seed_gives_reproducible_run():
    cfg = AqualoopConfig()
    cfg.simulation.duration_s = 200.0
    cfg.simulation.random_seed = 7
    df1 = run_simulation(cfg, temperature_setpoint=40.0, level_setpoint=0.15)
    df2 = run_simulation(cfg, temperature_setpoint=40.0, level_setpoint=0.15)
    assert (df1["measured_temperature_c"] == df2["measured_temperature_c"]).all()


def test_ideal_mode_has_no_sensor_noise():
    cfg = AqualoopConfig().ideal()
    cfg.simulation.duration_s = 100.0
    df = run_simulation(cfg, temperature_setpoint=40.0, level_setpoint=0.15)
    assert (df["true_temperature_c"] == df["measured_temperature_c"]).all()
