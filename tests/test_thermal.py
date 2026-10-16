from src.simulation.configuration import ThermalConfig, TankConfig
from src.plant.thermal import step_temperature, heater_power_w


def test_heater_power_scales_with_command():
    cfg = ThermalConfig(heater_power_w=40.0)
    assert heater_power_w(0.0, cfg) == 0.0
    assert abs(heater_power_w(100.0, cfg) - 40.0) < 1e-9
    assert abs(heater_power_w(50.0, cfg) - 20.0) < 1e-9


def test_temperature_rises_toward_analytical_steady_state_with_no_flow():
    thermal_cfg = ThermalConfig(heater_power_w=40.0, heat_loss_coeff_wk=1.2, ambient_temp_c=25.0)
    tank_cfg = TankConfig()
    height = 0.15
    temp = 25.0
    dt = 5.0
    for _ in range(30000):
        temp = step_temperature(temp, height, 0.0, 100.0, dt, thermal_cfg, tank_cfg)
    expected_ss = thermal_cfg.ambient_temp_c + thermal_cfg.heater_power_w / thermal_cfg.heat_loss_coeff_wk
    assert abs(temp - expected_ss) < 0.5


def test_temperature_falls_toward_ambient_with_heater_off():
    thermal_cfg = ThermalConfig(ambient_temp_c=25.0)
    tank_cfg = TankConfig()
    height = 0.15
    temp = 60.0
    for _ in range(6000):
        temp = step_temperature(temp, height, 0.0, 0.0, 5.0, thermal_cfg, tank_cfg)
    assert temp < 60.0
    assert temp > thermal_cfg.ambient_temp_c - 0.01


def test_inflow_of_cooler_reservoir_water_pulls_temperature_down():
    """This is the level-to-temperature coupling: more pump flow brings in
    more reservoir-temperature water, which is a real thermal disturbance."""
    thermal_cfg = ThermalConfig(reservoir_temp_c=20.0, heater_power_w=0.0, heat_loss_coeff_wk=1.2)
    tank_cfg = TankConfig()
    height = 0.15
    temp_with_flow = 40.0
    temp_without_flow = 40.0
    for _ in range(500):
        temp_with_flow = step_temperature(temp_with_flow, height, 3e-5, 0.0, 1.0, thermal_cfg, tank_cfg)
        temp_without_flow = step_temperature(temp_without_flow, height, 0.0, 0.0, 1.0, thermal_cfg, tank_cfg)
    assert temp_with_flow < temp_without_flow


def test_lower_water_level_gives_a_faster_thermal_response():
    """Less water means less thermal mass, so the same heater power should
    produce a bigger temperature change in the same amount of time."""
    thermal_cfg = ThermalConfig(heater_power_w=40.0)
    tank_cfg = TankConfig()
    dt = 1.0

    temp_shallow = 25.0
    temp_deep = 25.0
    for _ in range(300):
        temp_shallow = step_temperature(temp_shallow, 0.05, 0.0, 100.0, dt, thermal_cfg, tank_cfg)
        temp_deep = step_temperature(temp_deep, 0.25, 0.0, 100.0, dt, thermal_cfg, tank_cfg)

    assert (temp_shallow - 25.0) > (temp_deep - 25.0)
