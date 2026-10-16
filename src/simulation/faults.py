"""
Fault injection framework.

Complements disturbances.py. A disturbance is something that happens TO
the process (a change in ambient conditions, an extra draw on the tank).
A fault is something WRONG WITH a piece of equipment: a sensor reading
badly, an actuator not delivering what it was told, insulation that has
degraded. Both work the same way: apply_on_step mutates the live sensor
and plant objects while the fault is active, so the rest of the
simulation genuinely experiences a sensor or actuator that is not
working correctly, rather than a plotted-on annotation.

Faults implemented:

    sensor_bias           adds to a named sensor's bias while active
    sensor_noise          multiplies a named sensor's noise_std while active
    sensor_dropout        sets a named sensor's dropout_prob while active
    sensor_stuck          freezes a named sensor at its last reading
    pump_effectiveness    scales the pump's actual output (0-1)
    heater_effectiveness  scales the heater's actual output (0-1)
    extra_heat_loss       adds to the ambient heat loss coefficient,
                          W/K (a "lost insulation" fault)
    extra_outflow         adds an uncommanded drain flow, m3/s (a leak).
                          This uses the same Plant.extra_outflow_m3s
                          attribute disturbances.py uses for its own
                          extra_outflow disturbance; do not schedule a
                          fault and a disturbance of this kind in the
                          same run, or one will overwrite the other.

target selects which sensor a sensor_* fault applies to: "temperature",
"level" or "flow".
"""

from dataclasses import dataclass


@dataclass
class Fault:
    kind: str
    start_s: float
    duration_s: float
    magnitude: float = 0.0
    target: str = ""
    label: str = ""

    def is_active(self, t: float) -> bool:
        return self.start_s <= t < (self.start_s + self.duration_s)

    def name(self) -> str:
        return self.label or self.kind


class FaultSchedule:
    def __init__(self, faults):
        self.faults = list(faults)
        self._baselines_captured = False
        self._base_bias = {}
        self._base_noise = {}

    def _sensor_for(self, handles, target: str):
        return {
            "temperature": handles.temperature_sensor,
            "level": handles.level_sensor,
            "flow": handles.flow_sensor,
        }[target]

    def _capture_baselines(self, handles):
        for target in ("temperature", "level", "flow"):
            sensor = self._sensor_for(handles, target)
            self._base_bias[target] = sensor.cfg.bias
            self._base_noise[target] = sensor.cfg.noise_std
        self._baselines_captured = True

    def _active(self, t: float):
        return [f for f in self.faults if f.is_active(t)]

    def apply_on_step(self, step_index: int, t: float, handles) -> None:
        if not self._baselines_captured:
            self._capture_baselines(handles)

        for target in ("temperature", "level", "flow"):
            sensor = self._sensor_for(handles, target)
            sensor.cfg.bias = self._base_bias[target]
            sensor.cfg.noise_std = self._base_noise[target]
            sensor.cfg.dropout_prob = 0.0
            sensor.cfg.stuck = False

        handles.plant.pump_effectiveness = 1.0
        handles.plant.heater_effectiveness = 1.0
        handles.plant.extra_heat_loss_wk = 0.0
        handles.plant.extra_outflow_m3s = 0.0

        for f in self._active(t):
            if f.kind == "sensor_bias":
                sensor = self._sensor_for(handles, f.target)
                sensor.cfg.bias = self._base_bias[f.target] + f.magnitude
            elif f.kind == "sensor_noise":
                sensor = self._sensor_for(handles, f.target)
                sensor.cfg.noise_std = self._base_noise[f.target] * f.magnitude
            elif f.kind == "sensor_dropout":
                sensor = self._sensor_for(handles, f.target)
                sensor.cfg.dropout_prob = f.magnitude
            elif f.kind == "sensor_stuck":
                sensor = self._sensor_for(handles, f.target)
                sensor.cfg.stuck = True
            elif f.kind == "pump_effectiveness":
                handles.plant.pump_effectiveness = f.magnitude
            elif f.kind == "heater_effectiveness":
                handles.plant.heater_effectiveness = f.magnitude
            elif f.kind == "extra_heat_loss":
                handles.plant.extra_heat_loss_wk = f.magnitude
            elif f.kind == "extra_outflow":
                handles.plant.extra_outflow_m3s = f.magnitude
            else:
                raise ValueError(f"unknown fault kind: {f.kind}")

    def state_label(self, t: float) -> str:
        active = self._active(t)
        return ",".join(f.name() for f in active) if active else "none"
