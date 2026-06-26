import pandas as pd
import streamlit as st

from common import (
    SOURCE_NAMES_RU,
    city_ru,
    city_selector,
    condition_ru,
    get_observations,
    source_ru,
)
from theme import eyebrow

city = city_selector()
if city is None:
    st.stop()

eyebrow("Сырые данные")
st.markdown(
    f'<h2 style="margin: 0 0 22px;">Наблюдения · {city_ru(city["name"])}</h2>',
    unsafe_allow_html=True,
)

hours = st.sidebar.selectbox(
    "Период",
    [("Сутки", 24), ("Неделя", 168), ("Месяц", 24 * 30), ("Год", 24 * 365)],
    format_func=lambda x: x[0],
)[1]

source_options = ["все"] + list(SOURCE_NAMES_RU.keys())
source = st.sidebar.selectbox(
    "Источник",
    source_options,
    format_func=lambda s: "Все источники" if s == "все" else source_ru(s),
)
src_filter = None if source == "все" else source

obs = get_observations(city["id"], hours=hours, source=src_filter)
if not obs:
    st.info("Нет данных под выбранные фильтры.")
    st.stop()

df = pd.DataFrame(obs)
df["ts"] = pd.to_datetime(df["ts"], utc=True)
df = df.sort_values("ts", ascending=False).reset_index(drop=True)

search = st.text_input("Поиск по типу погоды (например: Дождь, Ясно)")
if search:
    mask_en = df["weather_main"].fillna("").str.contains(search, case=False)
    mask_ru = df["weather_main"].fillna("").map(condition_ru).str.contains(search, case=False)
    df = df[mask_en | mask_ru]

st.caption(f"Найдено записей: **{len(df)}**")

page_size = 50
total = max(1, (len(df) + page_size - 1) // page_size)
page = st.number_input("Страница", 1, total, 1)
start = (page - 1) * page_size

show = df.iloc[start:start + page_size].copy()
show["Источник"] = show["source"].map(source_ru)
show["Тип погоды"] = show["weather_main"].map(condition_ru)

display = show.rename(
    columns={
        "ts": "Время (UTC)",
        "temperature_c": "Температура, °C",
        "humidity": "Влажность, %",
        "pressure_hpa": "Давление, hPa",
        "wind_speed": "Ветер, м/с",
        "wind_direction": "Направление ветра, °",
        "cloud_cover": "Облачность, %",
        "precipitation_mm": "Осадки, мм",
    }
)[
    [
        "Время (UTC)", "Источник", "Температура, °C", "Влажность, %",
        "Давление, hPa", "Ветер, м/с", "Направление ветра, °",
        "Облачность, %", "Осадки, мм", "Тип погоды",
    ]
]
st.dataframe(display, use_container_width=True, hide_index=True)
