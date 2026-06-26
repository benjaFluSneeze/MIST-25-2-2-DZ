from datetime import timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from common import (
    city_ru,
    city_selector,
    condition_ru,
    get_external_forecasts,
    get_feature_importance,
    get_horizons,
    get_metrics,
    get_observations,
    post_predict,
    post_predict_manual,
)
from theme import (
    ACCENT, ACCENT_LIGHT, ACCENT_MUTED, ALERT, BORDER, CARD_BG, CORAL,
    MUTED, PRIMARY, PRIMARY_DARK, PRIMARY_LIGHT, RAIN_LIGHT, SUCCESS,
    TEXT, TEXT_LOW, TEXT_MID, WEATHER_COLORS, eyebrow,
)

city = city_selector()
if city is None:
    st.stop()

# --- Sidebar: horizon slider ---
horizon_info = get_horizons()
available_h = horizon_info.get("horizons") or [12]
default_h = horizon_info.get("default") or 12
if default_h not in available_h:
    default_h = available_h[len(available_h) // 2]

horizon = st.sidebar.select_slider(
    "Горизонт прогноза",
    options=available_h,
    value=default_h,
    format_func=lambda h: f"+{h} ч",
)
st.sidebar.caption(
    f"Под каждый горизонт обучена отдельная CatBoost-модель "
    f"({len(available_h)} моделей × 3 задачи)."
)

# --- Predict ---
with st.spinner("Считаем прогноз..."):
    try:
        pred = post_predict(city["id"], horizon)
    except Exception as e:  # noqa: BLE001
        st.error(f"Не удалось получить прогноз: {e}")
        st.stop()

temp = pred["predicted_temperature_c"]
p_rain = pred["predicted_rain_probability"]
target_ts = pd.to_datetime(pred["target_ts"], utc=True)

try:
    from zoneinfo import ZoneInfo
    city_tz = ZoneInfo(city.get("timezone") or "UTC")
except Exception:  # noqa: BLE001
    city_tz = None


def _to_local(ts):
    if city_tz is None or ts is None:
        return ts
    if hasattr(ts, "tz_convert"):
        return ts.tz_convert(city_tz)
    return ts.astimezone(city_tz)


tz_label = (city.get("timezone") or "UTC").split("/")[-1].replace("_", " ")
target_ts_local = _to_local(target_ts)
based_on_local = _to_local(pd.to_datetime(pred["based_on_ts"], utc=True))

# --- Page heading ---
eyebrow("Прогноз модели")
st.markdown(
    f'<h2 style="margin: 0 0 8px;">{city_ru(city["name"])} · +{horizon} ч</h2>'
    f'<p style="font-size: 13.5px; color: #7b8798; margin: 0 0 22px;">'
    f'Прогноз построен на основе наблюдения от '
    f'<span style="color: #cbd5e1; font-family: \'JetBrains Mono\', monospace;">'
    f'{based_on_local:%Y-%m-%d %H:%M}</span> ({tz_label})</p>',
    unsafe_allow_html=True,
)


# --- KPI block ---
def _kpi_card(label: str, value: str, unit: str, accent: str | None = None,
              extra: str = "") -> str:
    if accent == "amber":
        bg = "rgba(230,179,92,0.07)"
        border = "rgba(230,179,92,0.22)"
        label_color = ACCENT_MUTED
        value_color = ACCENT_LIGHT
        unit_color = ACCENT_MUTED
    elif accent == "rain":
        bg = CARD_BG
        border = BORDER
        label_color = TEXT_LOW
        value_color = RAIN_LIGHT
        unit_color = TEXT_LOW
    else:
        bg = CARD_BG
        border = BORDER
        label_color = TEXT_LOW
        value_color = TEXT
        unit_color = TEXT_LOW
    return f"""
    <div style="padding: 18px 20px; border-radius: 16px;
                background: {bg}; border: 1px solid {border};
                backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);">
        <div style="font-size: 11px; letter-spacing: 0.06em;
                    text-transform: uppercase; color: {label_color};
                    font-weight: 600; margin-bottom: 12px;">{label}</div>
        <div style="font-family: 'JetBrains Mono', monospace;
                    font-size: 38px; font-weight: 600; color: {value_color};
                    line-height: 1;">
            {value}<span style="font-size: 18px; color: {unit_color};
                                margin-left: 3px;">{unit}</span>
        </div>
        {extra}
    </div>
    """


c1, c2, c3 = st.columns(3)
c1.markdown(
    _kpi_card(
        f"Прогноз T° через +{horizon} ч",
        f"{temp:.1f}" if temp is not None else "—",
        "°C",
        accent="amber",
    ),
    unsafe_allow_html=True,
)
c2.markdown(
    _kpi_card(
        "Вероятность дождя",
        f"{p_rain*100:.0f}" if p_rain is not None else "—",
        "%",
        accent="rain",
    ),
    unsafe_allow_html=True,
)
cond = condition_ru(pred["predicted_condition"])
cond_color = WEATHER_COLORS.get(cond, TEXT_MID)
c3.markdown(
    f"""
    <div style="padding: 18px 20px; border-radius: 16px;
                background: {CARD_BG}; border: 1px solid {BORDER};
                backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);">
        <div style="font-size: 11px; letter-spacing: 0.06em;
                    text-transform: uppercase; color: {TEXT_LOW};
                    font-weight: 600; margin-bottom: 12px;">Тип погоды</div>
        <div style="display: flex; align-items: center; gap: 10px;">
            <span style="width: 14px; height: 14px; border-radius: 4px;
                         background: {cond_color};"></span>
            <span style="font-size: 30px; font-weight: 700;
                         letter-spacing: -0.02em;">{cond}</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

# --- Main forecast chart ---
obs = get_observations(city["id"], hours=48, source="open_meteo")
gismeteo = get_external_forecasts(city["id"], limit=60)
now_utc = pd.Timestamp.now(tz="UTC")
chart_start = now_utc - pd.Timedelta(hours=48)
chart_end = max(now_utc + pd.Timedelta(hours=36), target_ts + pd.Timedelta(hours=3))

st.markdown(
    '<div style="padding: 22px 24px 12px; border-radius: 18px;'
    'background: rgba(255,255,255,0.025);'
    'border: 1px solid rgba(148,163,184,0.1);'
    'backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);">'
    '<h3 style="margin: 0 0 16px;">Наш прогноз vs официальный (Gismeteo)</h3>',
    unsafe_allow_html=True,
)

fig = go.Figure()

if obs:
    df_obs = pd.DataFrame(obs)
    df_obs["ts"] = pd.to_datetime(df_obs["ts"], utc=True)
    df_obs = df_obs[df_obs["ts"] <= now_utc].sort_values("ts")
    if not df_obs.empty:
        x_obs = df_obs["ts"].dt.tz_convert(city_tz) if city_tz else df_obs["ts"]
        fig.add_trace(go.Scatter(
            x=x_obs, y=df_obs["temperature_c"],
            mode="lines",
            name="История (факт)",
            line=dict(color="#7b8798", width=2),
        ))

gismeteo_target_at_horizon: float | None = None
if gismeteo:
    df_g = pd.DataFrame(gismeteo)
    df_g["target_ts"] = pd.to_datetime(df_g["target_ts"], utc=True)
    df_g["fetched_at"] = pd.to_datetime(df_g["fetched_at"], utc=True)
    df_g = df_g[df_g["target_ts"] >= now_utc - pd.Timedelta(hours=3)]
    df_g = df_g.sort_values("fetched_at").drop_duplicates("target_ts", keep="last")
    df_g = df_g.sort_values("target_ts").reset_index(drop=True)
    if not df_g.empty:
        x_g = df_g["target_ts"].dt.tz_convert(city_tz) if city_tz else df_g["target_ts"]
        fig.add_trace(go.Scatter(
            x=x_g, y=df_g["temperature_c"],
            mode="lines+markers",
            name="Gismeteo (на завтра)",
            line=dict(color=ACCENT, width=2.2, dash="dot"),
            marker=dict(size=7, color=ACCENT),
        ))
        deltas = (df_g["target_ts"] - target_ts).abs()
        idx = deltas.idxmin()
        if deltas.loc[idx] <= pd.Timedelta(hours=2):
            gismeteo_target_at_horizon = float(df_g.loc[idx, "temperature_c"])

if temp is not None:
    fig.add_trace(go.Scatter(
        x=[target_ts_local if city_tz else target_ts], y=[temp],
        mode="markers",
        name=f"Наш прогноз (+{horizon} ч)",
        marker=dict(size=16, color=CORAL,
                    line=dict(width=2, color="#0e131d")),
    ))

fig.update_layout(
    height=380,
    margin=dict(t=10, b=30, l=0, r=0),
    xaxis_title=f"Время ({tz_label})" if city_tz else "Время (UTC)",
    yaxis_title="Температура, °C",
    legend=dict(orientation="h", y=-0.22),
)
chart_start_x = chart_start.tz_convert(city_tz) if city_tz else chart_start
chart_end_x = chart_end.tz_convert(city_tz) if city_tz else chart_end
fig.update_xaxes(range=[chart_start_x, chart_end_x])
st.plotly_chart(fig, use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# --- Comparison KPI row (when both forecasts exist) ---
if temp is not None and gismeteo_target_at_horizon is not None:
    diff = temp - gismeteo_target_at_horizon
    abs_diff = abs(diff)
    if abs_diff <= 1.5:
        delta_color = SUCCESS
    elif abs_diff <= 3.5:
        delta_color = ACCENT
    else:
        delta_color = ALERT
    st.markdown(
        f"""
        <div style="margin-top: 18px; padding: 22px 24px;
                    border-radius: 18px;
                    background: rgba(255,255,255,0.025);
                    border: 1px solid rgba(148,163,184,0.1);
                    display: grid;
                    grid-template-columns: 1fr auto 1fr auto 1fr;
                    gap: 18px; align-items: center;">
            <div style="text-align: center;">
                <div style="font-size: 12px; color: #7b8798; margin-bottom: 8px;">Наш прогноз</div>
                <div style="font-family: 'JetBrains Mono', monospace;
                            font-size: 30px; font-weight: 600; color: {CORAL};">
                    {temp:.1f}°C
                </div>
            </div>
            <div style="width: 1px; height: 46px; background: rgba(148,163,184,0.14);"></div>
            <div style="text-align: center;">
                <div style="font-size: 12px; color: #7b8798; margin-bottom: 8px;">Gismeteo</div>
                <div style="font-family: 'JetBrains Mono', monospace;
                            font-size: 30px; font-weight: 600; color: {ACCENT};">
                    {gismeteo_target_at_horizon:.1f}°C
                </div>
            </div>
            <div style="width: 1px; height: 46px; background: rgba(148,163,184,0.14);"></div>
            <div style="text-align: center;">
                <div style="font-size: 12px; color: #7b8798; margin-bottom: 8px;">Δ расхождение</div>
                <div style="font-family: 'JetBrains Mono', monospace;
                            font-size: 30px; font-weight: 600; color: {delta_color};">
                    {diff:+.1f}°C
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<div style='height: 26px;'></div>", unsafe_allow_html=True)

# --- What-if form ---
st.markdown(
    '<h3 style="margin: 0 0 6px;">Что если…</h3>'
    '<p style="font-size: 13px; color: #7b8798; margin: 0 0 18px;">'
    'Подставьте свои значения и посмотрите как изменится прогноз модели.</p>',
    unsafe_allow_html=True,
)

obs_recent = get_observations(city["id"], hours=2, source="open_meteo")
defaults = obs_recent[-1] if obs_recent else {}

with st.form("manual_predict"):
    f1, f2, f3 = st.columns(3)
    in_temp = f1.number_input("Температура, °C", -60.0, 55.0,
                               float(defaults.get("temperature_c") or 15.0), 0.5)
    in_humidity = f2.number_input("Влажность, %", 0.0, 100.0,
                                   float(defaults.get("humidity") or 60.0), 1.0)
    in_pressure = f3.number_input("Давление, hPa", 900.0, 1080.0,
                                   float(defaults.get("pressure_hpa") or 1013.0), 1.0)
    f4, f5, f6 = st.columns(3)
    in_wind = f4.number_input("Ветер, м/с", 0.0, 60.0,
                               float(defaults.get("wind_speed") or 3.0), 0.5)
    in_cloud = f5.number_input("Облачность, %", 0.0, 100.0,
                                float(defaults.get("cloud_cover") or 50.0), 5.0)
    in_precip = f6.number_input("Осадки, мм", 0.0, 100.0,
                                 float(defaults.get("precipitation_mm") or 0.0), 0.1)
    submitted = st.form_submit_button("✨ Рассчитать прогноз")

if submitted:
    payload = {
        "city_id": city["id"],
        "horizon_hours": horizon,
        "temperature_c": in_temp,
        "humidity": in_humidity,
        "pressure_hpa": in_pressure,
        "wind_speed": in_wind,
        "cloud_cover": in_cloud,
        "precipitation_mm": in_precip,
    }
    try:
        manual = post_predict_manual(payload)
    except Exception as e:  # noqa: BLE001
        st.error(f"Не удалось посчитать прогноз: {e}")
    else:
        mt = manual["predicted_temperature_c"]
        mp = manual["predicted_rain_probability"]
        mc = condition_ru(manual["predicted_condition"])
        delta = f"{(mt - temp):+.1f} к авто" if mt is not None and temp is not None else None
        m1, m2, m3 = st.columns(3)
        m1.metric("Прогноз T°, °C", f"{mt:.1f}" if mt is not None else "—", delta)
        m2.metric("P(дождь)", f"{mp*100:.0f}%" if mp is not None else "—")
        m3.metric("Тип погоды", mc)

st.markdown("<div style='height: 26px;'></div>", unsafe_allow_html=True)

# --- CV metrics ---
try:
    metrics = get_metrics()
except Exception:  # noqa: BLE001
    metrics = {}

col_cv, col_fi = st.columns([1, 1])

with col_cv:
    st.markdown(
        '<div style="padding: 22px 24px; border-radius: 18px;'
        'background: rgba(255,255,255,0.025);'
        'border: 1px solid rgba(148,163,184,0.1);">'
        '<h3 style="font-size: 15px; margin: 0 0 16px;">Метрики кросс-валидации</h3>',
        unsafe_allow_html=True,
    )
    if metrics:
        h_str = str(horizon)
        t_m = (metrics.get("temperature", {}).get("horizons") or {}).get(h_str, {})
        r_m = (metrics.get("rain", {}).get("horizons") or {}).get(h_str, {})
        cnd_m = (metrics.get("condition", {}).get("horizons") or {}).get(h_str, {})
        version = metrics.get("model_version", "—")
        st.caption(f"Версия модели: `{version}`")

        items = [
            ("T° CV-MAE", f"{t_m.get('cv_mae_mean', float('nan')):.2f} °C" if t_m else "—",
             ACCENT, f"naive: {t_m.get('naive_mae', 0):.2f}" if t_m else ""),
            ("Дождь CV-Acc",
             f"{r_m.get('cv_accuracy_mean', 0)*100:.1f}%" if r_m else "—",
             RAIN_LIGHT, f"F1: {r_m.get('cv_f1_mean', 0):.2f}" if r_m else ""),
            ("Тип погоды Acc",
             f"{cnd_m.get('cv_accuracy_mean', 0)*100:.1f}%" if cnd_m else "—",
             PRIMARY, f"F1: {cnd_m.get('cv_macro_f1_mean', 0):.2f}" if cnd_m else ""),
            ("Горизонт",
             f"+{horizon} ч",
             TEXT_LOW, ""),
        ]
        cols = st.columns(2)
        for i, (label, val, clr, sub) in enumerate(items):
            col = cols[i % 2]
            col.markdown(
                f"""
                <div style="padding: 14px 16px; border-radius: 12px;
                            background: rgba(255,255,255,0.025);
                            border: 1px solid rgba(148,163,184,0.1);
                            margin-bottom: 10px;">
                    <div style="font-size: 11px; color: #7b8798;
                                margin-bottom: 6px;">{label}</div>
                    <div style="font-family: 'JetBrains Mono', monospace;
                                font-size: 20px; font-weight: 600; color: {clr};">{val}</div>
                    <div style="font-size: 10.5px; color: #5b6675;
                                margin-top: 4px; font-family: 'JetBrains Mono', monospace;">
                        {sub}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("Метрики появятся после обучения моделей.")
    st.markdown("</div>", unsafe_allow_html=True)

with col_fi:
    st.markdown(
        '<div style="padding: 22px 24px; border-radius: 18px;'
        'background: rgba(255,255,255,0.025);'
        'border: 1px solid rgba(148,163,184,0.1);">'
        '<h3 style="font-size: 15px; margin: 0 0 16px;">Важность признаков</h3>',
        unsafe_allow_html=True,
    )
    fi = get_feature_importance("temperature", horizon)
    if fi:
        descriptions = (metrics or {}).get("feature_descriptions", {})
        df_fi = pd.DataFrame(fi).head(10)
        df_fi["Описание"] = df_fi["feature"].map(lambda f: descriptions.get(f, f))
        max_imp = df_fi["importance"].max() if not df_fi.empty else 1
        for _, row in df_fi.iterrows():
            pct = (row["importance"] / max_imp * 100) if max_imp else 0
            st.markdown(
                f"""
                <div style="margin-bottom: 10px;">
                    <div style="display: flex; justify-content: space-between;
                                font-size: 12.5px; margin-bottom: 5px;">
                        <span style="color: #cbd5e1;
                                     font-family: 'JetBrains Mono', monospace;">
                            {row["feature"]}</span>
                        <span style="color: #7b8798;
                                     font-family: 'JetBrains Mono', monospace;">
                            {row["importance"]:.1f}</span>
                    </div>
                    <div style="height: 7px; border-radius: 99px;
                                background: rgba(148,163,184,0.1); overflow: hidden;">
                        <div style="height: 100%; width: {pct:.1f}%;
                                    border-radius: 99px;
                                    background: linear-gradient(90deg, {PRIMARY_DARK}, {PRIMARY});">
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("Появится после обучения моделей.")
    st.markdown("</div>", unsafe_allow_html=True)
