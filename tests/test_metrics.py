import numpy as np

from src.analysis.metrics import (
    compute_step_metrics, disturbance_recovery_time, max_actuator_output, control_effort,
)


def test_rise_time_matches_known_first_order_response():
    tau = 100.0
    sp, y0 = 45.0, 25.0
    t = np.linspace(0, 2000, 20001)
    y = y0 + (sp - y0) * (1 - np.exp(-t / tau))

    metrics = compute_step_metrics(t, y, setpoint=sp, initial_value=y0)
    expected_rise_time = tau * np.log(9)  # analytical 10-90% rise time for a first-order step
    assert abs(metrics.rise_time_s - expected_rise_time) < 2.0
    assert metrics.overshoot_pct < 0.1  # a pure first-order response never overshoots


def test_overshoot_detected_correctly():
    t = np.linspace(0, 100, 1001)
    sp, y0 = 10.0, 0.0
    y = np.piecewise(t, [t < 50, t >= 50],
                      [lambda t: y0 + (sp - y0) * t / 50 * 1.3, lambda t: sp + 3.0 * np.exp(-(t - 50) / 10)])
    metrics = compute_step_metrics(t, y, setpoint=sp, initial_value=y0)
    assert metrics.overshoot_pct > 0.0


def test_zero_error_gives_zero_iae_and_ise():
    t = np.linspace(0, 100, 101)
    y = np.full_like(t, 45.0)
    metrics = compute_step_metrics(t, y, setpoint=45.0, initial_value=45.0)
    assert metrics.iae < 1e-9
    assert metrics.ise < 1e-9
    assert metrics.steady_state_error < 1e-9


def test_settling_time_detects_a_response_that_stays_within_band():
    t = np.linspace(0, 200, 201)
    sp = 100.0
    # overshoots outside the 2% band, then settles for good at t=120
    y = np.where(t < 120, sp * 1.2, sp)
    metrics = compute_step_metrics(t, y, setpoint=sp, initial_value=0.0, band_fraction=0.02)
    assert metrics.settling_time_s is not None
    assert abs(metrics.settling_time_s - 120.0) < 1.0


def test_settling_time_is_none_when_never_settled():
    t = np.linspace(0, 200, 201)
    y = np.full_like(t, 50.0)  # never gets anywhere near setpoint 100
    metrics = compute_step_metrics(t, y, setpoint=100.0, initial_value=0.0, band_fraction=0.02)
    assert metrics.settling_time_s is None


def test_disturbance_recovery_time_detects_return_to_band():
    t = np.linspace(0, 300, 3001)
    sp = 45.0
    y = np.where(t < 150, sp, np.where(t < 200, sp - 5.0, sp))
    recovery = disturbance_recovery_time(t, y, setpoint=sp, disturbance_end_s=150.0, band_fraction=0.02)
    assert recovery is not None
    assert abs(recovery - 50.0) < 1.0


def test_max_actuator_output_and_control_effort():
    u = np.array([0, 20, 80, 100, 40, 0])
    assert max_actuator_output(u) == 100.0
    assert control_effort(np.arange(len(u)), u) == (20 + 60 + 20 + 60 + 40)
