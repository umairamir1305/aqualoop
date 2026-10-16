"""
Virtual instrumentation calibration.

Given paired (reference, measured) samples, fits a linear calibration

    measured = slope * reference + intercept

by ordinary least squares, then reports the statistics an instrumentation
report needs: slope, intercept, residuals, RMSE and mean percentage error.

The (reference, measured) pairs used in this project come from the
virtual sensor models, not from a physical calibration bench. Anything
produced by generate_simulated_calibration_data is SIMULATED CALIBRATION
DATA and must never be presented as bench measurements. Replace it with
real reference-instrument readings if the physical hardware is ever
built.
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class CalibrationResult:
    slope: float
    intercept: float
    residuals: np.ndarray
    rmse: float
    max_abs_error: float
    mean_pct_error: float

    def correct(self, measured_value: float) -> float:
        """Invert the fitted line to turn a raw reading into a corrected
        estimate of the true quantity, given measured = slope*true + intercept."""
        if self.slope == 0:
            return measured_value
        return (measured_value - self.intercept) / self.slope


def calibrate_linear(reference: np.ndarray, measured: np.ndarray) -> CalibrationResult:
    reference = np.asarray(reference, dtype=float)
    measured = np.asarray(measured, dtype=float)

    slope, intercept = np.polyfit(reference, measured, deg=1)
    predicted = slope * reference + intercept
    residuals = measured - predicted

    rmse = float(np.sqrt(np.mean(residuals ** 2)))
    max_abs_error = float(np.max(np.abs(residuals)))

    nonzero = reference != 0
    if np.any(nonzero):
        pct_errors = np.abs(residuals[nonzero] / reference[nonzero]) * 100.0
        mean_pct_error = float(np.mean(pct_errors))
    else:
        mean_pct_error = float("nan")

    return CalibrationResult(
        slope=float(slope),
        intercept=float(intercept),
        residuals=residuals,
        rmse=rmse,
        max_abs_error=max_abs_error,
        mean_pct_error=mean_pct_error,
    )


def generate_simulated_calibration_data(sensor, true_values: np.ndarray):
    """Run a virtual sensor across a set of reference values and return the
    (reference, measured) pairs.

    At each reference value the sensor is sampled repeatedly and only the
    last reading is kept, the same way a real calibration bench holds a
    reference value steady and waits for the sensor to settle before
    recording it. Skipping this and reading a delayed sensor once per
    reference point would compare the current reference against a
    measurement that is still lagging a previous point, which reads as
    calibration error but is really just an artifact of moving too fast
    through the reference values.

    SIMULATED CALIBRATION DATA. This comes from the sensor model in this
    project, not a physical bench.
    """
    settle_samples = getattr(sensor.cfg, "delay_steps", 0) + 3
    measured = []
    for v in true_values:
        for _ in range(settle_samples):
            reading = sensor.measure(v)
        measured.append(reading)
    return np.asarray(true_values, dtype=float), np.array(measured)
