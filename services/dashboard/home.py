import os

import streamlit as st

from theme import ACCENT, CORAL, PRIMARY, PRIMARY_LIGHT, RAIN, STORM, SUCCESS

st.markdown(
f"""<div style="min-height: 70vh; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; padding: 40px 20px;">
<div style="display: inline-flex; align-items: center; gap: 8px; padding: 7px 14px; border-radius: 99px; background: rgba(110,197,214,0.08); border: 1px solid rgba(110,197,214,0.22); font-size: 13px; color: {PRIMARY_LIGHT}; margin-bottom: 30px; font-weight: 500;">
<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="{ACCENT}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 3v1M12 20v1M5 12H4M20 12h-1"/></svg>
Семестровый проект · WeatherML
</div>
<h1 style="font-size: clamp(40px, 6.2vw, 82px); margin: 0 0 22px; max-width: 880px;">Прогноз погоды<br>на машинном обучении</h1>
<p style="font-size: clamp(15px, 1.6vw, 19px); line-height: 1.55; color: #94a3b8; max-width: 560px; margin: 0 0 48px;">Сбор данных из нескольких источников, обучение моделей и сравнение нашего прогноза с официальным — всё в одном дашборде.</p>
</div>""",
    unsafe_allow_html=True,
)


def _icon(paths: str, stroke: str) -> str:
    return (
        f'<svg width="21" height="21" viewBox="0 0 24 24" fill="none" '
        f'stroke="{stroke}" stroke-width="1.9" stroke-linecap="round" '
        f'stroke-linejoin="round">{paths}</svg>'
    )


# (href, title, description, icon_paths, fg, bg)
CARDS = [
    ("overview", "Обзор", "Текущая погода, KPI и история выбранного города",
     '<rect x="3" y="3" width="7" height="9" rx="1.5"/>'
     '<rect x="14" y="3" width="7" height="5" rx="1.5"/>'
     '<rect x="14" y="12" width="7" height="9" rx="1.5"/>'
     '<rect x="3" y="16" width="7" height="5" rx="1.5"/>',
     PRIMARY, "rgba(110,197,214,0.12)"),
    ("predictions", "Прогноз", "ML-предсказание, what-if форма, сравнение с Gismeteo",
     '<path d="M9.9 15.5A2 2 0 0 0 8.5 14L4 12.7a.5.5 0 0 1 0-1L8.5 10A2 2 0 0 0 9.9 8.5L11.2 4a.5.5 0 0 1 1 0L13.5 8.5A2 2 0 0 0 14.9 10l4.5 1.3a.5.5 0 0 1 0 1L14.9 14a2 2 0 0 0-1.4 1.4L12.2 20a.5.5 0 0 1-1 0z"/>',
     STORM, "rgba(138,127,208,0.14)"),
    ("analytics", "Аналитика", "Сравнение городов, сезонность, аномалии",
     '<path d="M3 3v16a2 2 0 0 0 2 2h16"/>'
     '<path d="m19 9-5 5-4-4-3 3"/>',
     CORAL, "rgba(229,122,106,0.13)"),
    ("data", "Данные", "Сырые наблюдения с фильтрами и поиском",
     '<ellipse cx="12" cy="5" rx="9" ry="3"/>'
     '<path d="M3 5V19A9 3 0 0 0 21 19V5"/>'
     '<path d="M3 12A9 3 0 0 0 21 12"/>',
     RAIN, "rgba(79,134,198,0.14)"),
    ("monitoring", "Мониторинг", "Статус источников и логи сборщика",
     '<path d="M22 12h-2.5l-2 7-4-18-2 9H2"/>',
     SUCCESS, "rgba(91,191,154,0.14)"),
]

cards_html = "".join(
    f'<a href="/{href}" target="_self" class="home-card">'
    f'<div class="home-card-icon" style="background:{bg}; color:{fg};">{_icon(paths, fg)}</div>'
    f'<div class="home-card-title">{title}</div>'
    f'<div class="home-card-desc">{desc}</div>'
    f'</a>'
    for href, title, desc, paths, fg, bg in CARDS
)
st.markdown(
    f'<div style="display:grid; grid-template-columns:repeat({len(CARDS)},1fr); '
    f'gap:16px; max-width:1080px; margin:0 auto;">{cards_html}</div>',
    unsafe_allow_html=True,
)

public_api = os.environ.get("PUBLIC_API_URL", "http://localhost:8000")
st.markdown(
f"""<div style="margin-top: 42px; text-align: center; padding: 20px 0; font-family: 'JetBrains Mono', monospace; font-size: 12.5px; color: #5b6675;">
<span>REST API · <a href="{public_api}/docs" target="_blank" style="color: {PRIMARY_LIGHT}; text-decoration: none;">{public_api}/docs</a></span>
<span style="opacity: 0.4; margin: 0 10px;">·</span>
<span>PostgreSQL · CatBoost ×24</span>
</div>""",
    unsafe_allow_html=True,
)
