"""
Performance metrics, computed from actual simulation arrays.

Every function here takes time/response arrays that came out of
run_simulation (or a slice of them) and returns a plain number or a
small dataclass of numbers. Nothing is estimated or assumed; if a metric
cannot be computed from the data given (for example settling time when
the response never actually settles within the recorded window) the
function says so rather than returning a plausible-looking guess.
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np

# np.trapezoid was added in NumPy 2.0; np.trapz is the older name. Prefer the new
# one so NumPy 1.26 (the lower bound in requirements.txt) keeps working.
_trapezoid = getattr(np, "trapezoid", None) or np.trapz


@dataclass
class StepMetrics:
    rise_time_s: Optional[float]
    overshoot_pct: float
    settling_time_s: Optional[float]
    steady_state_error: float
    max_abs_error: float
    iae: float
    ise: float


def compute_step_metrics(t: np.ndarray, y: np.ndarray, setpoint: float,
                          initial_value: Optional[float] = None,
                          band_fraction: float = 0.02,
                          steady_state_window: int = 200) -> StepMetrics:
    t = np.asarray(t, dtype=float)
    y = np.asarray(y, dtype=float)
    y0 = initial_value if initial_value is not None else y[0]
    total_change = setpoint - y0

    error = setpoint - y
    max_abs_error = float(np.max(np.abs(error)))
    iae = float(_trapezoid(np.abs(error), t))
    ise = float(_trapezoid(error ** 2, t))
    steady_state_error = float(np.mean(np.abs(error[-steady_state_window:])))

    rise_time_s = None
    if abs(total_change) > 1e-9:
        target10 = y0 + 0.1 * total_change
        target90 = y0 + 0.9 * total_change
        if total_change > 0:
            hit10 = np.where(y >= target10)[0]
            hit90 = np.where(y >= target90)[0]
        else:
            hit10 = np.where(y <= target10)[0]
            hit90 = np.where(y <= target90)[0]
        if len(hit10) and len(hit90):
            rise_time_s = float(t[hit90[0]] - t[hit10[0]])

    if total_change > 0:
        overshoot_pct = max(0.0, (float(np.max(y)) - setpoint) / total_change * 100.0)
    elif total_change < 0:
        overshoot_pct = max(0.0, (setpoint - float(np.min(y))) / abs(total_change) * 100.0)
    else:
        overshoot_pct = 0.0

    band = band_fraction * abs(setpoint) if setpoint != 0 else band_fraction
    within_band = np.abs(error) <= max(band, 1e-9)
    settling_time_s = None
    for i in range(len(t)):
        if within_band[i:].all():
            settling_time_s = float(t[i])
            break

    return StepMetrics(
        rise_time_s=rise_time_s,
        overshoot_pct=overshoot_pct,
        settling_time_s=settling_time_s,
        steady_state_error=steady_state_error,
        max_abs_error=max_abs_error,
        iae=iae,
        ise=ise,
    )


def disturbance_recovery_time(t: np.ndarray, y: np.ndarray, setpoint: float,
                               disturbance_end_s: float,
                               band_fraction: float = 0.02) -> Optional[float]:
    """Time from the end of a disturbance until the response returns to,
    and stays within, the tolerance band around the setpoint."""
    t = np.asarray(t, dtype=float)
    y = np.asarray(y, dtype=float)
    band = band_fraction * abs(setpoint) if setpoint != 0 else band_fraction
    within_band = np.abs(y - setpoint) <= max(band, 1e-9)

    after = t >= disturbance_end_s
    idx_offset = np.argmax(after)
    for i in range(idx_offset, len(t)):
        if within_band[i:].all():
            return float(t[i] - disturbance_end_s)
    return None


def max_actuator_output(u: np.ndarray) -> float:
    return float(np.max(np.asarray(u, dtype=float)))


def control_effort(t: np.ndarray, u: np.ndarray) -> float:
    """Integral of the actuator command's rate of change, a measure of how
    much the actuator is being asked to move rather than how hard."""
    u = np.asarray(u, dtype=float)
    du = np.diff(u)
    return float(np.sum(np.abs(du)))
