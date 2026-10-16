"""
Disturbance framework.

A Disturbance is a start time, a duration, a magnitude and a kind. It
does not just get plotted alongside a curve that would have happened
anyway; DisturbanceSchedule.apply_on_step actually mutates the plant's
configuration and state while the disturbance is active, so the plant
equations genuinely change and the controllers have something real to
react to.

Three kinds are implemented, covering both loops:

    ambient_temp_step   ambient air temperature changes (a draft, a door
                        left open near the tank)
    inflow_temp_step    the reservoir's water temperature changes (a
                        second process drawing from the same reservoir)
    extra_outflow       an additional drain flow on top of the normal
                        gravity outlet (a small leak, or someone drawing
                        water off the tank by hand)

Pass a list of Disturbance objects to run_simulation as on_step and
disturbance_state_fn via DisturbanceSchedule; see
src/experiments/experiments.py for worked examples.
"""

from dataclasses import dataclass


@dataclass
class Disturbance:
    kind: str          # "ambient_temp_step" | "inflow_temp_step" | "extra_outflow"
    start_s: float
    duration_s: float
    magnitude: float   # degC for the two temperature kinds, m3/s for extra_outflow
    label: str = ""

    def is_active(self, t: float) -> bool:
        return self.start_s <= t < (self.start_s + self.duration_s)

    def name(self) -> str:
        return self.label or self.kind


class DisturbanceSchedule:
    def __init__(self, disturbances):
        self.disturbances = list(disturbances)
        self._base_ambient = None
        self._base_reservoir = None

    def _active(self, t: float):
        return [d for d in self.disturbances if d.is_active(t)]

    def apply_on_step(self, step_index: int, t: float, handles) -> None:
        """Use as the on_step callback passed to run_simulation."""
        plant = handles.plant
        thermal_cfg = plant.config.thermal

        if self._base_ambient is None:
            self._base_ambient = thermal_cfg.ambient_temp_c
            self._base_reservoir = thermal_cfg.reservoir_temp_c

        ambient = self._base_ambient
        reservoir = self._base_reservoir
        extra_outflow = 0.0

        for d in self._active(t):
            if d.kind == "ambient_temp_step":
                ambient += d.magnitude
            elif d.kind == "inflow_temp_step":
                reservoir += d.magnitude
            elif d.kind == "extra_outflow":
                extra_outflow += d.magnitude
            else:
                raise ValueError(f"unknown disturbance kind: {d.kind}")

        thermal_cfg.ambient_temp_c = ambient
        thermal_cfg.reservoir_temp_c = reservoir
        plant.extra_outflow_m3s = extra_outflow

    def state_label(self, t: float) -> str:
        """Use as disturbance_state_fn passed to run_simulation."""
        active = self._active(t)
        return ",".join(d.name() for d in active) if active else "none"
