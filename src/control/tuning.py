"""
Controller tuning.

Rather than hand-picking PID and PI gains, this module identifies a
first-order-plus-dead-time (FOPDT) approximation of the process from an
open-loop step test, then computes gains from that model with a
Ziegler-Nichols-style reaction-curve rule. This mirrors how a real process
would be tuned: bump the actuator in manual mode, record the response,
fit a simple model, calculate a starting set of gains, then adjust.

An FOPDT model has three numbers:

    K      process gain       (steady-state change in output) / (step size)
    tau    time constant      time for the response to reach 63.2% of its
                               total change
    theta  apparent dead time time before the response visibly starts
                               moving

theta for a system with no real transport delay is not exactly zero once
you account for sensor response lag and filtering, both of which delay
when the controller "sees" a change. The identification below estimates
theta directly from the recorded response rather than assuming it away,
so that effective instrumentation lag is reflected in the tuning.
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class FOPDTModel:
    gain: float
    tau_s: float
    theta_s: float


def identify_foprd(time_s: np.ndarray, response: np.ndarray, step_time_s: float,
                    step_size: float, baseline_value: float,
                    move_threshold_fraction: float = 0.02) -> FOPDTModel:
    """Fit an FOPDT model to a single open-loop step response.

    time_s, response: the recorded step test, covering time both before
    and after the step at step_time_s.
    step_size: the change in actuator command applied at step_time_s.
    baseline_value: the process variable's value before the step.
    """
    time_s = np.asarray(time_s, dtype=float)
    response = np.asarray(response, dtype=float)

    post_mask = time_s >= step_time_s
    post_time = time_s[post_mask] - step_time_s
    post_response = response[post_mask]

    total_change = post_response[-1] - baseline_value
    if abs(total_change) < 1e-9:
        raise ValueError("no measurable response to the step; check the step size")

    gain = total_change / step_size

    move_threshold = baseline_value + move_threshold_fraction * total_change
    moved = (np.sign(total_change) * (post_response - baseline_value)) >= (
        np.sign(total_change) * move_threshold_fraction * total_change)
    theta_idx = np.argmax(moved) if np.any(moved) else 0
    theta_s = post_time[theta_idx]

    target_63 = baseline_value + 0.632 * total_change
    if total_change >= 0:
        reached = post_response >= target_63
    else:
        reached = post_response <= target_63
    tau_idx = np.argmax(reached) if np.any(reached) else len(post_time) - 1
    tau_s = max(post_time[tau_idx] - theta_s, post_time[1] - post_time[0])

    return FOPDTModel(gain=gain, tau_s=tau_s, theta_s=max(theta_s, 1e-6))


def _simc_pi_gains(model: FOPDTModel, lambda_s: float) -> tuple:
    """Skogestad's SIMC rule: Kc = (1/K) * tau / (theta + lambda),
    Ti = min(tau, 4*(theta + lambda)).

    This project uses SIMC instead of the classic Ziegler-Nichols
    reaction-curve formulas because both ZN rules divide by theta
    directly, so as theta gets small (which it does here, since this
    plant has no real transport delay and only a few seconds of
    instrumentation lag) the ZN gains blow up towards unrealistic
    values. SIMC stays well behaved as theta shrinks: it degrades
    gracefully to a gain set purely by tau and the desired closed-loop
    speed lambda, which is exactly the regime this plant sits in.
    """
    kc = (1.0 / model.gain) * (model.tau_s / (model.theta_s + lambda_s))
    ti = min(model.tau_s, 4.0 * (model.theta_s + lambda_s))
    return kc, kc / ti


def pid_from_foprd(model: FOPDTModel, lambda_s: Optional[float] = None,
                    derivative_time_s: float = 5.0,
                    output_min: float = 0.0, output_max: float = 100.0,
                    derivative_filter_tau: float = 2.0) -> dict:
    """SIMC-based PID tuning from an FOPDT model.

    lambda_s sets the desired closed-loop time constant; smaller means a
    faster but less conservative response. Defaults to tau/4, a
    reasonably brisk but not aggressive choice.

    derivative_time_s is supplied directly rather than derived from the
    identified theta. The reaction-curve theta estimated by
    identify_foprd is dominated by how slowly a first-order response
    leaves its baseline, not by a genuine transport delay, since this
    plant does not have one; using it to size Td would give a derivative
    term far larger than the few seconds of real sensor and filter lag
    actually justify. Td = 5 s reflects that real lag instead.
    """
    lam = lambda_s if lambda_s is not None else model.tau_s / 4.0
    kp, ki = _simc_pi_gains(model, lam)
    kd = kp * derivative_time_s
    return dict(kp=kp, ki=ki, kd=kd, output_min=output_min, output_max=output_max,
                derivative_filter_tau=derivative_filter_tau)


def pi_from_foprd(model: FOPDTModel, lambda_s: Optional[float] = None,
                   output_min: float = 0.0, output_max: float = 100.0) -> dict:
    """SIMC-based PI tuning from an FOPDT model. See pid_from_foprd for why
    SIMC is used instead of a Ziegler-Nichols reaction-curve rule."""
    lam = lambda_s if lambda_s is not None else model.tau_s / 4.0
    kp, ki = _simc_pi_gains(model, lam)
    return dict(kp=kp, ki=ki, output_min=output_min, output_max=output_max)
