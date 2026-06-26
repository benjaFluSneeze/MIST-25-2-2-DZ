import pandas as pd
import plotly.express as px
import streamlit as st

from common import city_ru, get_cities, get_observations
from theme import eyebrow, sidebar_status

eyebrow("Аналитика")
st.markdown('<h2 style="margin: 0 0 26px;">Сравнение городов</h2>',
            unsafe_allow_html=True)

try:
    cities = get_cities()
except Exception as e:  # noqa: BLE001
    st.error(f"Не удалось получить список городов: {e}")
    st.stop()
if not cities:
    st.warning("В базе пока нет городов.")
    st.stop()

cities_sorted = sorted(cities, key=lambda c: city_ru(c["name"]))
ru_names = [city_ru(c["name"]) for c in cities_sorted]
selected_ru = st.sidebar.multiselect(
    "Города для сравнения", ru_names, default=ru_names[:3]
)
period = st.sidebar.selectbox(
    "Период",
    [("Неделя", 168), ("Месяц", 24 * 30), ("Год", 24 * 365)],
    format_func=lambda x: x[0],
)
hours = period[1]

frames = []
for c in cities_sorted:
    ru = city_ru(c["name"])
    if ru not in selected_ru:
        continue
    obs = get_observations(c["id"], hours=hours)
    if not obs:
        continue
    df = pd.DataFrame(obs)
    df["Город"] = ru
    frames.append(df)

if not frames:
    st.info("Нет данных по выбранным городам.")
    st.stop()

big = pd.concat(frames, ignore_index=True)
big["ts"] = pd.to_datetime(big["ts"], utc=True)
big = big.sort_values("ts")

st.subheader("Сравнение температур")
fig = px.line(
    big, x="ts", y="temperature_c", color="Город",
    labels={"ts": "Время (UTC)", "temperature_c": "Температура, °C"},
)
fig.update_layout(height=450, margin=dict(t=30, b=20))
st.plotly_chart(fig, use_container_width=True)

st.subheader("Сезонность (средняя температура по месяцам)")
big["month"] = big["ts"].dt.month
agg = big.groupby(["Город", "month"])["temperature_c"].mean().reset_index()
fig = px.line(
    agg, x="month", y="temperature_c", color="Город", markers=True,
    labels={"month": "Месяц", "temperature_c": "Средняя температура, °C"},
)
fig.update_layout(height=400, margin=dict(t=30, b=20))
st.plotly_chart(fig, use_container_width=True)

st.subheader("Аномалии: дни с отклонением температуры более 2σ от средней")
big["date"] = big["ts"].dt.date
daily = big.groupby(["Город", "date"])["temperature_c"].mean().reset_index()
stats = daily.groupby("Город")["temperature_c"].agg(["mean", "std"]).reset_index()
daily = daily.merge(stats, on="Город")
daily["z"] = (daily["temperature_c"] - daily["mean"]) / daily["std"]
anomalies = daily[daily["z"].abs() > 2].sort_values("z", key=abs, ascending=False)
if anomalies.empty:
    st.info("Аномалий не найдено (мало данных или слишком ровный период).")
else:
    show = anomalies[["Город", "date", "temperature_c", "z"]].head(20).rename(
        columns={
            "date": "Дата",
            "temperature_c": "Средняя температура, °C",
            "z": "Отклонение (σ)",
        }
    )
    st.dataframe(show, use_container_width=True, hide_index=True)

sidebar_status()
