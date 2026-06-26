"""Single source of truth for the multi-page nav.

Both app.py (which builds st.navigation) and theme.py (which renders
the sidebar nav links) import from here so URL paths, icons and labels
stay in sync — and so st.sidebar.page_link can be handed the actual
st.Page object (which carries url_path) instead of a string filepath
(which makes Streamlit fall back to the russian label as URL slug).
"""
import streamlit as st


def build_pages():
    """Return the ordered list of st.Page objects for st.navigation()."""
    # default=True page is always served from "/" — Streamlit ignores
    # url_path on it. So we use the empty slug for the home link mapping.
    return [
        st.Page("home.py",                title="Главная",       icon="🏠",  default=True),
        st.Page("_pages/overview.py",     title="Обзор города",  icon="📊",  url_path="overview"),
        st.Page("_pages/predictions.py",  title="Прогноз",       icon="🔮",  url_path="predictions"),
        st.Page("_pages/analytics.py",    title="Аналитика",     icon="📈",  url_path="analytics"),
        st.Page("_pages/data.py",         title="Данные",        icon="🗃️", url_path="data"),
        st.Page("_pages/monitoring.py",   title="Мониторинг",    icon="🛠️", url_path="monitoring"),
    ]


# Material icon for each url_path — used by the sidebar nav. Kept here
# next to build_pages so adding a page only touches one file.
NAV_ICONS = {
    "":            ":material/home:",   # default page (Главная) has empty url_path
    "home":        ":material/home:",
    "overview":    ":material/dashboard:",
    "predictions": ":material/auto_awesome:",
    "analytics":   ":material/show_chart:",
    "data":        ":material/database:",
    "monitoring":  ":material/monitoring:",
}
