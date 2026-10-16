"""
Discrete PID controller for the temperature loop, implemented directly
rather than pulled from a library, since the point of this project is
understanding the anti-windup and derivative handling, not calling a
function that hides them.

Anti-windup accumulates the integral term every step and then clamps it
to the actuator's output range, rather than conditionally deciding
whether to accumulate. This is simpler to reason about and keeps the
integral from ever holding a value larger than the heater could act on
by itself.

The derivative term acts on the measurement rather than the error
(derivative-on-measurement), so a setpoint step does not produce an
instantaneous spike in the output ("derivative kick"). It also passes
through a first-order low-pass filter before being used, since
differentiating a noisy measurement directly would otherwise let sensor
noise dominate the heater command.
"""

from dataclasses import dataclass
from typing import Optional

from src.simulation.configuration import PIDConfig


@dataclass
class PIDTerms:
    p: float
    i: float
    d: float
    output_unclamped: float
    output: float


class PIDController:
    def __init__(self, cfg: PIDConfig):
        self.cfg = cfg
        self._integral = 0.0
        self._prev_measurement: Optional[float] = None
        self._filtered_derivative = 0.0
        self.auto_mode = True
        self.manual_output = 0.0

    def reset(self, measurement: Optional[float] = None):
        """Clear all controller state. Call this when starting a fresh run
        or switching setpoints in a way that should not carry over history."""
        self._integral = 0.0
        self._prev_measurement = measurement
        self._filtered_derivative = 0.0

    def set_manual(self, output_pct: float):
        """Switch to manual mode and hold a fixed output. Used for the
        open-loop step tests in tuning.py."""
        self.auto_mode = False
        self.manual_output = float(output_pct)

    def set_auto(self, measurement: float):
        """Switch back to automatic control. The integral term is seeded
        from the manual output so the command does not jump at the
        moment of the switch (bumpless transfer)."""
        if not self.auto_mode:
            self._integral = self.manual_output
            self._prev_measurement = measurement
        self.auto_mode = True

    def update(self, setpoint: float, measurement: float, dt_s: float) -> PIDTerms:
        cfg = self.cfg

        if not self.auto_mode:
            output = min(max(self.manual_output, cfg.output_min), cfg.output_max)
            return PIDTerms(p=0.0, i=self.manual_output, d=0.0,
                             output_unclamped=output, output=output)

        error = setpoint - measurement

        if self._prev_measurement is None:
            self._prev_measurement = measurement

        p_term = cfg.kp * error

        raw_derivative = -(measurement - self._prev_measurement) / dt_s
        if cfg.derivative_filter_tau > 0:
            alpha = dt_s / (cfg.derivative_filter_tau + dt_s)
            self._filtered_derivative += alpha * (raw_derivative - self._filtered_derivative)
        else:
            self._filtered_derivative = raw_derivative
        d_term = cfg.kd * self._filtered_derivative

        self._integral = self._integral + cfg.ki * error * dt_s
        self._integral = min(max(self._integral, cfg.output_min), cfg.output_max)
        i_term = self._integral

        unclamped_output = p_term + i_term + d_term
        output = min(max(unclamped_output, cfg.output_min), cfg.output_max)

        self._prev_measurement = measurement

        return PIDTerms(p=p_term, i=i_term, d=d_term,
                         output_unclamped=unclamped_output, output=output)
