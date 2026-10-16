"""
Shared session-state helpers for the dashboard.

Streamlit reruns the whole script on every interaction, so anything that
should survive between reruns (the plant configuration, the most recent
run's results) lives in st.session_state. Running a simulation itself is
still a single, fast batch call into src.simulation.engine.run_simulation,
the same function the experiment suite uses; the dashboard does not
reimplement the simulation loop.
"""

import copy

import streamlit as st

from src.simulation.configuration import AqualoopConfig
from src.simulation.engine import build_handles, run_simulation


def get_config() -> AqualoopConfig:
    if "config" not in st.session_state:
        st.session_state.config = AqualoopConfig()
    return st.session_state.config


def reset_config():
    st.session_state.config = AqualoopConfig()


def run_and_store(temperature_setpoint, level_setpoint, duration_s=None,
                   initial_level_m=0.15, initial_temp_c=25.0,
                   on_step=None, disturbance_state_fn=None, fault_state_fn=None,
                   mode="realistic"):
    cfg = get_config()
    run_cfg = cfg.ideal() if mode == "ideal" else copy.deepcopy(cfg)

    handles = build_handles(run_cfg, initial_level_m=initial_level_m, initial_temp_c=initial_temp_c)
    df = run_simulation(run_cfg, temperature_setpoint=temperature_setpoint,
                         level_setpoint=level_setpoint, handles=handles,
                         duration_s=duration_s, on_step=on_step,
                         disturbance_state_fn=disturbance_state_fn,
                         fault_state_fn=fault_state_fn)
    st.session_state.last_run = df
    st.session_state.last_run_meta = {
        "temperature_setpoint": temperature_setpoint,
        "level_setpoint": level_setpoint,
        "mode": mode,
    }
    return df


def get_last_run():
    return st.session_state.get("last_run")


def get_last_run_meta():
    return st.session_state.get("last_run_meta", {})


def has_run() -> bool:
    return "last_run" in st.session_state and st.session_state.last_run is not None
