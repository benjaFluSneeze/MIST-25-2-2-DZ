import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from common import city_ru, get_cities, get_observations
from theme import (
    BORDER, CORAL, MUTED, PRIMARY, TEXT, TEXT_LOW, TEXT_MID,
    card_title, city_color, eyebrow, sidebar_status,
)

eyebrow("Аналитика")
st.markdown('<h2 style="margin: 0 0 26px;">Сравнение городов</h2>',
            unsafe_allow_html=True)

try:
    cities = get_cities()
except Exception as e:  # noqa: BLE001
    st.error(f"Не удалось получить список городов: {e}")
    sidebar_status()
    st.stop()
if not cities:
    st.warning("В базе пока нет городов.")
    sidebar_status()
    st.stop()

cities_sorted = sorted(cities, key=lambda c: city_ru(c["name"]))
ru_names = [city_ru(c["name"]) for c in cities_sorted]

# --- Sidebar: city chip selector ---
SS_KEY = "analytics_cmp_cities"
if SS_KEY not in st.session_state:
    st.session_state[SS_KEY] = ru_names[:3]


def _remove(name: str):
    st.session_state[SS_KEY] = [c for c in st.session_state[SS_KEY] if c != name]


def _add():
    pick = st.session_state.get("analytics_cmp_add")
    if pick and pick != "—" and pick not in st.session_state[SS_KEY]:
        st.session_state[SS_KEY].append(pick)
    st.session_state["analytics_cmp_add"] = "—"


st.sidebar.markdown(
    f'<div style="font-size:11px; letter-spacing:.06em; text-transform:uppercase;'
    f'color:{MUTED}; margin:6px 0 8px; font-weight:600;">Города для сравнения</div>',
    unsafe_allow_html=True,
)

# Chip rendering — every chip gets the city's own colour. Chip + X-button
# share a sidebar row so the user can remove with one click.
for ru in st.session_state[SS_KEY]:
    cc = city_color(ru)
    r = int(cc[1:3], 16); g = int(cc[3:5], 16); b = int(cc[5:7], 16)
    chip_col, btn_col = st.sidebar.columns([0.82, 0.18])
    chip_col.markdown(
        f'<div style="display:inline-flex; align-items:center; gap:7px;'
        f'padding:6px 10px; border-radius:8px; font-size:13px; font-weight:500;'
        f'color:{cc}; background:rgba({r},{g},{b},0.12); '
        f'border:1px solid rgba({r},{g},{b},0.32);">'
        f'<span style="width:7px;height:7px;border-radius:50%;background:{cc};">'
        f'</span>{ru}</div>',
        unsafe_allow_html=True,
    )
    btn_col.button("✕", key=f"rm_{ru}", on_click=_remove, args=(ru,),
                   help=f"Убрать {ru}")

remaining = ["—"] + [n for n in ru_names if n not in st.session_state[SS_KEY]]
if len(remaining) > 1:
    st.sidebar.selectbox(
        "Добавить город",
        remaining,
        key="analytics_cmp_add",
        on_change=_add,
        label_visibility="collapsed",
        format_func=lambda x: "+ добавить город" if x == "—" else x,
    )

period = st.sidebar.selectbox(
    "Период",
    [("Неделя", 168), ("Месяц", 24 * 30), ("Год", 24 * 365)],
    format_func=lambda x: x[0],
)
hours = period[1]

selected_ru = st.session_state[SS_KEY]
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
    st.info("Выберите хотя бы один город в сайдбаре, чтобы построить сравнение.")
    sidebar_status()
    st.stop()

big = pd.concat(frames, ignore_index=True)
big["ts"] = pd.to_datetime(big["ts"], utc=True)
big = big.sort_values("ts")

color_map = {ru: city_color(ru) for ru in selected_ru}

# --- Temperature comparison chart ---
st.markdown(
    '<div style="padding: 22px 24px 12px; border-radius: 18px;'
    'background: rgba(255,255,255,0.025);'
    'border: 1px solid rgba(148,163,184,0.1);'
    'backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);'
    'margin-bottom: 18px;">'
    + card_title("Сравнение температур"),
    unsafe_allow_html=True,
)
fig = px.line(
    big, x="ts", y="temperature_c", color="Город",
    color_discrete_map=color_map,
    labels={"ts": "Время (UTC)", "temperature_c": "Температура, °C"},
)
fig.update_traces(line=dict(width=2.2, shape="spline", smoothing=1.0))
fig.update_layout(height=420, margin=dict(t=10, b=30, l=0, r=0),
                   legend=dict(orientation="h", y=-0.22))
st.plotly_chart(fig, use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# --- Seasonality chart ---
st.markdown(
    '<div style="padding: 22px 24px 12px; border-radius: 18px;'
    'background: rgba(255,255,255,0.025);'
    'border: 1px solid rgba(148,163,184,0.1);'
    'backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);'
    'margin-bottom: 18px;">'
    + card_title("Сезонность · средняя температура по месяцам"),
    unsafe_allow_html=True,
)
big["month"] = big["ts"].dt.month
agg = big.groupby(["Город", "month"])["temperature_c"].mean().reset_index()
fig = px.line(
    agg, x="month", y="temperature_c", color="Город", markers=True,
    color_discrete_map=color_map,
    labels={"month": "Месяц", "temperature_c": "Средняя температура, °C"},
)
fig.update_traces(line=dict(width=2.2, shape="spline", smoothing=1.0),
                  marker=dict(size=8))
fig.update_layout(height=380, margin=dict(t=10, b=30, l=0, r=0),
                   legend=dict(orientation="h", y=-0.22))
st.plotly_chart(fig, use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# --- Anomalies table ---
st.markdown(
    '<h3 style="font-size:18px; font-weight:700; letter-spacing:-.02em; '
    'margin: 14px 0 14px;">Аномалии: дни с отклонением температуры более 2σ</h3>',
    unsafe_allow_html=True,
)
big["date"] = big["ts"].dt.date
daily = big.groupby(["Город", "date"])["temperature_c"].mean().reset_index()
stats = daily.groupby("Город")["temperature_c"].agg(["mean", "std"]).reset_index()
daily = daily.merge(stats, on="Город")
daily["z"] = (daily["temperature_c"] - daily["mean"]) / daily["std"]
anomalies = daily[daily["z"].abs() > 2].sort_values("z", key=abs, ascending=False)
if anomalies.empty:
    st.info("Аномалий не найдено (мало данных или слишком ровный период).")
else:
    rows_html = ""
    for _, row in anomalies.head(20).iterrows():
        cc = city_color(row["Город"])
        z = row["z"]
        z_color = CORAL if z > 0 else PRIMARY
        rows_html += (
            f'<div style="display:grid; grid-template-columns:1.2fr 1.4fr 1.2fr 1fr;'
            f'padding:13px 18px; font-size:13.5px; border-bottom:1px solid {BORDER};'
            f'align-items:center;">'
            f'<span style="display:flex;align-items:center;gap:8px;color:{TEXT};">'
            f'<span style="width:9px;height:9px;border-radius:50%;background:{cc};"></span>'
            f'<span style="font-weight:500;">{row["Город"]}</span></span>'
            f'<span style="color:{TEXT_MID};font-family:\'JetBrains Mono\',monospace;'
            f'font-size:12.5px;">{row["date"]}</span>'
            f'<span style="font-family:\'JetBrains Mono\',monospace;color:{TEXT_MID};">'
            f'T° = {row["temperature_c"]:+.1f} °C</span>'
            f'<span style="text-align:right;font-family:\'JetBrains Mono\',monospace;'
            f'font-weight:600;color:{z_color};">{z:+.2f}σ</span>'
            f'</div>'
        )
    st.markdown(
        f'<div style="border-radius:16px; border:1px solid {BORDER};'
        f'overflow:hidden; background:rgba(255,255,255,0.018);">'
        f'<div style="display:grid; grid-template-columns:1.2fr 1.4fr 1.2fr 1fr;'
        f'padding:13px 18px; background:rgba(255,255,255,0.03);'
        f'font-size:11px; letter-spacing:.05em; text-transform:uppercase;'
        f'color:{TEXT_LOW}; font-weight:600; border-bottom:1px solid {BORDER};">'
        f'<span>Город</span><span>Дата</span><span>Температура</span>'
        f'<span style="text-align:right;">Отклонение</span></div>'
        f'{rows_html}</div>',
        unsafe_allow_html=True,
    )

sidebar_status()
