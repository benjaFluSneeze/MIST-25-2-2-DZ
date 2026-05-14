import pandas as pd
import streamlit as st

from _common import city_selector, get_observations

st.title("🗃️ Data")

city = city_selector()
if city is None:
    st.stop()

hours = st.sidebar.selectbox(
    "Период",
    [("Сутки", 24), ("Неделя", 168), ("Месяц", 24 * 30), ("Год", 24 * 365)],
    format_func=lambda x: x[0],
)[1]
source = st.sidebar.selectbox(
    "Источник", ["все", "open_meteo", "open_meteo_archive", "openweather"]
)
src_filter = None if source == "все" else source

obs = get_observations(city["id"], hours=hours, source=src_filter)
if not obs:
    st.info("Нет данных под фильтры.")
    st.stop()

df = pd.DataFrame(obs)
df["ts"] = pd.to_datetime(df["ts"], utc=True)
df = df.sort_values("ts", ascending=False).reset_index(drop=True)

search = st.text_input("Поиск по типу погоды (weather_main)")
if search:
    df = df[df["weather_main"].fillna("").str.contains(search, case=False)]

st.caption(f"Найдено записей: **{len(df)}**")

page_size = 50
total = max(1, (len(df) + page_size - 1) // page_size)
page = st.number_input("Страница", 1, total, 1)
start = (page - 1) * page_size
st.dataframe(df.iloc[start:start + page_size], use_container_width=True)
