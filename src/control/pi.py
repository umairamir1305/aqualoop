"""
Discrete PI controller for the level loop.

No derivative term, for two reasons. First, the ultrasonic level
measurement is the noisiest signal in this project (see level_sensor.py),
and differentiating a noisy signal amplifies that noise directly into the
pump command. Second, the tank level process does not have the kind of
lag that derivative action is meant to compensate for: the gravity drain
already provides natural damping through the sqrt(h) outflow
relationship, so the process is closer to self-regulating than the
thermal loop is. PI is standard practice for level control in industry
for the same reasons.

Anti-windup and manual/auto mode work the same way as the temperature
PID controller in pid.py: accumulate the integral every step, then clamp
it to the actuator's output range.
"""

from dataclasses import dataclass

from src.simulation.configuration import PIConfig


@dataclass
class PITerms:
    p: float
    i: float
    output_unclamped: float
    output: float


class PIController:
    def __init__(self, cfg: PIConfig):
        self.cfg = cfg
        self._integral = 0.0
        self.auto_mode = True
        self.manual_output = 0.0

    def reset(self):
        self._integral = 0.0

    def set_manual(self, output_pct: float):
        self.auto_mode = False
        self.manual_output = float(output_pct)

    def set_auto(self):
        if not self.auto_mode:
            self._integral = self.manual_output
        self.auto_mode = True

    def update(self, setpoint: float, measurement: float, dt_s: float) -> PITerms:
        cfg = self.cfg

        if not self.auto_mode:
            output = min(max(self.manual_output, cfg.output_min), cfg.output_max)
            return PITerms(p=0.0, i=self.manual_output, output_unclamped=output, output=output)

        error = setpoint - measurement
        p_term = cfg.kp * error

        self._integral = self._integral + cfg.ki * error * dt_s
        self._integral = min(max(self._integral, cfg.output_min), cfg.output_max)
        i_term = self._integral

        unclamped_output = p_term + i_term
        output = min(max(unclamped_output, cfg.output_min), cfg.output_max)

        return PITerms(p=p_term, i=i_term, output_unclamped=unclamped_output, output=output)
