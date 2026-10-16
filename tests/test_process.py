from src.simulation.configuration import AqualoopConfig
from src.plant.process import Plant


def test_heater_interlock_blocks_heating_when_level_is_low():
    cfg = AqualoopConfig()
    cfg.tank.min_safe_level_m = 0.05
    plant = Plant(cfg, initial_level_m=0.01, initial_temp_c=25.0)

    state = plant.step(pump_cmd_pct=0.0, heater_cmd_pct=100.0, dt_s=1.0)

    assert state.dry_run_interlock_active is True
    # with the heater forced off, temperature should not be rising
    assert state.temp_c <= 25.0 + 1e-9


def test_heater_interlock_releases_once_level_recovers():
    cfg = AqualoopConfig()
    cfg.tank.min_safe_level_m = 0.05
    plant = Plant(cfg, initial_level_m=0.20, initial_temp_c=25.0)

    state = plant.step(pump_cmd_pct=50.0, heater_cmd_pct=100.0, dt_s=1.0)

    assert state.dry_run_interlock_active is False
    assert state.temp_c > 25.0


def test_plant_state_updates_each_step():
    cfg = AqualoopConfig()
    plant = Plant(cfg, initial_level_m=0.15, initial_temp_c=25.0)
    s1 = plant.step(pump_cmd_pct=50.0, heater_cmd_pct=50.0, dt_s=1.0)
    s2 = plant.step(pump_cmd_pct=50.0, heater_cmd_pct=50.0, dt_s=1.0)
    assert s2.temp_c != s1.temp_c or s2.level_m != s1.level_m
