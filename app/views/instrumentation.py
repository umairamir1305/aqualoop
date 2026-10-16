import numpy as np
import plotly.graph_objects as go
import streamlit as st

from app.theme import style_plotly, TEMP, LEVEL, TEXT_MUTED
from app.sim_state import get_config, get_last_run
from src.instrumentation.temperature_sensor import TemperatureSensor
from src.instrumentation.level_sensor import LevelSensor
from src.instrumentation.flow_sensor import FlowSensor
from src.instrumentation.calibration import calibrate_linear, generate_simulated_calibration_data

cfg = get_config()

st.markdown("# Instrumentation")
st.markdown(
    '<div class="aq-caption">Virtual sensors, their configured imperfections, and simulated '
    'calibration. All data on this page is simulated.</div>',
    unsafe_allow_html=True,
)

st.markdown("## Sensor configuration")
t1, t2, t3 = st.columns(3)
with t1:
    st.markdown("**Temperature**")
    st.write(f"Noise: {cfg.temperature_sensor.noise_std} degC (1 sd)")
    st.write(f"Resolution: {cfg.temperature_sensor.resolution} degC")
    st.write(f"Delay: {cfg.temperature_sensor.delay_steps} steps")
with t2:
    st.markdown("**Level**")
    st.write(f"Noise: {cfg.level_sensor.noise_std*1000:.1f} mm (1 sd)")
    st.write(f"Resolution: {cfg.level_sensor.resolution*1000:.1f} mm")
    st.write(f"Outlier chance: {cfg.level_sensor.outlier_prob*100:.0f}% / step, "
             f"{cfg.level_sensor.outlier_magnitude*1000:.0f} mm")
with t3:
    st.markdown("**Flow**")
    st.write(f"Noise: {cfg.flow_sensor.noise_std:.2e} m3/s (1 sd)")
    st.write(f"Min detectable flow: {cfg.flow_sensor.min_detectable_flow_m3s:.2e} m3/s")
    st.write(f"Delay: {cfg.flow_sensor.delay_steps} steps")

st.markdown("## Last run: raw vs filtered")
df = get_last_run()
if df is None:
    st.markdown(
        '<div class="aq-note">Run a simulation from Process Overview to compare '
        'true, measured and filtered signals.</div>', unsafe_allow_html=True)
else:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["time_s"], y=df["measured_temperature_c"], name="measured",
                              line=dict(color=TEXT_MUTED, width=1)))
    fig.add_trace(go.Scatter(x=df["time_s"], y=df["filtered_temperature_c"], name="filtered",
                              line=dict(color=TEMP, width=2)))
    fig.update_yaxes(title="C")
    style_plotly(fig, height=220)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=df["time_s"], y=df["measured_level_m"], name="measured",
                               line=dict(color=TEXT_MUTED, width=1)))
    fig2.add_trace(go.Scatter(x=df["time_s"], y=df["filtered_level_m"], name="filtered",
                               line=dict(color=LEVEL, width=2)))
    fig2.update_yaxes(title="m")
    fig2.update_xaxes(title="time (s)")
    style_plotly(fig2, height=220)
    st.plotly_chart(fig2, width="stretch", config={"displayModeBar": False})

st.markdown("## Simulated calibration")
st.markdown(
    '<div class="aq-caption">SIMULATED CALIBRATION DATA: generated from the sensor models above, '
    'not a physical bench.</div>', unsafe_allow_html=True)

sensor_choice = st.radio("Sensor", ["Temperature", "Level", "Flow"], horizontal=True)
if st.button("Run calibration"):
    rng = np.random.default_rng(cfg.simulation.random_seed)
    if sensor_choice == "Temperature":
        sensor = TemperatureSensor(cfg.temperature_sensor, rng, initial_true_value_c=25.0)
        ref = np.linspace(20.0, 70.0, 21)
        unit = "degC"
    elif sensor_choice == "Level":
        sensor = LevelSensor(cfg.level_sensor, rng, initial_true_value_m=0.15)
        ref = np.linspace(0.02, 0.28, 21)
        unit = "m"
    else:
        sensor = FlowSensor(cfg.flow_sensor, rng)
        ref = np.linspace(0.0, 6.0e-6, 21)
        unit = "m3/s"

    reference, measured = generate_simulated_calibration_data(sensor, ref)
    result = calibrate_linear(reference, measured)

    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(x=reference, y=measured, mode="markers", name="simulated reading",
                               marker=dict(color=LEVEL, size=7)))
    fit_x = np.linspace(reference.min(), reference.max(), 50)
    fig3.add_trace(go.Scatter(x=fit_x, y=result.slope * fit_x + result.intercept, name="fit",
                               line=dict(color=TEMP, width=1.5, dash="dash")))
    fig3.update_xaxes(title=f"reference ({unit})")
    fig3.update_yaxes(title=f"measured ({unit})")
    style_plotly(fig3, height=320)
    st.plotly_chart(fig3, width="stretch", config={"displayModeBar": False})

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Slope", f"{result.slope:.4f}")
    m2.metric("Intercept", f"{result.intercept:.4g}")
    m3.metric("RMSE", f"{result.rmse:.4g}")
    m4.metric("Mean % error", f"{result.mean_pct_error:.2f}%")
