"""
Simulation engine.

Runs the actual closed feedback loop, one timestep at a time: read the
plant's true state, generate sensor measurements from it, filter those
measurements (EMA), let the controllers compute new actuator
commands from them, log everything, then advance the plant physics using
those commands. Every value in the returned dataset comes out of this
loop; nothing is pre-drawn or faked to look like a control response.

Setpoints can be a constant number or a function of simulated time,
t -> setpoint, which is how step tests and setpoint-change experiments
are built on top of this engine without changing the engine itself.
"""

from dataclasses import dataclass, field
from typing import Callable, Optional, Union

import numpy as np
import pandas as pd

from src.simulation.configuration import AqualoopConfig
from src.plant.process import Plant
from src.plant.tank import pump_flow
from src.instrumentation.temperature_sensor import TemperatureSensor
from src.instrumentation.level_sensor import LevelSensor
from src.instrumentation.flow_sensor import FlowSensor
from src.instrumentation.filtering import EMAFilter
from src.control.pid import PIDController
from src.control.pi import PIController

SetpointLike = Union[float, Callable[[float], float]]


def _as_function(value: SetpointLike) -> Callable[[float], float]:
    if callable(value):
        return value
    return lambda t: float(value)


def combine_on_step(*callbacks):
    """Combine several on_step callbacks (for example a DisturbanceSchedule
    and a FaultSchedule) into one, calling each in the order given."""
    callbacks = [cb for cb in callbacks if cb is not None]

    def _combined(step_index, t, handles):
        for cb in callbacks:
            cb(step_index, t, handles)

    return _combined


@dataclass
class SimulationHandles:
    """The live objects a simulation run is built from, exposed so an
    experiment script can reach in and change things mid-run (inject a
    fault, force manual mode for a step test, and so on)."""
    plant: Plant
    temperature_sensor: TemperatureSensor
    level_sensor: LevelSensor
    flow_sensor: FlowSensor
    temperature_filter: Optional[EMAFilter]
    level_filter: Optional[EMAFilter]
    temperature_pid: PIDController
    level_pi: PIController
    rng: np.random.Generator


def build_handles(config: AqualoopConfig, initial_level_m: float = 0.15,
                   initial_temp_c: Optional[float] = None,
                   use_filters: bool = True) -> SimulationHandles:
    rng = np.random.default_rng(config.simulation.random_seed)
    plant = Plant(config, initial_level_m=initial_level_m, initial_temp_c=initial_temp_c)
    temp0 = plant.state.temp_c

    return SimulationHandles(
        plant=plant,
        temperature_sensor=TemperatureSensor(config.temperature_sensor, rng, initial_true_value_c=temp0),
        level_sensor=LevelSensor(config.level_sensor, rng, initial_true_value_m=initial_level_m),
        flow_sensor=FlowSensor(config.flow_sensor, rng),
        temperature_filter=EMAFilter(alpha=0.3, initial_value=temp0) if use_filters else None,
        level_filter=EMAFilter(alpha=0.15, initial_value=initial_level_m) if use_filters else None,
        temperature_pid=PIDController(config.temperature_pid),
        level_pi=PIController(config.level_pi),
        rng=rng,
    )


def run_simulation(config: AqualoopConfig,
                    temperature_setpoint: SetpointLike,
                    level_setpoint: SetpointLike,
                    handles: Optional[SimulationHandles] = None,
                    duration_s: Optional[float] = None,
                    disturbance_state_fn: Optional[Callable[[float], str]] = None,
                    fault_state_fn: Optional[Callable[[float], str]] = None,
                    on_step: Optional[Callable[[int, float, SimulationHandles], None]] = None
                    ) -> pd.DataFrame:
    """Run the closed-loop simulation and return a tidy DataFrame.

    handles lets a caller (an experiment script, or the dashboard) reuse
    an already-configured plant/sensors/controllers, for example to keep
    running after a manual step test before switching to automatic mode.
    on_step is called at the start of every iteration with (step_index,
    time_s, handles), before that step's control action is computed, so
    an experiment can apply a disturbance or a fault by mutating the
    config objects the handles already hold.
    """
    dt = config.simulation.dt_s
    duration = duration_s if duration_s is not None else config.simulation.duration_s
    n_steps = int(round(duration / dt))

    if handles is None:
        handles = build_handles(config)

    sp_temp_fn = _as_function(temperature_setpoint)
    sp_level_fn = _as_function(level_setpoint)
    dist_fn = disturbance_state_fn or (lambda t: "none")
    fault_fn = fault_state_fn or (lambda t: "none")

    rows = []

    for k in range(n_steps):
        t = k * dt

        if on_step is not None:
            on_step(k, t, handles)

        true_level = handles.plant.state.level_m
        true_temp = handles.plant.state.temp_c

        measured_temp = handles.temperature_sensor.measure(true_temp)
        measured_level = handles.level_sensor.measure(true_level)

        filtered_temp = (handles.temperature_filter.update(measured_temp)
                          if handles.temperature_filter is not None else measured_temp)
        filtered_level = (handles.level_filter.update(measured_level)
                           if handles.level_filter is not None else measured_level)

        sp_temp = sp_temp_fn(t)
        sp_level = sp_level_fn(t)

        pid_terms = handles.temperature_pid.update(sp_temp, filtered_temp, dt)
        pi_terms = handles.level_pi.update(sp_level, filtered_level, dt)

        heater_cmd = pid_terms.output
        pump_cmd = pi_terms.output

        # Same effective command the plant will receive in plant.step below, so a
        # pump_effectiveness fault shows up in the logged and measured flow too.
        true_flow = pump_flow(pump_cmd * handles.plant.pump_effectiveness,
                              handles.plant.config.pump)
        measured_flow = handles.flow_sensor.measure(true_flow)

        controller_mode = "auto" if (handles.temperature_pid.auto_mode and handles.level_pi.auto_mode) else "manual"

        rows.append({
            "time_s": t,
            "true_temperature_c": true_temp,
            "measured_temperature_c": measured_temp,
            "filtered_temperature_c": filtered_temp,
            "temperature_setpoint_c": sp_temp,
            "heater_command_pct": heater_cmd,
            "true_level_m": true_level,
            "measured_level_m": measured_level,
            "filtered_level_m": filtered_level,
            "level_setpoint_m": sp_level,
            "pump_command_pct": pump_cmd,
            "true_flow_m3s": true_flow,
            "measured_flow_m3s": measured_flow,
            "dry_run_interlock": handles.plant.state.dry_run_interlock_active,
            "disturbance_state": dist_fn(t),
            "fault_state": fault_fn(t),
            "controller_mode": controller_mode,
        })

        handles.plant.step(pump_cmd, heater_cmd, dt)

    return pd.DataFrame(rows)
