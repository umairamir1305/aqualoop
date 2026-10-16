import numpy as np
import plotly.graph_objects as go
import streamlit as st

from app.theme import readout, status_pill, style_plotly, LEVEL, TEMP, TEXT_MUTED, FAULT, BG
from app.schematic import render_schematic
from app.sim_state import get_config, run_and_store, get_last_run, get_last_run_meta, has_run

cfg = get_config()

st.markdown("# Process Overview")
st.markdown(
    '<div class="aq-caption">Coupled level and temperature control, simulated. '
    'Set targets, run, and scrub through the result.</div>',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("#### Setpoints")
    temp_sp = st.slider("Temperature setpoint (C)", 25.0, 70.0, 45.0, 0.5)
    level_sp = st.slider("Level setpoint (m)", 0.05, 0.28, 0.15, 0.01)

    st.markdown("#### Run")
    duration_min = st.slider("Duration (simulated minutes)", 10, 240, 180, 5)
    mode = st.radio("Instrumentation mode", ["realistic", "ideal"], horizontal=True,
                     help="Realistic: sensor noise, bias, delay and the pump's dead zone are active. "
                          "Ideal: all of that is switched off so you can see the textbook response.")
    run_clicked = st.button("Run simulation", type="primary", width='stretch')

if run_clicked:
    with st.spinner("Running simulation..."):
        run_and_store(temp_sp, level_sp, duration_s=duration_min * 60.0,
                       initial_level_m=0.15, initial_temp_c=25.0, mode=mode)

if not has_run():
    st.markdown(
        '<div class="aq-note">No run yet. Set your targets in the sidebar and click '
        '<b>Run simulation</b>.</div>', unsafe_allow_html=True)
    st.stop()

df = get_last_run()
meta = get_last_run_meta()
n = len(df)

st.markdown("<br/>", unsafe_allow_html=True)
scrub = st.slider("Scrub through the run", 0, n - 1, n - 1, key="scrub",
                   format="", label_visibility="collapsed")
row = df.iloc[scrub]
t_s = row["time_s"]

status_cols = st.columns([1, 1, 1, 3])
interlock = bool(row["dry_run_interlock"])
with status_cols[0]:
    st.markdown(status_pill(f"t = {t_s:,.0f} s", "inactive"), unsafe_allow_html=True)
with status_cols[1]:
    st.markdown(status_pill(meta.get("mode", "realistic").upper(), "ok"), unsafe_allow_html=True)
with status_cols[2]:
    st.markdown(status_pill("interlock" if interlock else "no interlock",
                             "fault" if interlock else "ok"), unsafe_allow_html=True)

st.markdown("<br/>", unsafe_allow_html=True)
r1 = st.columns(5)
with r1[0]:
    st.markdown(readout("TEMPERATURE", f"{row['true_temperature_c']:.1f}&deg;C",
                         f"setpoint {row['temperature_setpoint_c']:.1f}", TEMP), unsafe_allow_html=True)
with r1[1]:
    st.markdown(readout("LEVEL", f"{row['true_level_m']:.3f} m",
                         f"setpoint {row['level_setpoint_m']:.2f}", LEVEL), unsafe_allow_html=True)
with r1[2]:
    st.markdown(readout("FLOW", f"{row['true_flow_m3s']*6.0e7:.0f}", "mL / min"), unsafe_allow_html=True)
with r1[3]:
    st.markdown(readout("HEATER", f"{row['heater_command_pct']:.0f}%", "PID output", TEMP), unsafe_allow_html=True)
with r1[4]:
    st.markdown(readout("PUMP", f"{row['pump_command_pct']:.0f}%", "PI output", LEVEL), unsafe_allow_html=True)

st.markdown("<br/>", unsafe_allow_html=True)
left, right = st.columns([1, 1.35])

with left:
    schematic_svg = render_schematic(
        level_m=row["true_level_m"], temp_c=row["true_temperature_c"],
        level_setpoint_m=row["level_setpoint_m"], temp_setpoint_c=row["temperature_setpoint_c"],
        tank_height_m=cfg.tank.height_m, heater_pct=row["heater_command_pct"],
        pump_pct=row["pump_command_pct"], flow_m3s=row["true_flow_m3s"],
        interlock_active=interlock,
    )
    st.iframe(f'<div style="background:{BG};margin:0;padding:0;">{schematic_svg}</div>',
              height=340, width="stretch")

with right:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["time_s"], y=df["true_temperature_c"], name="temperature",
                              line=dict(color=TEMP, width=2)))
    fig.add_trace(go.Scatter(x=df["time_s"], y=df["temperature_setpoint_c"], name="setpoint",
                              line=dict(color=TEXT_MUTED, width=1, dash="dash")))
    fig.add_vline(x=t_s, line_width=1, line_color=TEXT_MUTED)
    fig.update_yaxes(title="C")
    style_plotly(fig, height=190)
    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=df["time_s"], y=df["true_level_m"], name="level",
                               line=dict(color=LEVEL, width=2)))
    fig2.add_trace(go.Scatter(x=df["time_s"], y=df["level_setpoint_m"], name="setpoint",
                               line=dict(color=TEXT_MUTED, width=1, dash="dash")))
    fig2.add_vline(x=t_s, line_width=1, line_color=TEXT_MUTED)
    fig2.update_yaxes(title="m")
    style_plotly(fig2, height=190)
    st.plotly_chart(fig2, width='stretch', config={"displayModeBar": False})

st.markdown("##### Actuator commands")
fig3 = go.Figure()
fig3.add_trace(go.Scatter(x=df["time_s"], y=df["heater_command_pct"], name="heater",
                           line=dict(color=TEMP, width=1.6)))
fig3.add_trace(go.Scatter(x=df["time_s"], y=df["pump_command_pct"], name="pump",
                           line=dict(color=LEVEL, width=1.6)))
fig3.add_vline(x=t_s, line_width=1, line_color=TEXT_MUTED)
fig3.update_yaxes(title="%")
fig3.update_xaxes(title="time (s)")
style_plotly(fig3, height=200)
st.plotly_chart(fig3, width='stretch', config={"displayModeBar": False})
