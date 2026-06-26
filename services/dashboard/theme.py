"""Custom CSS and Plotly defaults for the cyan-amber weather UI.

Palette designed by Claude design — cold cyan as primary (sky / water),
warm amber as accent (sun / temperature), coral for our own forecast
marker. All colours are colourblind-friendly and high-contrast on
the near-black background.

Call `apply_theme()` once at the top of every page.
"""
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# === Primary palette ===
PRIMARY = "#6ec5d6"        # cyan-500, основной (небо, вода, данные)
PRIMARY_DARK = "#4ea3b8"   # cyan-700, для градиентов и hover
PRIMARY_LIGHT = "#9fd6e2"  # cyan-300, текстовые акценты

ACCENT = "#e6b35c"         # amber-400, тёплое (солнце, температура)
ACCENT_LIGHT = "#f0c878"   # amber-200, KPI-числа
ACCENT_MUTED = "#cdab73"   # amber-700, подписи на янтарном фоне

CORAL = "#e57a6a"          # rose-400, наш прогноз и алерты
RAIN = "#4f86c6"           # blue-500, осадки
RAIN_LIGHT = "#6ea8e0"     # blue-400, вероятность дождя
STORM = "#8a7fd0"          # violet-400, грозы
SUCCESS = "#5bbf9a"        # emerald-500, статус ок
WARNING = "#e6b35c"        # = ACCENT
ALERT = "#e57a6a"          # = CORAL

# === Surfaces / chrome ===
BG = "#080b12"             # почти чёрный с холодным подтоном
CARD_BG = "rgba(255,255,255,0.025)"
CARD_BG_ACTIVE = "rgba(255,255,255,0.04)"
BORDER = "rgba(148,163,184,0.10)"
BORDER_BRIGHT = "rgba(148,163,184,0.16)"

# === Text ===
TEXT = "#e9eef6"           # high-emphasis
TEXT_MID = "#cbd5e1"       # body
TEXT_LOW = "#7b8798"       # captions, axis labels
MUTED = "#5b6675"           # tertiary
TEXT_LOW_LIGHT = "#94a3b8"

# === Weather class colours (used in pie + bars) ===
WEATHER_COLORS = {
    "Ясно":       ACCENT,
    "Облачно":    "#94a3b8",
    "Дождь":      RAIN,
    "Гроза":      STORM,
    "Снег":       "#e0f2fe",
    "Туман":      "rgba(148,163,184,0.6)",
}

# Compat aliases for any old imports
ACCENT_2 = PRIMARY_DARK
ACCENT_3 = CORAL


_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

html, body, [class*="css"] {{
    font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
    -webkit-font-smoothing: antialiased;
}}

.stApp {{
    background:
        radial-gradient(1100px 620px at 8% -8%, rgba(78,163,184,0.13), transparent 60%),
        radial-gradient(900px 600px at 108% 112%, rgba(230,179,92,0.06), transparent 55%),
        {BG};
    color: {TEXT};
}}

/* — hide Streamlit chrome — */
#MainMenu, footer {{ visibility: hidden; }}
[data-testid="stToolbar"] {{ display: none !important; }}
[data-testid="stDecoration"] {{ display: none !important; }}
[data-testid="stStatusWidget"] {{ display: none !important; }}
[data-testid="stHeader"] {{ background: transparent !important; }}
.stDeployButton {{ display: none !important; }}

/* — headings — */
h1 {{
    background: linear-gradient(105deg, {PRIMARY_LIGHT} 0%, {PRIMARY} 38%, #cfe0e6 62%, {ACCENT} 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-weight: 800 !important;
    letter-spacing: -0.035em !important;
    line-height: 1.02 !important;
}}

h2 {{
    color: {TEXT} !important;
    font-weight: 700 !important;
    letter-spacing: -0.025em !important;
}}

h3 {{
    color: {TEXT} !important;
    font-weight: 600 !important;
    letter-spacing: -0.02em !important;
}}

/* — eyebrow label above heading (page section name) — */
.eyebrow {{
    color: {PRIMARY};
    font-weight: 600;
    font-size: 13px;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    margin-bottom: 6px;
}}

/* — KPI / metric cards — */
[data-testid="stMetric"] {{
    background: {CARD_BG};
    border: 1px solid {BORDER};
    border-radius: 16px;
    padding: 18px 20px;
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    transition: border-color 0.2s, transform 0.2s;
}}

[data-testid="stMetric"]:hover {{
    border-color: rgba(110,197,214,0.4);
    transform: translateY(-2px);
}}

[data-testid="stMetricLabel"] {{
    color: {TEXT_LOW} !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}}

[data-testid="stMetricValue"] {{
    color: {TEXT} !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 32px !important;
    font-weight: 600 !important;
    line-height: 1 !important;
}}

[data-testid="stMetricDelta"] {{
    font-family: 'JetBrains Mono', monospace !important;
}}

/* — sidebar — */
[data-testid="stSidebar"] {{
    background: rgba(11,16,25,0.5);
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    border-right: 1px solid {BORDER};
}}

[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {{
    background: none !important;
    -webkit-text-fill-color: {TEXT} !important;
    color: {TEXT} !important;
}}

/* — buttons — */
.stButton > button, .stForm button[type="submit"] {{
    background: linear-gradient(135deg, {PRIMARY}, {PRIMARY_DARK}) !important;
    color: #06222a !important;
    border: none !important;
    border-radius: 11px !important;
    padding: 11px 20px !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    box-shadow: 0 6px 18px rgba(78,163,184,0.30) !important;
    transition: filter 0.15s !important;
}}

.stButton > button:hover, .stForm button[type="submit"]:hover {{
    filter: brightness(1.08) !important;
    transform: none !important;
}}

/* — inputs — */
.stTextInput input, .stNumberInput input, .stSelectbox > div > div,
[data-baseweb="select"] > div {{
    background: {CARD_BG_ACTIVE} !important;
    border: 1px solid {BORDER_BRIGHT} !important;
    border-radius: 10px !important;
    color: {TEXT} !important;
    font-family: 'JetBrains Mono', monospace !important;
}}

.stTextInput input:focus, .stNumberInput input:focus {{
    border-color: {PRIMARY} !important;
    box-shadow: 0 0 0 1px {PRIMARY} !important;
}}

/* — slider — */
[data-baseweb="slider"] [role="slider"] {{
    background: {PRIMARY} !important;
    border: 3px solid #0c121c !important;
    box-shadow: 0 0 0 1px rgba(110,197,214,0.6), 0 4px 12px rgba(110,197,214,0.35) !important;
}}

/* — dataframe — */
[data-testid="stDataFrame"] {{
    border: 1px solid {BORDER};
    border-radius: 16px;
    overflow: hidden;
    background: rgba(255,255,255,0.018);
}}

/* — captions — */
[data-testid="stCaptionContainer"] {{
    color: {TEXT_LOW} !important;
    font-size: 13.5px;
}}

/* — info / warning / success boxes — */
[data-testid="stAlert"] {{
    border-radius: 12px;
    border: 1px solid {BORDER};
    background: {CARD_BG} !important;
}}

/* — divider — */
hr {{
    border-color: {BORDER} !important;
    margin: 1.5rem 0 !important;
}}

/* — expander — */
.streamlit-expanderHeader, [data-testid="stExpander"] {{
    background: {CARD_BG} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 12px !important;
}}

/* — sidebar nav links (st.navigation links) — */
[data-testid="stSidebarNav"] a {{
    border-radius: 10px !important;
    padding: 10px 12px !important;
    color: {TEXT_LOW_LIGHT} !important;
    font-size: 14px !important;
    transition: background 0.15s, color 0.15s !important;
}}

[data-testid="stSidebarNav"] a:hover {{
    background: rgba(255,255,255,0.04) !important;
    color: {TEXT} !important;
}}

/* === Custom utility classes used by markdown blocks === */
.glass-card {{
    background: {CARD_BG};
    border: 1px solid {BORDER};
    border-radius: 18px;
    padding: 22px 24px;
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
}}

.glass-card-accent {{
    background: rgba(230,179,92,0.07);
    border: 1px solid rgba(230,179,92,0.22);
    border-radius: 16px;
    padding: 18px 20px;
}}

.glass-card-coral {{
    background: rgba(229,122,106,0.08);
    border: 1px solid rgba(229,122,106,0.25);
    border-radius: 16px;
    padding: 18px 20px;
}}

.uppercase-label {{
    font-size: 11px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: {TEXT_LOW};
    font-weight: 600;
}}

.mono {{
    font-family: 'JetBrains Mono', monospace;
}}
</style>
"""


def _plotly_template() -> dict:
    """Custom plotly template matching the dark UI."""
    layout = go.Layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, system-ui, sans-serif", color=TEXT, size=13),
        colorway=[PRIMARY, ACCENT, CORAL, RAIN, STORM, SUCCESS, PRIMARY_LIGHT, ACCENT_LIGHT],
        xaxis=dict(
            gridcolor="rgba(148,163,184,0.09)",
            zerolinecolor="rgba(148,163,184,0.2)",
            linecolor=BORDER_BRIGHT,
            tickfont=dict(family="JetBrains Mono, monospace", color=MUTED, size=11),
            title_font=dict(color=TEXT_LOW, size=12),
        ),
        yaxis=dict(
            gridcolor="rgba(148,163,184,0.09)",
            zerolinecolor="rgba(148,163,184,0.2)",
            linecolor=BORDER_BRIGHT,
            tickfont=dict(family="JetBrains Mono, monospace", color=MUTED, size=11),
            title_font=dict(color=TEXT_LOW, size=12),
        ),
        legend=dict(
            bgcolor="rgba(11,16,25,0.6)",
            bordercolor=BORDER_BRIGHT,
            borderwidth=1,
            font=dict(color=TEXT_MID),
        ),
        hoverlabel=dict(
            bgcolor="#0e131d",
            bordercolor=PRIMARY,
            font=dict(color=TEXT, family="Inter, sans-serif"),
        ),
        margin=dict(t=30, r=20, b=40, l=50),
    )
    return go.layout.Template(layout=layout)


_APPLIED = False


def apply_theme():
    """Inject CSS once per session and register the Plotly template."""
    global _APPLIED
    st.markdown(_CSS, unsafe_allow_html=True)
    if not _APPLIED:
        pio.templates["weatherml"] = _plotly_template()
        pio.templates.default = "plotly_dark+weatherml"
        _APPLIED = True


def eyebrow(text: str):
    """Small uppercase cyan label above a page heading."""
    st.markdown(f'<div class="eyebrow">{text}</div>', unsafe_allow_html=True)
