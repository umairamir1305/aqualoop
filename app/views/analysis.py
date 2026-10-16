import json
from pathlib import Path

import pandas as pd
import streamlit as st

from app.theme import readout, TEMP, LEVEL
from app.sim_state import get_last_run, get_last_run_meta
from src.analysis.metrics import compute_step_metrics

st.markdown("# Results & Analysis")
st.markdown(
    '<div class="aq-caption">Performance metrics computed from simulation output, not read off a '
    'chart by eye.</div>', unsafe_allow_html=True)

df = get_last_run()
meta = get_last_run_meta()

if df is None:
    st.markdown('<div class="aq-note">Run a simulation from Process Overview first.</div>',
                unsafe_allow_html=True)
else:
    temp_sp = meta.get("temperature_setpoint", df["temperature_setpoint_c"].iloc[0])
    level_sp = meta.get("level_setpoint", df["level_setpoint_m"].iloc[0])

    temp_metrics = compute_step_metrics(df["time_s"].values, df["true_temperature_c"].values,
                                         setpoint=float(temp_sp) if isinstance(temp_sp, (int, float)) else 45.0,
                                         initial_value=df["true_temperature_c"].iloc[0])
    level_metrics = compute_step_metrics(df["time_s"].values, df["true_level_m"].values,
                                          setpoint=float(level_sp) if isinstance(level_sp, (int, float)) else 0.15,
                                          initial_value=df["true_level_m"].iloc[0])

    st.markdown("## Last run: temperature")
    c = st.columns(5)
    rt = temp_metrics.rise_time_s
    c[0].markdown(readout("Rise time", f"{rt:.0f} s" if rt else "n/a", color=TEMP), unsafe_allow_html=True)
    st_ = temp_metrics.settling_time_s
    c[1].markdown(readout("Settling (2%)", f"{st_:.0f} s" if st_ else "n/a", color=TEMP), unsafe_allow_html=True)
    c[2].markdown(readout("Overshoot", f"{temp_metrics.overshoot_pct:.1f}%", color=TEMP), unsafe_allow_html=True)
    c[3].markdown(readout("SSE", f"{temp_metrics.steady_state_error:.3f}", color=TEMP), unsafe_allow_html=True)
    c[4].markdown(readout("IAE", f"{temp_metrics.iae:.0f}", color=TEMP), unsafe_allow_html=True)

    st.markdown("<br/>", unsafe_allow_html=True)
    st.markdown("## Last run: level")
    c2 = st.columns(5)
    rt2 = level_metrics.rise_time_s
    c2[0].markdown(readout("Rise time", f"{rt2:.0f} s" if rt2 else "n/a", color=LEVEL), unsafe_allow_html=True)
    st2_ = level_metrics.settling_time_s
    c2[1].markdown(readout("Settling (2%)", f"{st2_:.0f} s" if st2_ else "n/a", color=LEVEL), unsafe_allow_html=True)
    c2[2].markdown(readout("Overshoot", f"{level_metrics.overshoot_pct:.1f}%", color=LEVEL), unsafe_allow_html=True)
    c2[3].markdown(readout("SSE", f"{level_metrics.steady_state_error:.4f}", color=LEVEL), unsafe_allow_html=True)
    c2[4].markdown(readout("IAE", f"{level_metrics.iae:.2f}", color=LEVEL), unsafe_allow_html=True)

st.markdown("## Saved experiment summaries")
st.markdown(
    '<div class="aq-caption">Read from results/reports/. Run experiments from the Experiments page '
    'to refresh these.</div>', unsafe_allow_html=True)

reports_dir = Path(__file__).resolve().parent.parent.parent / "results" / "reports"
entries = []
if reports_dir.exists():
    for f in sorted(reports_dir.glob("*.json")):
        try:
            data = json.loads(f.read_text())
        except Exception:
            continue
        entries.append((data.get("experiment", f.stem), data))

if entries:
    for name, data in entries:
        with st.expander(name):
            flat = {k: v for k, v in data.items()
                    if k not in ("experiment", "data_label") and not isinstance(v, (dict, list))}
            if flat:
                row = pd.DataFrame([flat])
                st.dataframe(row, width="stretch", hide_index=True)
            nested = {k: v for k, v in data.items() if isinstance(v, (dict, list))}
            for k, v in nested.items():
                st.caption(k)
                st.json(v)
else:
    st.markdown('<div class="aq-note">No saved experiment summaries yet. Run some from the '
                'Experiments page.</div>', unsafe_allow_html=True)
