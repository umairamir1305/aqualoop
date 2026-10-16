"""
Signal filtering for the virtual instrumentation chain.

An exponential moving average (EMA) is the standard low-pass filter for
a noisy single-channel signal like the level measurement:

    y[n] = alpha * x[n] + (1 - alpha) * y[n-1]

A smaller alpha filters harder (smoother output) at the cost of more lag
behind the true signal. That tradeoff is why alpha is a configuration
parameter here rather than a fixed constant: the dashboard can demonstrate
it directly by sweeping alpha and showing the noise/lag tradeoff on a
live chart.
"""


class EMAFilter:
    def __init__(self, alpha: float, initial_value: float = 0.0):
        if not 0.0 < alpha <= 1.0:
            raise ValueError("alpha must be in (0, 1]")
        self.alpha = alpha
        self._y = initial_value
        self._initialized = False

    def update(self, x: float) -> float:
        if not self._initialized:
            self._y = x
            self._initialized = True
        else:
            self._y = self.alpha * x + (1.0 - self.alpha) * self._y
        return self._y

    def reset(self, value: float = 0.0):
        self._y = value
        self._initialized = False
