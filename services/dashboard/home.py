import os
import streamlit as st

from theme import ACCENT

st.markdown(
    f"""
    <div style="text-align: center; padding: 60px 0 40px 0;">
        <div style="display: inline-block; padding: 6px 16px; background: rgba(99, 102, 241, 0.15);
                    border: 1px solid {ACCENT}; border-radius: 50px; font-size: 13px;
                    color: {ACCENT}; font-weight: 500; margin-bottom: 24px;">
            🌤️ Семестровый проект · WeatherML
        </div>
        <h1 style="font-size: clamp(2.5rem, 6vw, 4.5rem); margin: 0 0 16px 0;">
            Прогноз погоды на ML
        </h1>
        <p style="color: #94a3b8; font-size: 1.15rem; max-width: 640px; margin: 0 auto;">
            Сбор данных из нескольких источников, обучение моделей, сравнение
            нашего прогноза с официальным — всё в одном дашборде.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

cards = [
    ("📊", "Обзор", "Ключевые метрики и графики выбранного города за неделю"),
    ("🔮", "Прогноз", "ML-предсказание, what-if форма, сравнение с Gismeteo"),
    ("📈", "Аналитика", "Сравнение городов, сезонность, аномалии"),
    ("🗃️", "Данные", "Сырые наблюдения с фильтрами и поиском"),
    ("🛠️", "Мониторинг", "Статус источников и логи сбора данных"),
]

cols = st.columns(len(cards))
for col, (icon, title, desc) in zip(cols, cards):
    col.markdown(
        f"""
        <div style="background: linear-gradient(135deg, rgba(99, 102, 241, 0.08), rgba(139, 92, 246, 0.04));
                    border: 1px solid #2d2d4a; border-radius: 16px; padding: 20px;
                    height: 100%; backdrop-filter: blur(12px);">
            <div style="font-size: 28px; margin-bottom: 8px;">{icon}</div>
            <div style="color: #f1f5f9; font-weight: 600; font-size: 1rem; margin-bottom: 4px;">{title}</div>
            <div style="color: #94a3b8; font-size: 0.85rem; line-height: 1.4;">{desc}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<div style='height: 32px;'></div>", unsafe_allow_html=True)

api = os.environ.get("API_URL", "http://api:8000")
st.markdown(
    f"""
    <div style="text-align: center; color: #64748b; font-size: 0.85rem; padding: 20px 0;">
        REST API · <code>{api}</code> · документация <a href="{api}/docs" target="_blank"
            style="color: {ACCENT}; text-decoration: none;">/docs</a>
    </div>
    """,
    unsafe_allow_html=True,
)
