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
    ACCENT, ACCENT_LIGHT, ACCENT_MUTED,
    PRIMARY, PRIMARY_LIGHT, RAIN, STORM,
    TEXT, TEXT_LOW, MUTED, WEATHER_COLORS, eyebrow,
)

city = city_selector()
if city is None:
    st.stop()

eyebrow("Обзор города")
st.markdown(
    f'<h2 style="margin: 0 0 8px;">{city_ru(city["name"])}</h2>',
    unsafe_allow_html=True,
)

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
st.markdown(
    f'''<p style="font-size: 13.5px; color: #7b8798; margin: 0 0 26px;">
    Последнее обновление:
    <span style="color: #cbd5e1; font-family: \'JetBrains Mono\', monospace;">
    {latest["ts"]:%Y-%m-%d %H:%M UTC}</span>
    · источник:
    <span style="color: {PRIMARY_LIGHT}; font-family: \'JetBrains Mono\', monospace;">
    {source_ru(latest["source"])}</span>
    </p>''',
    unsafe_allow_html=True,
)


# --- KPI block: temperature with amber accent, rest neutral ---
def _kpi_card(label: str, value: str, unit: str, sub: str, accent: bool = False, color: str = TEXT) -> str:
    bg = "rgba(230,179,92,0.07)" if accent else "rgba(255,255,255,0.025)"
    border = "rgba(230,179,92,0.22)" if accent else "rgba(148,163,184,0.12)"
    label_color = ACCENT_MUTED if accent else TEXT_LOW
    sub_color = "#a98c5a" if accent else TEXT_LOW
    return f"""
    <div style="padding: 18px 20px; border-radius: 16px;
                background: {bg}; border: 1px solid {border};
                backdrop-filter: blur(14px);
                -webkit-backdrop-filter: blur(14px);">
        <div style="font-size: 11px; letter-spacing: 0.06em;
                    text-transform: uppercase; color: {label_color};
                    font-weight: 600; margin-bottom: 12px;">{label}</div>
        <div style="font-family: 'JetBrains Mono', monospace;
                    font-size: 32px; font-weight: 600; color: {color};
                    line-height: 1;">
            {value}<span style="font-size: 16px; color: {label_color};
                                margin-left: 3px;">{unit}</span>
        </div>
        <div style="font-size: 12px; color: {sub_color}; margin-top: 8px;">{sub}</div>
    </div>
    """


temp_value = f"{latest['temperature_c']:.1f}" if pd.notna(latest["temperature_c"]) else "—"
hum_value = f"{latest['humidity']:.0f}" if pd.notna(latest["humidity"]) else "—"
wind_value = f"{latest['wind_speed']:.1f}" if pd.notna(latest["wind_speed"]) else "—"
pres_value = f"{latest['pressure_hpa']:.0f}" if pd.notna(latest["pressure_hpa"]) else "—"

c1, c2, c3, c4 = st.columns(4)
c1.markdown(
    _kpi_card("Температура", temp_value, "°C", condition_ru(latest["weather_main"]),
              accent=True, color=ACCENT_LIGHT),
    unsafe_allow_html=True,
)
c2.markdown(
    _kpi_card("Влажность", hum_value, "%",
              "высокая" if pd.notna(latest["humidity"]) and latest["humidity"] > 70 else "норма",
              color=TEXT),
    unsafe_allow_html=True,
)
c3.markdown(
    _kpi_card("Ветер", wind_value, "м/с",
              "сильный" if pd.notna(latest["wind_speed"]) and latest["wind_speed"] > 8 else "слабый",
              color=TEXT),
    unsafe_allow_html=True,
)
c4.markdown(
    _kpi_card("Давление", pres_value, "hPa", "норма", color=TEXT),
    unsafe_allow_html=True,
)

st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

# --- Temperature chart in glass card ---
st.markdown(
    '<div style="padding: 22px 24px 4px; border-radius: 18px;'
    'background: rgba(255,255,255,0.025);'
    'border: 1px solid rgba(148,163,184,0.1);'
    'backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);">'
    '<h3 style="margin: 0 0 4px;">Температура за неделю</h3>',
    unsafe_allow_html=True,
)
fig_t = px.area(
    df, x="ts", y="temperature_c", color="Источник",
    labels={"ts": "Время (UTC)", "temperature_c": "°C"},
    color_discrete_sequence=[PRIMARY, PRIMARY_DARK := "#4ea3b8", ACCENT],
)
fig_t.update_traces(line=dict(width=2.4), fillcolor="rgba(110,197,214,0.15)")
fig_t.update_layout(height=340, margin=dict(t=10, b=20, l=0, r=0),
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
        '<h3 style="margin: 0 0 14px;">Осадки, мм</h3>',
        unsafe_allow_html=True,
    )
    fig_p = px.bar(
        df, x="ts", y="precipitation_mm",
        labels={"ts": "Время (UTC)", "precipitation_mm": "мм"},
    )
    fig_p.update_traces(marker_color=RAIN, marker_line_width=0)
    fig_p.update_layout(height=320, margin=dict(t=10, b=20, l=0, r=0), bargap=0.05)
    st.plotly_chart(fig_p, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown(
        '<div style="padding: 22px 24px 4px; border-radius: 18px;'
        'background: rgba(255,255,255,0.025);'
        'border: 1px solid rgba(148,163,184,0.1);'
        'backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);">'
        '<h3 style="margin: 0 0 14px;">Тип погоды · частоты</h3>',
        unsafe_allow_html=True,
    )
    counts = df["Тип погоды"].value_counts().reset_index()
    counts.columns = ["Тип погоды", "Часов"]
    fig_pie = px.pie(
        counts, names="Тип погоды", values="Часов",
        color="Тип погоды",
        color_discrete_map=WEATHER_COLORS,
        hole=0.55,
    )
    fig_pie.update_traces(textposition="outside", textinfo="percent")
    fig_pie.update_layout(
        height=320, margin=dict(t=10, b=20, l=0, r=0),
        showlegend=True, legend=dict(orientation="v", y=0.5, x=1.05),
    )
    st.plotly_chart(fig_pie, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
