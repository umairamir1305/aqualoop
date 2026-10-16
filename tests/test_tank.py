import numpy as np

from src.simulation.configuration import TankConfig, PumpConfig
from src.plant.tank import pump_flow, outlet_flow, step_level


def test_pump_flow_zero_at_zero_command():
    assert pump_flow(0.0, PumpConfig()) == 0.0


def test_pump_flow_zero_inside_dead_zone():
    cfg = PumpConfig(dead_zone_pct=8.0)
    assert pump_flow(5.0, cfg) == 0.0


def test_pump_flow_max_at_full_command():
    cfg = PumpConfig(max_flow_m3s=5e-5)
    assert abs(pump_flow(100.0, cfg) - cfg.max_flow_m3s) < 1e-12


def test_pump_flow_is_monotonic():
    cfg = PumpConfig()
    commands = np.linspace(0, 100, 50)
    flows = [pump_flow(c, cfg) for c in commands]
    assert all(f2 >= f1 for f1, f2 in zip(flows, flows[1:]))


def test_pump_flow_not_proportional_to_command():
    cfg = PumpConfig(dead_zone_pct=8.0, nonlinearity_gamma=1.25, max_flow_m3s=1.0)
    flow_at_50 = pump_flow(50.0, cfg)
    # 50% command must not simply give 50% of rated flow
    assert abs(flow_at_50 - 0.5) > 1e-6


def test_outlet_flow_zero_at_zero_height():
    assert outlet_flow(0.0, TankConfig()) == 0.0


def test_outlet_flow_increases_with_height():
    cfg = TankConfig()
    assert outlet_flow(0.2, cfg) > outlet_flow(0.1, cfg)


def test_level_never_goes_negative():
    tank_cfg = TankConfig()
    pump_cfg = PumpConfig(max_flow_m3s=0.0)
    h = 0.001
    for _ in range(500):
        h = step_level(h, 0.0, 1.0, tank_cfg, pump_cfg)
    assert h >= 0.0


def test_level_never_exceeds_tank_height():
    tank_cfg = TankConfig(height_m=0.3)
    pump_cfg = PumpConfig(max_flow_m3s=1.0, dead_zone_pct=0.0)
    h = 0.29
    for _ in range(1000):
        h = step_level(h, 100.0, 1.0, tank_cfg, pump_cfg)
    assert h <= tank_cfg.height_m


def test_level_settles_to_a_flow_balance():
    tank_cfg = TankConfig()
    pump_cfg = PumpConfig()
    h = 0.05
    for _ in range(40000):
        h = step_level(h, 40.0, 1.0, tank_cfg, pump_cfg)
    qin = pump_flow(40.0, pump_cfg)
    qout = outlet_flow(h, tank_cfg)
    assert abs(qin - qout) < 1e-7
