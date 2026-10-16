import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.theme import style_plotly, LEVEL, TEMP, TEXT_MUTED
from src.experiments import experiments as exp

st.markdown("# Experiments")
st.markdown(
    '<div class="aq-caption">The same eleven experiments behind the technical report, run live. '
    'Each also writes a CSV, a plot and a JSON summary under data/ and results/.</div>',
    unsafe_allow_html=True,
)

EXPERIMENTS = {
    "1. Temperature sensor calibration": exp.experiment_01_temperature_calibration,
    "2. Level sensor calibration": exp.experiment_02_level_calibration,
    "3. Flow sensor calibration": exp.experiment_03_flow_calibration,
    "4. Open-loop temperature response": exp.experiment_04_open_loop_temperature_response,
    "5. Closed-loop temperature control": exp.experiment_05_closed_loop_temperature_control,
    "6. Controller tuning report": exp.experiment_06_controller_tuning_report,
    "7. Temperature disturbance rejection": exp.experiment_07_temperature_disturbance_rejection,
    "8. Closed-loop level control": exp.experiment_08_closed_loop_level_control,
    "9. Level disturbance rejection": exp.experiment_09_level_disturbance_rejection,
    "10. Coupled full-system operation": exp.experiment_10_coupled_full_system,
    "11. P vs PI vs PID comparison": exp.experiment_11_p_pi_pid_comparison,
}

choice = st.selectbox("Choose an experiment", list(EXPERIMENTS.keys()))
run_clicked = st.button("Run", type="primary")

UNIT_SUFFIXES = {"_pct": "%", "_m3s": " m3/s", "_c": " C", "_m": " m", "_s": " s"}


def format_label(key: str) -> str:
    for suffix, unit in UNIT_SUFFIXES.items():
        if key.endswith(suffix):
            base = key[: -len(suffix)].replace("_", " ")
            return f"{base} ({unit.strip()})"
    return key.replace("_", " ")

if not run_clicked:
    st.markdown('<div class="aq-note">Pick an experiment and click <b>Run</b>.</div>',
                unsafe_allow_html=True)
    st.stop()

with st.spinner("Running..."):
    result = EXPERIMENTS[choice]()

summary = {k: v for k, v in result["summary"].items()
           if not isinstance(v, (dict, list)) and k not in ("data_label", "experiment")}

st.markdown("### Result")
cols = st.columns(min(4, max(1, len(summary))))
for i, (k, v) in enumerate(summary.items()):
    with cols[i % len(cols)]:
        st.metric(format_label(k), f"{v:.4g}" if isinstance(v, float) else str(v))

df = result.get("df")

if df is not None and "reference" in df.columns:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["reference"], y=df["measured"], mode="markers",
                              name="simulated reading", marker=dict(color=LEVEL, size=7)))
    cal = result["calibration"]
    fit_x = np.linspace(df["reference"].min(), df["reference"].max(), 50)
    fig.add_trace(go.Scatter(x=fit_x, y=cal.slope * fit_x + cal.intercept, name="fit",
                              line=dict(color=TEMP, dash="dash")))
    style_plotly(fig, height=340)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

elif df is not None and "true_temperature_c" in df.columns and "true_level_m" in df.columns:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["time_s"], y=df["true_temperature_c"], name="temperature",
                              line=dict(color=TEMP, width=1.8)))
    if "temperature_setpoint_c" in df.columns:
        fig.add_trace(go.Scatter(x=df["time_s"], y=df["temperature_setpoint_c"], name="setpoint",
                                  line=dict(color=TEXT_MUTED, width=1, dash="dash")))
    fig.update_yaxes(title="C")
    style_plotly(fig, height=210)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=df["time_s"], y=df["true_level_m"], name="level",
                               line=dict(color=LEVEL, width=1.8)))
    if "level_setpoint_m" in df.columns:
        fig2.add_trace(go.Scatter(x=df["time_s"], y=df["level_setpoint_m"], name="setpoint",
                                   line=dict(color=TEXT_MUTED, width=1, dash="dash")))
    fig2.update_yaxes(title="m")
    fig2.update_xaxes(title="time (s)")
    style_plotly(fig2, height=210)
    st.plotly_chart(fig2, width="stretch", config={"displayModeBar": False})

elif "all_dfs" in result:
    fig = go.Figure()
    for label, sub_df in result["all_dfs"].items():
        color = {"P": TEXT_MUTED, "PI": LEVEL, "PID": TEMP}.get(label, TEXT_MUTED)
        fig.add_trace(go.Scatter(x=sub_df["time_s"], y=sub_df["true_temperature_c"],
                                  name=label, line=dict(width=1.8, color=color)))
    fig.update_yaxes(title="C")
    fig.update_xaxes(title="time (s)")
    style_plotly(fig, height=320)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.dataframe(result["comparison_table"], width="stretch", hide_index=True)

elif "temperature_model" in result["summary"]:
    m1, m2 = st.columns(2)
    with m1:
        st.markdown("**Temperature loop**")
        st.json(result["summary"]["temperature_model"])
        st.json(result["summary"]["temperature_pid_gains_in_use"])
    with m2:
        st.markdown("**Level loop**")
        st.json(result["summary"]["level_model"])
        st.json(result["summary"]["level_pi_gains_in_use"])

st.caption("Saved: " + ", ".join(result["paths"].values()))
