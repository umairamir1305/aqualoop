"""
Visual theme for the Aqualoop dashboard.

Palette and type choices are deliberate, not Streamlit defaults: a dark
instrument-panel background (real control-room HMI screens are almost
always dark, since operators look at them for a full shift and a bright
white dashboard is fatiguing), a teal for water/level readings, an amber
for heat/temperature readings, and monospace numerals for every live
reading so digits don't jitter as they update. Status color (normal,
warning, fault) is reserved for actual status, never used decoratively.
"""

import streamlit as st

BG = "#10141B"
PANEL = "#171D27"
PANEL_ALT = "#1D2430"
BORDER = "#2A3242"
TEXT = "#E7EBF2"
TEXT_MUTED = "#8B93A6"
TEXT_FAINT = "#5B6376"

LEVEL = "#2FBFA8"      # teal: water / level channel
TEMP = "#E8955A"       # amber: heat / temperature channel
OK = "#2FBFA8"
WARNING = "#F2B705"
FAULT = "#E5484D"
INACTIVE = "#3A4256"

FONT_UI = "'Inter', -apple-system, 'Segoe UI', sans-serif"
FONT_MONO = "'IBM Plex Mono', 'SFMono-Regular', Consolas, monospace"


def apply_page_config(title: str):
    st.set_page_config(page_title=f"Aqualoop | {title}", page_icon=None, layout="wide",
                        initial_sidebar_state="expanded")


def inject_css():
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

    html, body, [class*="css"] {{
        font-family: {FONT_UI};
    }}

    .stApp {{
        background-color: {BG};
        color: {TEXT};
    }}

    section[data-testid="stSidebar"] {{
        background-color: {PANEL};
        border-right: 1px solid {BORDER};
    }}

    #MainMenu, footer, header[data-testid="stHeader"] {{
        visibility: hidden;
        height: 0;
    }}

    .block-container {{
        padding-top: 1.6rem;
        padding-bottom: 2rem;
        max-width: 1180px;
    }}

    h1, h2, h3 {{
        font-family: {FONT_UI};
        font-weight: 600;
        color: {TEXT};
        letter-spacing: -0.01em;
    }}

    h1 {{ font-size: 1.5rem; margin-bottom: 0.1rem; }}
    h2 {{ font-size: 1.15rem; margin-top: 1.6rem; }}
    h3 {{ font-size: 0.95rem; color: {TEXT_MUTED}; text-transform: none; }}

    p, div, span, label {{ color: {TEXT}; }}

    hr {{ border-color: {BORDER}; }}

    /* readout cards */
    .aq-readout {{
        background: {PANEL};
        border: 1px solid {BORDER};
        border-radius: 4px;
        padding: 10px 14px;
    }}
    .aq-readout-label {{
        font-size: 0.72rem;
        color: {TEXT_MUTED};
        margin-bottom: 2px;
    }}
    .aq-readout-value {{
        font-family: {FONT_MONO};
        font-size: 1.55rem;
        font-weight: 500;
        font-variant-numeric: tabular-nums;
        line-height: 1.15;
    }}
    .aq-readout-sub {{
        font-family: {FONT_MONO};
        font-size: 0.78rem;
        color: {TEXT_FAINT};
        margin-top: 2px;
    }}

    /* status pill */
    .aq-pill {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 0.76rem;
        color: {TEXT_MUTED};
        border: 1px solid {BORDER};
        border-radius: 999px;
        padding: 3px 10px 3px 8px;
    }}
    .aq-dot {{
        width: 7px; height: 7px; border-radius: 50%;
        display: inline-block;
    }}

    /* buttons */
    .stButton > button, .stDownloadButton > button {{
        background: {PANEL_ALT};
        color: {TEXT};
        border: 1px solid {BORDER};
        border-radius: 4px;
        font-family: {FONT_UI};
        font-weight: 500;
        padding: 0.4rem 1rem;
    }}
    .stButton > button:hover {{
        border-color: {LEVEL};
        color: {LEVEL};
    }}
    .stButton > button[kind="primary"] {{
        background: {LEVEL};
        border-color: {LEVEL};
        color: {BG};
        font-weight: 600;
    }}
    .stButton > button[kind="primary"]:hover {{
        background: {TEXT};
        border-color: {TEXT};
        color: {BG};
    }}
    /* Recent Streamlit versions wrap the label in inner elements that set their own
       colour, which left the label light-on-light (invisible) on primary-button hover.
       Make every descendant follow the button's colour. */
    .stButton > button *, .stDownloadButton > button * {{
        color: inherit;
    }}

    /* inputs */
    .stSlider [data-baseweb="slider"] {{ padding-top: 0.4rem; }}
    div[data-testid="stMetricValue"] {{
        font-family: {FONT_MONO};
        font-variant-numeric: tabular-nums;
    }}

    /* tabs */
    button[data-baseweb="tab"] {{
        font-family: {FONT_UI};
        color: {TEXT_MUTED};
    }}
    button[data-baseweb="tab"][aria-selected="true"] {{
        color: {LEVEL};
    }}

    .aq-caption {{
        font-size: 0.8rem;
        color: {TEXT_MUTED};
        margin-top: -0.6rem;
    }}

    .aq-note {{
        background: {PANEL};
        border: 1px solid {BORDER};
        border-left: 3px solid {LEVEL};
        border-radius: 3px;
        padding: 10px 14px;
        font-size: 0.85rem;
        color: {TEXT_MUTED};
    }}
    .aq-note.warn {{ border-left-color: {WARNING}; }}
    .aq-note.fault {{ border-left-color: {FAULT}; }}
    </style>
    """, unsafe_allow_html=True)


def status_color(state: str) -> str:
    return {"ok": OK, "warning": WARNING, "fault": FAULT, "inactive": INACTIVE}.get(state, INACTIVE)


def readout(label: str, value: str, sub: str = "", color: str = TEXT) -> str:
    sub_html = f'<div class="aq-readout-sub">{sub}</div>' if sub else ""
    return f"""
    <div class="aq-readout">
        <div class="aq-readout-label">{label}</div>
        <div class="aq-readout-value" style="color:{color}">{value}</div>
        {sub_html}
    </div>
    """


def status_pill(label: str, state: str) -> str:
    return f'<span class="aq-pill"><span class="aq-dot" style="background:{status_color(state)}"></span>{label}</span>'


def style_plotly(fig, height=280, show_legend=True):
    fig.update_layout(
        paper_bgcolor=PANEL,
        plot_bgcolor=PANEL,
        font=dict(family=FONT_MONO, color=TEXT_MUTED, size=11),
        margin=dict(l=50, r=20, t=28, b=36),
        height=height,
        showlegend=show_legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0,
                    font=dict(size=10), bgcolor="rgba(0,0,0,0)"),
        hovermode="x unified",
        hoverlabel=dict(bgcolor=PANEL_ALT, font=dict(family=FONT_MONO, size=11, color=TEXT)),
    )
    fig.update_xaxes(gridcolor=BORDER, zerolinecolor=BORDER, showline=True, linecolor=BORDER)
    fig.update_yaxes(gridcolor=BORDER, zerolinecolor=BORDER, showline=True, linecolor=BORDER)
    return fig
