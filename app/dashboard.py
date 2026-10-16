import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from app.theme import apply_page_config, inject_css

apply_page_config("Process Control Laboratory")
inject_css()

pages = [
    st.Page("views/overview.py", title="Process Overview", default=True),
    st.Page("views/control.py", title="Control Engineering"),
    st.Page("views/instrumentation.py", title="Instrumentation"),
    st.Page("views/experiments.py", title="Experiments"),
    st.Page("views/faults.py", title="Fault & Disturbance Testing"),
    st.Page("views/analysis.py", title="Results & Analysis"),
]

with st.sidebar:
    st.markdown("### AQUALOOP")
    st.markdown(
        '<div class="aq-caption">Virtual process control laboratory<br/>'
        'Simulated data. No physical hardware.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("---")

nav = st.navigation(pages, position="sidebar")
nav.run()
