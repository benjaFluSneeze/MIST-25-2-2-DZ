"""Custom CSS and Plotly defaults for a 2026-ish dark UI.

Call `apply_theme()` once at the top of every page.
"""
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

ACCENT = "#6366f1"
ACCENT_2 = "#8b5cf6"
ACCENT_3 = "#ec4899"
SUCCESS = "#10b981"
WARNING = "#f59e0b"
TEXT = "#f1f5f9"
MUTED = "#94a3b8"
BG = "#0f0f1a"
CARD = "#1a1a2e"
BORDER = "#2d2d4a"


_CSS = f"""
<style>
/* — общий фон и шрифты — */
html, body, [class*="css"] {{
    font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif !important;
}}

.stApp {{
    background: radial-gradient(circle at 20% 0%, rgba(99, 102, 241, 0.08), transparent 50%),
                radial-gradient(circle at 80% 100%, rgba(139, 92, 246, 0.06), transparent 50%),
                {BG};
}}

/* — спрятать дефолтные элементы Streamlit — */
#MainMenu {{ visibility: hidden; }}
footer {{ visibility: hidden; }}
[data-testid="stToolbar"] {{ display: none !important; }}
[data-testid="stDecoration"] {{ display: none !important; }}
[data-testid="stStatusWidget"] {{ display: none !important; }}
[data-testid="stHeader"] {{ background: transparent !important; }}
.viewerBadge_container__1QSob {{ display: none !important; }}
.stDeployButton {{ display: none !important; }}

/* — заголовок страницы (h1) с градиентом — */
h1 {{
    background: linear-gradient(135deg, {ACCENT} 0%, {ACCENT_2} 50%, {ACCENT_3} 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-weight: 800 !important;
    letter-spacing: -0.02em !important;
    margin-bottom: 0.5rem !important;
}}

h2, h3 {{
    color: {TEXT} !important;
    font-weight: 600 !important;
    letter-spacing: -0.01em !important;
}}

/* — KPI-карточки (st.metric) — */
[data-testid="stMetric"] {{
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.08), rgba(139, 92, 246, 0.04));
    border: 1px solid {BORDER};
    border-radius: 16px;
    padding: 18px 22px;
    backdrop-filter: blur(12px);
    transition: transform 0.2s, border-color 0.2s;
}}

[data-testid="stMetric"]:hover {{
    transform: translateY(-2px);
    border-color: {ACCENT};
}}

[data-testid="stMetricLabel"] {{
    color: {MUTED} !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}}

[data-testid="stMetricValue"] {{
    color: {TEXT} !important;
    font-size: 2rem !important;
    font-weight: 700 !important;
}}

/* — sidebar — */
[data-testid="stSidebar"] {{
    background: {CARD};
    border-right: 1px solid {BORDER};
}}

[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {{
    background: none !important;
    -webkit-text-fill-color: {TEXT} !important;
    color: {TEXT} !important;
}}

/* — кнопки — */
.stButton > button, .stForm button[type="submit"] {{
    background: linear-gradient(135deg, {ACCENT}, {ACCENT_2}) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 10px 20px !important;
    font-weight: 600 !important;
    transition: transform 0.15s, box-shadow 0.15s !important;
}}

.stButton > button:hover, .stForm button[type="submit"]:hover {{
    transform: translateY(-1px);
    box-shadow: 0 8px 20px rgba(99, 102, 241, 0.35);
}}

/* — inputs / select — */
.stTextInput input, .stNumberInput input, .stSelectbox > div > div {{
    background: {BG} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 8px !important;
    color: {TEXT} !important;
}}

/* — dataframe — */
[data-testid="stDataFrame"] {{
    border: 1px solid {BORDER};
    border-radius: 12px;
    overflow: hidden;
}}

/* — captions / footnotes — */
[data-testid="stCaptionContainer"] {{
    color: {MUTED} !important;
}}

/* — info / warning / success boxes — */
[data-testid="stAlert"] {{
    border-radius: 12px;
    border: 1px solid {BORDER};
}}

/* — divider — */
hr {{
    border-color: {BORDER} !important;
    margin: 1.5rem 0 !important;
}}

/* — слайдер: цвет — */
[data-baseweb="slider"] [role="slider"] {{
    background: {ACCENT} !important;
}}

/* — expander — */
.streamlit-expanderHeader {{
    background: {CARD} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 10px !important;
}}
</style>
"""


def _plotly_template() -> dict:
    """Custom plotly template matching the dark UI."""
    layout = go.Layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, system-ui, sans-serif", color=TEXT, size=13),
        colorway=[ACCENT, ACCENT_2, ACCENT_3, SUCCESS, WARNING, "#3b82f6", "#06b6d4", "#f97316"],
        xaxis=dict(
            gridcolor="rgba(148, 163, 184, 0.12)",
            zerolinecolor="rgba(148, 163, 184, 0.2)",
            linecolor=BORDER,
        ),
        yaxis=dict(
            gridcolor="rgba(148, 163, 184, 0.12)",
            zerolinecolor="rgba(148, 163, 184, 0.2)",
            linecolor=BORDER,
        ),
        legend=dict(
            bgcolor="rgba(26, 26, 46, 0.6)",
            bordercolor=BORDER,
            borderwidth=1,
            font=dict(color=TEXT),
        ),
        hoverlabel=dict(
            bgcolor=CARD,
            bordercolor=ACCENT,
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
