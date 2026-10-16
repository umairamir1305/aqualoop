import plotly.graph_objects as go
import streamlit as st

from app.theme import style_plotly, readout, LEVEL, TEMP, TEXT_MUTED
from app.sim_state import get_config, get_last_run

cfg = get_config()

st.markdown("# Control Engineering")
st.markdown(
    '<div class="aq-caption">Controller structure, gains, and the identification behind them. '
    'See the technical report for the full derivation.</div>',
    unsafe_allow_html=True,
)

st.markdown("## Temperature loop: discrete PID")
c1, c2 = st.columns([1, 1.3])
with c1:
    st.markdown(readout("Kp", f"{cfg.temperature_pid.kp:.4f}"), unsafe_allow_html=True)
    st.markdown("<br/>", unsafe_allow_html=True)
    st.markdown(readout("Ki", f"{cfg.temperature_pid.ki:.4f}"), unsafe_allow_html=True)
    st.markdown("<br/>", unsafe_allow_html=True)
    st.markdown(readout("Kd", f"{cfg.temperature_pid.kd:.4f}"), unsafe_allow_html=True)
with c2:
    st.markdown(
        "Anti-windup: integral accumulates every step, then clamps to the "
        f"actuator range [{cfg.temperature_pid.output_min:.0f}, {cfg.temperature_pid.output_max:.0f}]%.\n\n"
        "Derivative acts on the measurement, not the error, avoiding a kick on a "
        f"setpoint step, and passes through a {cfg.temperature_pid.derivative_filter_tau:.1f} s "
        "low-pass filter before use.\n\n"
        "Identified from an open-loop step test (20% to 60% heater command) and "
        "tuned with Skogestad's SIMC rule rather than a classic Ziegler-Nichols "
        "reaction curve, since this plant's dead time is small enough that ZN's "
        "formulas, which divide directly by it, become impractical."
    )

st.markdown("## Level loop: discrete PI")
c3, c4 = st.columns([1, 1.3])
with c3:
    st.markdown(readout("Kp", f"{cfg.level_pi.kp:.4f}"), unsafe_allow_html=True)
    st.markdown("<br/>", unsafe_allow_html=True)
    st.markdown(readout("Ki", f"{cfg.level_pi.ki:.4f}"), unsafe_allow_html=True)
with c4:
    st.markdown(
        "No derivative term. The ultrasonic level measurement is the noisiest "
        "signal in the project, and the gravity drain's sqrt(h) outflow already "
        "damps the process on its own, so there is little for a D term to "
        "usefully compensate and a real risk of amplifying sensor glitches into "
        "the pump command.\n\n"
        f"Output range: [{cfg.level_pi.output_min:.0f}, {cfg.level_pi.output_max:.0f}]%, "
        "same anti-windup approach as the temperature loop."
    )

st.markdown("## Last run: controller terms")
df = get_last_run()
if df is None:
    st.markdown(
        '<div class="aq-note">Run a simulation from Process Overview to see the '
        'P, I and D contributions over time.</div>', unsafe_allow_html=True)
else:
    temp_error = df["temperature_setpoint_c"] - df["true_temperature_c"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["time_s"], y=temp_error, name="temperature error",
                              line=dict(color=TEMP, width=1.6)))
    fig.add_hline(y=0, line_width=1, line_color=TEXT_MUTED)
    fig.update_yaxes(title="C")
    fig.update_xaxes(title="time (s)")
    style_plotly(fig, height=220)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    level_error = df["level_setpoint_m"] - df["true_level_m"]
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=df["time_s"], y=level_error, name="level error",
                               line=dict(color=LEVEL, width=1.6)))
    fig2.add_hline(y=0, line_width=1, line_color=TEXT_MUTED)
    fig2.update_yaxes(title="m")
    fig2.update_xaxes(title="time (s)")
    style_plotly(fig2, height=220)
    st.plotly_chart(fig2, width="stretch", config={"displayModeBar": False})
