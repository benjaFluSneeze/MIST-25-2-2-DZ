import os
import streamlit as st

st.set_page_config(page_title="WeatherML", page_icon="⛅", layout="wide")

st.title("⛅ WeatherML — прогноз погоды")
st.markdown(
    """
    Учебный проект: сбор погодных данных (Open-Meteo, OpenWeatherMap, Gismeteo),
    обучение ML-моделей и сравнение нашего прогноза с официальным.

    **Страницы** (выберите слева):
    - 📊 **Overview** — текущая ситуация и KPI по выбранному городу
    - 🔮 **Predictions** — прогноз нашей модели, сравнение с Gismeteo, метрики
    - 📈 **Analytics** — сравнение городов, тренды и сезонность
    - 🗃️ **Data** — таблица сырых наблюдений с фильтрами
    - 🛠️ **Monitoring** — статус источников данных
    """
)

api = os.environ.get("API_URL", "http://api:8000")
st.caption(f"API: `{api}`")
