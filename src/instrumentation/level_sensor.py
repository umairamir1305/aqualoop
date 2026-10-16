"""
Virtual ultrasonic level sensor (JSN-SR04T-style reference).

Noisier than the temperature sensor, and with occasional single-sample
outliers, reflecting the kind of echo glitch a time-of-flight ultrasonic
rangefinder produces over a disturbed water surface. This is a different
failure mode from the temperature sensor's quiet Gaussian noise, which is
the point: the two sensing principles do not behave the same way.
"""

from collections import deque

import numpy as np

from src.simulation.configuration import LevelSensorConfig


class LevelSensor:
    def __init__(self, cfg: LevelSensorConfig, rng: np.random.Generator,
                 initial_true_value_m: float = 0.15):
        self.cfg = cfg
        self.rng = rng
        buf_len = max(cfg.delay_steps, 1)
        seed_value = initial_true_value_m * cfg.scale + cfg.bias
        self._delay_buffer: deque = deque([seed_value] * buf_len, maxlen=buf_len)
        self._last_value = seed_value

    def measure(self, true_value_m: float) -> float:
        cfg = self.cfg

        if cfg.stuck:
            return self._last_value

        if cfg.dropout_prob > 0 and self.rng.random() < cfg.dropout_prob:
            return self._last_value

        noisy = true_value_m * cfg.scale + cfg.bias
        if cfg.noise_std > 0:
            noisy += self.rng.normal(0.0, cfg.noise_std)

        if cfg.outlier_prob > 0 and self.rng.random() < cfg.outlier_prob:
            sign = 1.0 if self.rng.random() < 0.5 else -1.0
            noisy += sign * cfg.outlier_magnitude

        self._delay_buffer.append(noisy)
        delayed = self._delay_buffer[0]

        if cfg.resolution > 0:
            delayed = round(delayed / cfg.resolution) * cfg.resolution

        delayed = max(delayed, 0.0)
        self._last_value = delayed
        return delayed
