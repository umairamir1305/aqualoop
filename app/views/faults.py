import plotly.graph_objects as go
import streamlit as st

from app.theme import style_plotly, LEVEL, TEMP, TEXT_MUTED, WARNING
from app.sim_state import get_config
from src.simulation.engine import build_handles, run_simulation
from src.simulation.disturbances import Disturbance, DisturbanceSchedule
from src.simulation.faults import Fault, FaultSchedule

cfg = get_config()

st.markdown("# Fault & Disturbance Testing")
st.markdown(
    '<div class="aq-caption">Inject a disturbance or a fault into a live run. Both mutate the plant '
    'or sensor objects while active, the same mechanism the experiment suite uses.</div>',
    unsafe_allow_html=True,
)

kind_group = st.radio("Type", ["Disturbance", "Fault"], horizontal=True)

if kind_group == "Disturbance":
    kind = st.selectbox("Kind", ["ambient_temp_step", "inflow_temp_step", "extra_outflow"])
    magnitude_defaults = {"ambient_temp_step": (-10.0, -50.0, 50.0, "C"),
                          "inflow_temp_step": (-15.0, -50.0, 50.0, "C"),
                          "extra_outflow": (2.5e-6, 0.0, 6.0e-6, "m3/s")}
    default, lo, hi, unit = magnitude_defaults[kind]
    magnitude = st.slider(f"Magnitude ({unit})", float(lo), float(hi), float(default))
    target = None
else:
    kind = st.selectbox("Kind", ["sensor_bias", "sensor_noise", "sensor_dropout", "sensor_stuck",
                                  "pump_effectiveness", "heater_effectiveness", "extra_heat_loss"])
    target = None
    if kind.startswith("sensor_"):
        target = st.selectbox("Target sensor", ["temperature", "level", "flow"])
    magnitude_defaults = {"sensor_bias": (3.0, "degC or m, matches the sensor"),
                          "sensor_noise": (5.0, "multiplier on normal noise_std"),
                          "sensor_dropout": (0.3, "probability per step, 0-1"),
                          "sensor_stuck": (0.0, "not used"),
                          "pump_effectiveness": (0.4, "fraction of commanded output, 0-1"),
                          "heater_effectiveness": (0.4, "fraction of commanded output, 0-1"),
                          "extra_heat_loss": (2.0, "W/K added to the ambient loss")}
    default, help_text = magnitude_defaults[kind]
    magnitude = st.slider("Magnitude", 0.0, max(5.0, default * 2), float(default), help=help_text)

start_min = st.slider("Start (simulated minutes)", 0, 60, 15)
duration_min = st.slider("Duration (simulated minutes)", 1, 60, 15)
total_min = st.slider("Total run length (simulated minutes)", 20, 180, 60)

if st.button("Run with this condition", type="primary"):
    start_s, duration_s = start_min * 60.0, duration_min * 60.0
    handles = build_handles(cfg, initial_level_m=0.15, initial_temp_c=25.0)

    if kind_group == "Disturbance":
        schedule = DisturbanceSchedule([Disturbance(kind=kind, start_s=start_s,
                                                      duration_s=duration_s, magnitude=magnitude)])
        on_step, dist_fn, fault_fn = schedule.apply_on_step, schedule.state_label, None
    else:
        f_kwargs = dict(kind=kind, start_s=start_s, duration_s=duration_s, magnitude=magnitude)
        if target:
            f_kwargs["target"] = target
        schedule = FaultSchedule([Fault(**f_kwargs)])
        on_step, dist_fn, fault_fn = schedule.apply_on_step, None, schedule.state_label

    df = run_simulation(cfg, temperature_setpoint=45.0, level_setpoint=0.15, handles=handles,
                         duration_s=total_min * 60.0, on_step=on_step,
                         disturbance_state_fn=dist_fn, fault_state_fn=fault_fn)
    st.session_state.fault_test_df = df
    st.session_state.fault_test_window = (start_s, start_s + duration_s)

if "fault_test_df" in st.session_state:
    df = st.session_state.fault_test_df
    w0, w1 = st.session_state.fault_test_window

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["time_s"], y=df["true_temperature_c"], name="temperature",
                              line=dict(color=TEMP, width=1.8)))
    fig.add_trace(go.Scatter(x=df["time_s"], y=df["temperature_setpoint_c"], name="setpoint",
                              line=dict(color=TEXT_MUTED, width=1, dash="dash")))
    fig.add_vrect(x0=w0, x1=w1, fillcolor=WARNING, opacity=0.12, line_width=0)
    fig.update_yaxes(title="C")
    style_plotly(fig, height=210)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=df["time_s"], y=df["true_level_m"], name="level",
                               line=dict(color=LEVEL, width=1.8)))
    fig2.add_trace(go.Scatter(x=df["time_s"], y=df["level_setpoint_m"], name="setpoint",
                               line=dict(color=TEXT_MUTED, width=1, dash="dash")))
    fig2.add_vrect(x0=w0, x1=w1, fillcolor=WARNING, opacity=0.12, line_width=0)
    fig2.update_yaxes(title="m")
    fig2.update_xaxes(title="time (s)")
    style_plotly(fig2, height=210)
    st.plotly_chart(fig2, width="stretch", config={"displayModeBar": False})

    st.markdown(
        '<div class="aq-caption">Shaded band: the condition is active. '
        'Sensor/actuator faults are visible in the measured signal and commands even when the true '
        'process barely moves; process disturbances move the true state directly.</div>',
        unsafe_allow_html=True)
else:
    st.markdown('<div class="aq-note">Configure a condition above and click '
                '<b>Run with this condition</b>.</div>', unsafe_allow_html=True)
