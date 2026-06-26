import streamlit as st

from theme import apply_theme

st.set_page_config(
    page_title="WeatherML — Прогноз погоды",
    page_icon="⛅",
    layout="wide",
    initial_sidebar_state="expanded",
)

pages = [
    st.Page("home.py", title="Главная", icon="🏠", default=True),
    st.Page("_pages/overview.py", title="Обзор", icon="📊"),
    st.Page("_pages/predictions.py", title="Прогноз", icon="🔮"),
    st.Page("_pages/analytics.py", title="Аналитика", icon="📈"),
    st.Page("_pages/data.py", title="Данные", icon="🗃️"),
    st.Page("_pages/monitoring.py", title="Мониторинг", icon="🛠️"),
]

# Hide Streamlit's auto-nav — we render our own below the brand block.
nav = st.navigation(pages, position="hidden")
apply_theme()
nav.run()
