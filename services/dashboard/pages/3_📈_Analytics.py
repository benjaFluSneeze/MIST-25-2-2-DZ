import pandas as pd
import plotly.express as px
import streamlit as st

from common import get_cities, get_observations
from theme import apply_theme

apply_theme()

st.title("📈 Analytics")

try:
    cities = get_cities()
except Exception as e:  # noqa: BLE001
    st.error(f"Не удалось получить список городов: {e}")
    st.stop()
if not cities:
    st.warning("В базе пока нет городов.")
    st.stop()

names = [c["name"] for c in cities]
selected = st.sidebar.multiselect("Города для сравнения", names, default=names[:3])
period = st.sidebar.selectbox(
    "Период", [("Неделя", 168), ("Месяц", 24 * 30), ("Год", 24 * 365)],
    format_func=lambda x: x[0],
)
hours = period[1]

frames = []
for c in cities:
    if c["name"] not in selected:
        continue
    obs = get_observations(c["id"], hours=hours)
    if not obs:
        continue
    df = pd.DataFrame(obs)
    df["city"] = c["name"]
    frames.append(df)

if not frames:
    st.info("Нет данных по выбранным городам.")
    st.stop()

big = pd.concat(frames, ignore_index=True)
big["ts"] = pd.to_datetime(big["ts"], utc=True)
big = big.sort_values("ts")

st.subheader("Сравнение температур")
fig = px.line(big, x="ts", y="temperature_c", color="city",
              labels={"ts": "Время (UTC)", "temperature_c": "Температура, °C"})
fig.update_layout(height=450, margin=dict(t=30, b=20))
st.plotly_chart(fig, use_container_width=True)

st.subheader("Сезонность (средняя температура по месяцам)")
big["month"] = big["ts"].dt.month
agg = big.groupby(["city", "month"])["temperature_c"].mean().reset_index()
fig = px.line(agg, x="month", y="temperature_c", color="city", markers=True,
              labels={"month": "Месяц", "temperature_c": "Средняя °C"})
fig.update_layout(height=400, margin=dict(t=30, b=20))
st.plotly_chart(fig, use_container_width=True)

st.subheader("Аномалии: дни с отклонением температуры > 2σ от средней")
big["date"] = big["ts"].dt.date
daily = big.groupby(["city", "date"])["temperature_c"].mean().reset_index()
stats = daily.groupby("city")["temperature_c"].agg(["mean", "std"]).reset_index()
daily = daily.merge(stats, on="city")
daily["z"] = (daily["temperature_c"] - daily["mean"]) / daily["std"]
anomalies = daily[daily["z"].abs() > 2].sort_values("z", key=abs, ascending=False)
if anomalies.empty:
    st.info("Аномалий не найдено (мало данных или слишком ровный период).")
else:
    st.dataframe(
        anomalies[["city", "date", "temperature_c", "z"]].head(20),
        use_container_width=True,
    )
