import numpy as np

from src.simulation.configuration import (
    TemperatureSensorConfig, LevelSensorConfig, FlowSensorConfig,
)
from src.instrumentation.temperature_sensor import TemperatureSensor
from src.instrumentation.level_sensor import LevelSensor
from src.instrumentation.flow_sensor import FlowSensor
from src.instrumentation.calibration import calibrate_linear
from src.instrumentation.filtering import EMAFilter


def test_temperature_sensor_noise_matches_configured_std():
    rng = np.random.default_rng(0)
    cfg = TemperatureSensorConfig(noise_std=0.2, resolution=0.0, delay_steps=0, bias=0.0)
    sensor = TemperatureSensor(cfg, rng, initial_true_value_c=45.0)
    readings = [sensor.measure(45.0) for _ in range(5000)]
    assert abs(np.mean(readings) - 45.0) < 0.05
    assert abs(np.std(readings) - 0.2) < 0.03


def test_temperature_sensor_bias_shifts_the_reading():
    rng = np.random.default_rng(0)
    cfg = TemperatureSensorConfig(noise_std=0.0, resolution=0.0, delay_steps=0, bias=1.5)
    sensor = TemperatureSensor(cfg, rng, initial_true_value_c=45.0)
    assert abs(sensor.measure(45.0) - 46.5) < 1e-9


def test_temperature_sensor_delay_lags_a_step_change():
    rng = np.random.default_rng(0)
    cfg = TemperatureSensorConfig(noise_std=0.0, resolution=0.0, delay_steps=3, bias=0.0)
    sensor = TemperatureSensor(cfg, rng, initial_true_value_c=25.0)
    readings = [sensor.measure(60.0) for _ in range(5)]
    assert readings[0] == 25.0          # still showing the old value
    assert readings[-1] == 60.0         # caught up after enough steps


def test_temperature_sensor_stuck_fault_freezes_the_reading():
    rng = np.random.default_rng(0)
    cfg = TemperatureSensorConfig(noise_std=0.0, resolution=0.0, delay_steps=0, stuck=True)
    sensor = TemperatureSensor(cfg, rng, initial_true_value_c=30.0)
    sensor.measure(30.0)
    frozen = sensor.measure(30.0)
    later = sensor.measure(80.0)
    assert later == frozen


def test_level_sensor_resolution_quantizes_the_reading():
    rng = np.random.default_rng(0)
    cfg = LevelSensorConfig(noise_std=0.0, resolution=0.001, delay_steps=0, outlier_prob=0.0)
    sensor = LevelSensor(cfg, rng)
    reading = sensor.measure(0.12345)
    assert abs(round(reading / 0.001) * 0.001 - reading) < 1e-12


def test_flow_sensor_reads_zero_below_minimum_detectable_flow():
    rng = np.random.default_rng(0)
    cfg = FlowSensorConfig(min_detectable_flow_m3s=3.0e-6, noise_std=0.0, delay_steps=0)
    sensor = FlowSensor(cfg, rng)
    assert sensor.measure(1.0e-6) == 0.0


def test_flow_sensor_reads_nonzero_above_minimum_detectable_flow():
    rng = np.random.default_rng(0)
    cfg = FlowSensorConfig(min_detectable_flow_m3s=3.0e-6, noise_std=0.0, delay_steps=0)
    sensor = FlowSensor(cfg, rng)
    assert sensor.measure(5.0e-6) > 0.0


def test_calibration_recovers_a_known_linear_relationship():
    reference = np.linspace(0, 100, 25)
    measured = 2.0 * reference + 1.0  # noise-free, known ground truth
    result = calibrate_linear(reference, measured)
    assert abs(result.slope - 2.0) < 1e-9
    assert abs(result.intercept - 1.0) < 1e-9
    assert result.rmse < 1e-9


def test_calibration_correct_inverts_the_fit():
    reference = np.linspace(0, 100, 25)
    measured = 2.0 * reference + 1.0
    result = calibrate_linear(reference, measured)
    assert abs(result.correct(measured[10]) - reference[10]) < 1e-9


def test_ema_filter_reduces_noise_variance():
    rng = np.random.default_rng(1)
    true_value = 45.0
    noisy = true_value + rng.normal(0.0, 0.3, size=2000)
    f = EMAFilter(alpha=0.1, initial_value=true_value)
    filtered = [f.update(x) for x in noisy]
    assert np.std(filtered[200:]) < np.std(noisy[200:])


def test_ema_filter_lags_more_as_alpha_decreases():
    step_signal = [0.0] * 50 + [10.0] * 200
    f_fast = EMAFilter(alpha=0.5, initial_value=0.0)
    f_slow = EMAFilter(alpha=0.05, initial_value=0.0)
    fast_out = [f_fast.update(x) for x in step_signal]
    slow_out = [f_slow.update(x) for x in step_signal]
    # shortly after the step, the slower filter should still be further from 10
    assert abs(slow_out[55] - 10.0) > abs(fast_out[55] - 10.0)
