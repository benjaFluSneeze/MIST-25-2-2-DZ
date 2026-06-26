import streamlit as st

from navigation import build_pages
from theme import apply_theme, set_nav_pages

st.set_page_config(
    page_title="WeatherML — Прогноз погоды",
    page_icon="⛅",
    layout="wide",
    initial_sidebar_state="expanded",
)

pages = build_pages()
set_nav_pages(pages)  # so _sidebar_chrome can page_link them with url_path

# Hide Streamlit's auto-nav — we render our own below the brand block.
nav = st.navigation(pages, position="hidden")
apply_theme(active_path=(nav.url_path or "").lstrip("/"))
nav.run()
