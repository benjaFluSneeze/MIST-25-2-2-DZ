import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from common import (
    city_ru,
    city_selector,
    condition_ru,
    get_observations,
    source_ru,
)
from theme import (
    ACCENT, ACCENT_LIGHT, ICONS, PRIMARY, PRIMARY_DARK, PRIMARY_LIGHT, RAIN,
    WEATHER_COLORS, card_title, eyebrow, kpi_card, sidebar_status,
)

city = city_selector()
if city is None:
    sidebar_status()
    st.stop()

eyebrow("Обзор города")
st.markdown(
    f'<h2 style="margin: 0 0 8px;">{city_ru(city["name"])}</h2>',
    unsafe_allow_html=True,
)

obs = get_observations(city["id"], hours=168)
if not obs:
    st.warning("Нет данных по городу. Дождитесь первого запуска сбора данных.")
    sidebar_status()
    st.stop()

df = pd.DataFrame(obs)
df["ts"] = pd.to_datetime(df["ts"], utc=True)
df = df.sort_values("ts")
df["Источник"] = df["source"].map(source_ru)
df["Тип погоды"] = df["weather_main"].map(condition_ru)

latest = df.iloc[-1]
st.markdown(
    f'''<p style="font-size: 13.5px; color: #7b8798; margin: 0 0 22px;">
    Последнее обновление:
    <span style="color: #cbd5e1; font-family: \'JetBrains Mono\', monospace;">
    {latest["ts"]:%Y-%m-%d %H:%M UTC}</span>
    · источник:
    <span style="color: {PRIMARY_LIGHT}; font-family: \'JetBrains Mono\', monospace;">
    {source_ru(latest["source"])}</span>
    </p>''',
    unsafe_allow_html=True,
)

temp_value = f"{latest['temperature_c']:.1f}" if pd.notna(latest["temperature_c"]) else "—"
hum_value = f"{latest['humidity']:.0f}" if pd.notna(latest["humidity"]) else "—"
wind_value = f"{latest['wind_speed']:.1f}" if pd.notna(latest["wind_speed"]) else "—"
pres_value = f"{latest['pressure_hpa']:.0f}" if pd.notna(latest["pressure_hpa"]) else "—"

cond_sub = condition_ru(latest["weather_main"])
hum_sub = "высокая" if pd.notna(latest["humidity"]) and latest["humidity"] > 70 else "норма"
wind_sub = "сильный" if pd.notna(latest["wind_speed"]) and latest["wind_speed"] > 8 else "слабый"

c1, c2, c3, c4 = st.columns(4)
c1.markdown(
    kpi_card("Температура", temp_value, "°C", ICONS["sun"], accent="amber", sub=cond_sub),
    unsafe_allow_html=True,
)
c2.markdown(
    kpi_card("Влажность", hum_value, "%", ICONS["droplet"], sub=hum_sub),
    unsafe_allow_html=True,
)
c3.markdown(
    kpi_card("Ветер", wind_value, "м/с", ICONS["wind"], sub=wind_sub),
    unsafe_allow_html=True,
)
c4.markdown(
    kpi_card("Давление", pres_value, "hPa", ICONS["gauge"], sub="норма"),
    unsafe_allow_html=True,
)

st.markdown("<div style='height: 22px;'></div>", unsafe_allow_html=True)

# --- Temperature chart in glass card ---
st.markdown(
    '<div style="padding: 22px 24px 4px; border-radius: 18px;'
    'background: rgba(255,255,255,0.025);'
    'border: 1px solid rgba(148,163,184,0.1);'
    'backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);">'
    + card_title("Температура за неделю"),
    unsafe_allow_html=True,
)
fig_t = px.area(
    df, x="ts", y="temperature_c", color="Источник",
    labels={"ts": "Время (UTC)", "temperature_c": "°C"},
    color_discrete_sequence=[PRIMARY, PRIMARY_DARK, ACCENT],
)
fig_t.update_traces(line=dict(width=2.4, shape="spline", smoothing=1.0),
                     fillpattern=dict(shape=""))
for tr in fig_t.data:
    tr.update(fillcolor="rgba(110,197,214,0.18)")
fig_t.update_layout(height=320, margin=dict(t=10, b=20, l=0, r=0),
                     legend=dict(orientation="h", y=-0.18))
st.plotly_chart(fig_t, use_container_width=True)
st.markdown("</div><div style='height: 18px;'></div>", unsafe_allow_html=True)

# --- Bottom row: precipitation + pie ---
col1, col2 = st.columns(2)

with col1:
    st.markdown(
        '<div style="padding: 22px 24px 4px; border-radius: 18px;'
        'background: rgba(255,255,255,0.025);'
        'border: 1px solid rgba(148,163,184,0.1);'
        'backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);">'
        + card_title("Осадки, мм"),
        unsafe_allow_html=True,
    )
    fig_p = px.bar(
        df, x="ts", y="precipitation_mm",
        labels={"ts": "Время (UTC)", "precipitation_mm": "мм"},
    )
    fig_p.update_traces(marker_color=RAIN, marker_line_width=0)
    fig_p.update_layout(height=300, margin=dict(t=10, b=20, l=0, r=0), bargap=0.05)
    st.plotly_chart(fig_p, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown(
        '<div style="padding: 22px 24px 4px; border-radius: 18px;'
        'background: rgba(255,255,255,0.025);'
        'border: 1px solid rgba(148,163,184,0.1);'
        'backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);">'
        + card_title("Тип погоды · частоты"),
        unsafe_allow_html=True,
    )
    counts = df["Тип погоды"].value_counts().reset_index()
    counts.columns = ["Тип погоды", "Часов"]
    fig_pie = px.pie(
        counts, names="Тип погоды", values="Часов",
        color="Тип погоды",
        color_discrete_map=WEATHER_COLORS,
        hole=0.6,
    )
    fig_pie.update_traces(textposition="outside", textinfo="percent")
    fig_pie.update_layout(
        height=300, margin=dict(t=10, b=20, l=0, r=0),
        showlegend=True, legend=dict(orientation="v", y=0.5, x=1.05),
    )
    st.plotly_chart(fig_pie, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

sidebar_status()
