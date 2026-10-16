"""
Runnable demonstration: brings the process to a temperature setpoint of
45 C and a level setpoint of 0.15 m from a cold start, using the tuned
default gains in src/simulation/configuration.py.

Run from the project root:

    python3 scripts/run_demo.py

Produces results/figures/demo_closed_loop.png and prints the rise time,
overshoot, settling time and steady-state error computed from the
simulation output.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import matplotlib.pyplot as plt

from src.simulation.configuration import AqualoopConfig
from src.simulation.engine import run_simulation, build_handles


def main():
    cfg = AqualoopConfig()
    cfg.simulation.duration_s = 20000.0

    handles = build_handles(cfg, initial_level_m=0.15, initial_temp_c=25.0)
    df = run_simulation(cfg, temperature_setpoint=45.0, level_setpoint=0.15, handles=handles)

    t = df["time_s"].values
    y = df["true_temperature_c"].values
    sp, y0 = 45.0, 25.0

    t10 = t[np.argmax(y >= y0 + 0.1 * (sp - y0))]
    t90 = t[np.argmax(y >= y0 + 0.9 * (sp - y0))]
    rise_time = t90 - t10

    overshoot_pct = max(0.0, (y.max() - sp) / (sp - y0) * 100.0)

    band = 0.02 * sp
    within = np.abs(y - sp) <= band
    settle_idx = next((i for i in range(len(y)) if within[i:].all()), None)
    settling_time = t[settle_idx] if settle_idx is not None else float("nan")

    sse = np.mean(np.abs(y[-500:] - sp))

    print("Closed-loop temperature response, setpoint 45 C, cold start at 25 C")
    print(f"  rise time (10-90%):   {rise_time:.0f} s")
    print(f"  overshoot:            {overshoot_pct:.2f} %")
    print(f"  settling time (2%):   {settling_time:.0f} s")
    print(f"  steady-state error:   {sse:.3f} C")

    fig, axes = plt.subplots(3, 1, figsize=(9, 8), sharex=True)

    axes[0].plot(t, df["true_temperature_c"], label="true temperature")
    axes[0].plot(t, df["temperature_setpoint_c"], "--", label="setpoint")
    axes[0].set_ylabel("Temperature (C)")
    axes[0].legend(loc="lower right")
    axes[0].set_title("Aqualoop virtual plant: closed-loop cold start to 45 C / 0.15 m")

    axes[1].plot(t, df["true_level_m"], label="true level")
    axes[1].plot(t, df["level_setpoint_m"], "--", label="setpoint")
    axes[1].set_ylabel("Level (m)")
    axes[1].legend(loc="lower right")

    axes[2].plot(t, df["heater_command_pct"], label="heater command")
    axes[2].plot(t, df["pump_command_pct"], label="pump command")
    axes[2].set_ylabel("Command (%)")
    axes[2].set_xlabel("Time (s)")
    axes[2].legend(loc="upper right")

    fig.tight_layout()
    out_path = Path(__file__).resolve().parent.parent / "results" / "figures" / "demo_closed_loop.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=140)
    print(f"\nSaved plot to {out_path}")


if __name__ == "__main__":
    main()
