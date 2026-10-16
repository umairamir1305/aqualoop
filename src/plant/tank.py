"""
Water level dynamics for the Aqualoop process tank.

The tank is modelled as a single well-mixed control volume with a gravity
drain. The mass balance in terms of height is

    A * dh/dt = Qin - Qout

with a physically meaningful outflow relationship for a submerged,
sharp-edged orifice draining under gravity

    Qout = Cd * Ao * sqrt(2 * g * h)

Qin comes from the inlet pump through a nonlinear command-to-flow curve.
A 50% pump command is not assumed to give 50% of the pump's rated flow.
"""

import numpy as np

from src.simulation.configuration import TankConfig, PumpConfig

G = 9.81  # m/s2


def pump_flow(command_pct: float, cfg: PumpConfig) -> float:
    """Map a 0-100% pump command to a volumetric flow rate.

    Below cfg.dead_zone_pct the pump does not move enough water to matter
    (assumption: static friction in a small DC pump). Above the dead zone,
    flow rises with the command raised to cfg.nonlinearity_gamma, so a
    gamma above 1 means the pump has to spin up before flow tracks the
    command closely, rather than flow being directly proportional to
    command.
    """
    command_pct = float(np.clip(command_pct, 0.0, 100.0))
    if command_pct <= cfg.dead_zone_pct:
        return 0.0
    span = 100.0 - cfg.dead_zone_pct
    frac = (command_pct - cfg.dead_zone_pct) / span
    frac = frac ** cfg.nonlinearity_gamma
    return cfg.max_flow_m3s * frac


def outlet_flow(height_m: float, cfg: TankConfig) -> float:
    """Gravity drain flow through the outlet orifice."""
    h = max(height_m, 0.0)
    return cfg.discharge_coeff * cfg.outlet_area_m2 * np.sqrt(2.0 * G * h)


def level_derivative(height_m: float, pump_command_pct: float,
                      tank_cfg: TankConfig, pump_cfg: PumpConfig,
                      extra_outflow_m3s: float = 0.0) -> float:
    """dh/dt for the process tank at the current state.

    extra_outflow_m3s lets a disturbance (see src/simulation/disturbances.py)
    add an additional drain flow on top of the normal gravity outlet,
    representing things like a temporary leak or a manual water draw-off.
    It defaults to zero and does nothing unless a disturbance sets it.
    """
    qin = pump_flow(pump_command_pct, pump_cfg)
    qout = outlet_flow(height_m, tank_cfg) + max(extra_outflow_m3s, 0.0)
    dhdt = (qin - qout) / tank_cfg.area_m2
    # An empty tank cannot lose more water: the drain runs dry, not negative.
    if height_m <= 0.0 and dhdt < 0.0:
        dhdt = 0.0
    return dhdt


def step_level(height_m: float, pump_command_pct: float, dt_s: float,
               tank_cfg: TankConfig, pump_cfg: PumpConfig,
               extra_outflow_m3s: float = 0.0) -> float:
    """Advance the tank level by one explicit Euler step.

    Explicit Euler is used rather than a higher-order integrator because
    the tank's time constant is on the order of tens of seconds to
    minutes, far larger than the simulation timestep (dt_s, typically
    0.5-1 s). That keeps the scheme well inside its stability region
    while staying easy to read and easy to explain: the next height is
    just the current height plus the rate of change times the timestep.
    """
    dhdt = level_derivative(height_m, pump_command_pct, tank_cfg, pump_cfg, extra_outflow_m3s)
    new_h = height_m + dhdt * dt_s
    return float(np.clip(new_h, 0.0, tank_cfg.height_m))
