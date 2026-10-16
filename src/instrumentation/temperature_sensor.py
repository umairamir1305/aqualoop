"""
Virtual temperature sensor (DS18B20-style reference).

Quiet noise, a modest response lag from the sensor's own thermal mass,
and quantization at the 12-bit resolution step of a real DS18B20. See
level_sensor.py and flow_sensor.py: each of the three virtual sensors
uses a different noise/resolution/delay profile on purpose, matching
the fact that a thermistor, an ultrasonic rangefinder and a turbine
flow meter fail in different ways.
"""

from collections import deque

import numpy as np

from src.simulation.configuration import TemperatureSensorConfig


class TemperatureSensor:
    def __init__(self, cfg: TemperatureSensorConfig, rng: np.random.Generator,
                 initial_true_value_c: float = 25.0):
        self.cfg = cfg
        self.rng = rng
        buf_len = max(cfg.delay_steps, 1)
        seed_value = initial_true_value_c * cfg.scale + cfg.bias
        self._delay_buffer: deque = deque([seed_value] * buf_len, maxlen=buf_len)
        self._last_value = seed_value

    def measure(self, true_value_c: float) -> float:
        cfg = self.cfg

        if cfg.stuck:
            return self._last_value

        if cfg.dropout_prob > 0 and self.rng.random() < cfg.dropout_prob:
            return self._last_value

        noisy = true_value_c * cfg.scale + cfg.bias
        if cfg.noise_std > 0:
            noisy += self.rng.normal(0.0, cfg.noise_std)

        self._delay_buffer.append(noisy)
        delayed = self._delay_buffer[0]

        if cfg.resolution > 0:
            delayed = round(delayed / cfg.resolution) * cfg.resolution

        self._last_value = delayed
        return delayed
