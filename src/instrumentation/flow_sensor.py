"""
Virtual turbine flow sensor (YF-S201-style reference).

A turbine flow sensor needs a minimum flow rate before the rotor spins
fast enough to register a pulse train, so this sensor reads exactly zero
below cfg.min_detectable_flow_m3s even when the true flow is not quite
zero. That threshold behaviour, not just added noise, is what makes this
sensor distinct from the temperature and level models.
"""

from collections import deque

import numpy as np

from src.simulation.configuration import FlowSensorConfig


class FlowSensor:
    def __init__(self, cfg: FlowSensorConfig, rng: np.random.Generator):
        self.cfg = cfg
        self.rng = rng
        buf_len = max(cfg.delay_steps, 1)
        self._delay_buffer: deque = deque([0.0] * buf_len, maxlen=buf_len)
        self._last_value = 0.0

    def measure(self, true_value_m3s: float) -> float:
        cfg = self.cfg

        if cfg.stuck:
            return self._last_value

        if cfg.dropout_prob > 0 and self.rng.random() < cfg.dropout_prob:
            return self._last_value

        if true_value_m3s < cfg.min_detectable_flow_m3s:
            reading = 0.0
        else:
            reading = true_value_m3s * cfg.scale + cfg.bias
            if cfg.noise_std > 0:
                reading += self.rng.normal(0.0, cfg.noise_std)
            if cfg.resolution > 0:
                reading = round(reading / cfg.resolution) * cfg.resolution

        self._delay_buffer.append(reading)
        delayed = max(self._delay_buffer[0], 0.0)

        self._last_value = delayed
        return delayed
