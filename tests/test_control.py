from src.simulation.configuration import PIDConfig, PIConfig
from src.control.pid import PIDController
from src.control.pi import PIController


def test_pid_output_never_exceeds_limits():
    cfg = PIDConfig(kp=50.0, ki=5.0, kd=1.0, output_min=0.0, output_max=100.0)
    pid = PIDController(cfg)
    output = None
    for _ in range(200):
        terms = pid.update(setpoint=200.0, measurement=0.0, dt_s=1.0)
        output = terms.output
        assert cfg.output_min <= output <= cfg.output_max


def test_pid_anti_windup_keeps_integral_within_output_range():
    cfg = PIDConfig(kp=1.0, ki=10.0, kd=0.0, output_min=0.0, output_max=100.0)
    pid = PIDController(cfg)
    for _ in range(500):
        pid.update(setpoint=1000.0, measurement=0.0, dt_s=1.0)
    assert 0.0 <= pid._integral <= 100.0


def test_pid_anti_windup_lets_integral_unwind_immediately_on_overshoot():
    """Once windup has pushed the integral to its ceiling, a small overshoot
    past the setpoint should start pulling the integral back down on the
    very next step, rather than needing extra time first to work off banked
    windup the way an unclamped integral would."""
    cfg = PIDConfig(kp=1.0, ki=10.0, kd=0.0, output_min=0.0, output_max=100.0)
    pid = PIDController(cfg)
    for _ in range(200):
        pid.update(setpoint=1000.0, measurement=0.0, dt_s=1.0)
    assert pid._integral == 100.0  # confirm the integral is saturated

    pid.update(setpoint=1000.0, measurement=1001.0, dt_s=1.0)  # small overshoot
    assert pid._integral < 100.0


def test_pid_manual_mode_holds_fixed_output():
    cfg = PIDConfig()
    pid = PIDController(cfg)
    pid.set_manual(37.0)
    terms = pid.update(setpoint=45.0, measurement=20.0, dt_s=1.0)
    assert terms.output == 37.0


def test_pid_bumpless_transfer_seeds_integral_from_manual_output():
    cfg = PIDConfig(kp=1.0, ki=1.0, kd=0.0)
    pid = PIDController(cfg)
    pid.set_manual(42.0)
    pid.set_auto(measurement=30.0)
    assert pid._integral == 42.0


def test_pid_derivative_kick_is_reduced_by_acting_on_measurement():
    """A pure error-derivative controller spikes hard on a setpoint jump.
    Derivative-on-measurement should not, because the measurement itself
    has not moved yet."""
    cfg = PIDConfig(kp=0.0, ki=0.0, kd=50.0, derivative_filter_tau=0.0)
    pid = PIDController(cfg)
    pid.update(setpoint=25.0, measurement=25.0, dt_s=1.0)
    terms = pid.update(setpoint=80.0, measurement=25.0, dt_s=1.0)
    assert terms.d == 0.0


def test_pi_output_never_exceeds_limits():
    cfg = PIConfig(kp=200.0, ki=20.0, output_min=0.0, output_max=100.0)
    pi = PIController(cfg)
    for _ in range(200):
        terms = pi.update(setpoint=1.0, measurement=0.0, dt_s=1.0)
        assert cfg.output_min <= terms.output <= cfg.output_max


def test_pi_anti_windup_keeps_integral_within_output_range():
    cfg = PIConfig(kp=1.0, ki=50.0, output_min=0.0, output_max=100.0)
    pi = PIController(cfg)
    for _ in range(500):
        pi.update(setpoint=10.0, measurement=0.0, dt_s=1.0)
    assert 0.0 <= pi._integral <= 100.0


def test_pi_manual_mode_holds_fixed_output():
    cfg = PIConfig()
    pi = PIController(cfg)
    pi.set_manual(15.0)
    terms = pi.update(setpoint=0.2, measurement=0.1, dt_s=1.0)
    assert terms.output == 15.0
