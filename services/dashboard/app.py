import streamlit as st

from theme import apply_theme

st.set_page_config(
    page_title="WeatherML — Прогноз погоды",
    page_icon="⛅",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme()

pages = [
    st.Page("home.py", title="Главная", icon="🏠", default=True),
    st.Page("pages/overview.py", title="Обзор", icon="📊"),
    st.Page("pages/predictions.py", title="Прогноз", icon="🔮"),
    st.Page("pages/analytics.py", title="Аналитика", icon="📈"),
    st.Page("pages/data.py", title="Данные", icon="🗃️"),
    st.Page("pages/monitoring.py", title="Мониторинг", icon="🛠️"),
]

st.navigation(pages).run()
