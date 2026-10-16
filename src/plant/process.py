"""
Coupled plant: ties the level model (tank.py) and thermal model
(thermal.py) together into one object the simulation engine steps
forward in time.

This is also where the low-level heater interlock lives. If the tank
level drops below TankConfig.min_safe_level_m, the heater command is
forced to zero regardless of what the temperature controller is asking
for, the same way a real immersion heater would need a dry-run cutout
to avoid heating an element with no water around it.
"""

from dataclasses import dataclass, replace
from typing import Optional

from src.simulation.configuration import AqualoopConfig
from src.plant.tank import step_level, pump_flow
from src.plant.thermal import step_temperature


@dataclass
class PlantState:
    level_m: float
    temp_c: float
    dry_run_interlock_active: bool = False


class Plant:
    """The physical (simulated) Aqualoop process tank and reservoir.

    Beyond the two state variables, this object exposes a handful of
    mutable attributes that faults and disturbances act on directly:
    pump_effectiveness and heater_effectiveness scale the actuators down
    (a "worn pump" or "degraded heating element" fault), extra_heat_loss_wk
    adds on top of the configured ambient loss coefficient (a "lost
    insulation" process fault), and extra_outflow_m3s adds an additional
    drain flow (a leak, or a disturbance like a manual water draw-off).
    All default to values that make the plant behave exactly as if no
    fault or disturbance were active.
    """

    def __init__(self, config: AqualoopConfig, initial_level_m: float = 0.15,
                 initial_temp_c: Optional[float] = None):
        self.config = config
        temp0 = initial_temp_c if initial_temp_c is not None else config.thermal.ambient_temp_c
        self.state = PlantState(level_m=initial_level_m, temp_c=temp0)

        self.pump_effectiveness = 1.0
        self.heater_effectiveness = 1.0
        self.extra_heat_loss_wk = 0.0
        self.extra_outflow_m3s = 0.0

    def step(self, pump_cmd_pct: float, heater_cmd_pct: float, dt_s: float) -> PlantState:
        """Advance the plant by one timestep and return the new state."""
        tank_cfg = self.config.tank
        pump_cfg = self.config.pump
        thermal_cfg = self.config.thermal

        interlock = self.state.level_m < tank_cfg.min_safe_level_m
        effective_heater_cmd = 0.0 if interlock else heater_cmd_pct * self.heater_effectiveness
        effective_pump_cmd = pump_cmd_pct * self.pump_effectiveness

        qin = pump_flow(effective_pump_cmd, pump_cfg)

        new_level = step_level(self.state.level_m, effective_pump_cmd, dt_s, tank_cfg, pump_cfg,
                                extra_outflow_m3s=self.extra_outflow_m3s)

        if self.extra_heat_loss_wk:
            degraded_thermal_cfg = replace(
                thermal_cfg, heat_loss_coeff_wk=thermal_cfg.heat_loss_coeff_wk + self.extra_heat_loss_wk)
        else:
            degraded_thermal_cfg = thermal_cfg

        new_temp = step_temperature(self.state.temp_c, self.state.level_m, qin,
                                     effective_heater_cmd, dt_s, degraded_thermal_cfg, tank_cfg)

        self.state = PlantState(level_m=new_level, temp_c=new_temp,
                                 dry_run_interlock_active=interlock)
        return self.state
