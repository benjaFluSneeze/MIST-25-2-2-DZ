import pandas as pd
import plotly.express as px
import streamlit as st

from common import (
    city_ru,
    city_selector,
    condition_ru,
    get_observations,
    source_ru,
)

city = city_selector()
if city is None:
    st.stop()

st.title(f"📊 Обзор · {city_ru(city['name'])}")

obs = get_observations(city["id"], hours=168)
if not obs:
    st.warning("Нет данных по городу. Дождитесь первого запуска сбора данных.")
    st.stop()

df = pd.DataFrame(obs)
df["ts"] = pd.to_datetime(df["ts"], utc=True)
df = df.sort_values("ts")
df["Источник"] = df["source"].map(source_ru)
df["Тип погоды"] = df["weather_main"].map(condition_ru)

latest = df.iloc[-1]

st.caption(
    f"Последнее обновление: **{latest['ts']:%Y-%m-%d %H:%M UTC}** · "
    f"источник: `{source_ru(latest['source'])}`"
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Температура, °C", f"{latest['temperature_c']:.1f}" if pd.notna(latest['temperature_c']) else "—")
c2.metric("Влажность, %", f"{latest['humidity']:.0f}" if pd.notna(latest['humidity']) else "—")
c3.metric("Ветер, м/с", f"{latest['wind_speed']:.1f}" if pd.notna(latest['wind_speed']) else "—")
c4.metric("Давление, hPa", f"{latest['pressure_hpa']:.0f}" if pd.notna(latest['pressure_hpa']) else "—")

st.subheader("Температура за неделю")
fig = px.line(
    df, x="ts", y="temperature_c", color="Источник",
    labels={"ts": "Время (UTC)", "temperature_c": "Температура, °C"},
)
fig.update_layout(height=400, margin=dict(t=30, b=20))
st.plotly_chart(fig, use_container_width=True)

col1, col2 = st.columns(2)
with col1:
    st.subheader("Осадки")
    fig = px.bar(
        df, x="ts", y="precipitation_mm",
        labels={"ts": "Время (UTC)", "precipitation_mm": "Осадки, мм"},
    )
    fig.update_layout(height=350, margin=dict(t=30, b=20))
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Тип погоды (частоты)")
    counts = df["Тип погоды"].value_counts().reset_index()
    counts.columns = ["Тип погоды", "Часов"]
    fig = px.pie(counts, names="Тип погоды", values="Часов")
    fig.update_layout(height=350, margin=dict(t=30, b=20))
    st.plotly_chart(fig, use_container_width=True)
