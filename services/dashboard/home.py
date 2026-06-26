import os
import streamlit as st

from theme import ACCENT, PRIMARY, PRIMARY_LIGHT

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

cards = [
    ("📊", "Обзор", "Текущая погода, KPI и история выбранного города"),
    ("🔮", "Прогноз", "ML-предсказание, what-if форма, сравнение с Gismeteo"),
    ("📈", "Аналитика", "Сравнение городов, сезонность, аномалии"),
    ("🗃️", "Данные", "Сырые наблюдения с фильтрами и поиском"),
    ("🛠️", "Мониторинг", "Статус источников и логи сборщика"),
]

cols = st.columns(len(cards))
for col, (icon, title, desc) in zip(cols, cards):
    col.markdown(
f"""<div style="background: rgba(255,255,255,0.035); border: 1px solid rgba(148,163,184,0.12); border-radius: 18px; padding: 22px 20px; height: 100%; backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);">
<div style="font-size: 28px; margin-bottom: 12px;">{icon}</div>
<div style="color: #e9eef6; font-weight: 600; font-size: 15.5px; margin-bottom: 6px;">{title}</div>
<div style="color: #7b8798; font-size: 13px; line-height: 1.5;">{desc}</div>
</div>""",
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
