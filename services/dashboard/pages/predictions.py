from datetime import timedelta

import pandas as pd
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
from theme import ACCENT, ACCENT_2, ACCENT_3, MUTED, SUCCESS, TEXT, WARNING

city = city_selector()
if city is None:
    st.stop()

st.title(f"🔮 Прогноз · {city_ru(city['name'])}")

# --- Horizon slider in sidebar ---
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

# --- Auto prediction at the selected horizon ---
with st.spinner("Считаем прогноз..."):
    try:
        pred = post_predict(city["id"], horizon)
    except Exception as e:  # noqa: BLE001
        st.error(f"Не удалось получить прогноз: {e}")
        st.stop()

temp = pred["predicted_temperature_c"]
p_rain = pred["predicted_rain_probability"]
target_ts = pd.to_datetime(pred["target_ts"], utc=True)

c1, c2, c3 = st.columns(3)
c1.metric(
    f"Прогноз температуры через +{horizon} ч, °C",
    f"{temp:.1f}" if temp is not None else "—",
    help=f"На {target_ts:%Y-%m-%d %H:%M UTC}",
)
c2.metric("Вероятность дождя", f"{p_rain*100:.0f}%" if p_rain is not None else "—")
c3.metric("Тип погоды", condition_ru(pred["predicted_condition"]))

st.caption(f"Прогноз построен на основе наблюдения от {pred['based_on_ts']} UTC")

# ---------------------------------------------------------------------------
# Chart: history (last 48h) + our prediction + Gismeteo curve for tomorrow
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Наш прогноз vs официальный (Gismeteo)")

obs = get_observations(city["id"], hours=48, source="open_meteo")
gismeteo = get_external_forecasts(city["id"], limit=40)

fig = go.Figure()

if obs:
    df_obs = pd.DataFrame(obs)
    df_obs["ts"] = pd.to_datetime(df_obs["ts"], utc=True)
    df_obs = df_obs.sort_values("ts")
    fig.add_trace(go.Scatter(
        x=df_obs["ts"], y=df_obs["temperature_c"],
        mode="lines",
        name="История (последние 48 ч)",
        line=dict(color=MUTED, width=2),
    ))

# Gismeteo line — only the most recent fetch (latest fetched_at per target_ts)
gismeteo_line_x: list = []
gismeteo_line_y: list = []
gismeteo_target_at_horizon: float | None = None
if gismeteo:
    df_g = pd.DataFrame(gismeteo)
    df_g["target_ts"] = pd.to_datetime(df_g["target_ts"], utc=True)
    df_g["fetched_at"] = pd.to_datetime(df_g["fetched_at"], utc=True)
    # keep only the latest fetch per target_ts
    df_g = df_g.sort_values("fetched_at").drop_duplicates("target_ts", keep="last")
    df_g = df_g.sort_values("target_ts")
    if not df_g.empty:
        gismeteo_line_x = df_g["target_ts"].tolist()
        gismeteo_line_y = df_g["temperature_c"].tolist()
        fig.add_trace(go.Scatter(
            x=gismeteo_line_x, y=gismeteo_line_y,
            mode="lines+markers",
            name="Gismeteo (прогноз на завтра)",
            line=dict(color=WARNING, width=2.5, dash="dot"),
            marker=dict(size=8, color=WARNING),
        ))
        # find Gismeteo value at the closest target_ts to our prediction
        deltas = (df_g["target_ts"] - target_ts).abs()
        idx = deltas.idxmin()
        if deltas.loc[idx] <= pd.Timedelta(hours=2):
            gismeteo_target_at_horizon = float(df_g.loc[idx, "temperature_c"])

# Our prediction as a single dot
if temp is not None:
    fig.add_trace(go.Scatter(
        x=[target_ts], y=[temp],
        mode="markers",
        name=f"Наш прогноз (+{horizon} ч)",
        marker=dict(size=16, color=ACCENT_3,
                    line=dict(width=2, color=TEXT)),
    ))

fig.update_layout(
    height=420,
    margin=dict(t=30, b=30),
    xaxis_title="Время (UTC)",
    yaxis_title="Температура, °C",
    legend=dict(orientation="h", y=-0.25),
)
st.plotly_chart(fig, use_container_width=True)

# Side-by-side KPI: ours vs Gismeteo at the same target time
if temp is not None and gismeteo_target_at_horizon is not None:
    diff = temp - gismeteo_target_at_horizon
    abs_diff = abs(diff)
    if abs_diff <= 1.5:
        badge_color = SUCCESS
        badge_text = "Прогнозы согласуются"
    elif abs_diff <= 3.5:
        badge_color = WARNING
        badge_text = "Умеренное расхождение"
    else:
        badge_color = ACCENT_3
        badge_text = "Сильное расхождение"
    c1, c2, c3 = st.columns(3)
    c1.metric(f"Наш прогноз (+{horizon} ч), °C", f"{temp:.1f}")
    c2.metric("Gismeteo на это же время, °C", f"{gismeteo_target_at_horizon:.1f}")
    c3.metric("Разница", f"{diff:+.1f} °C")
    st.markdown(
        f"""
        <div style="padding: 8px 14px; background: {badge_color}22;
                    border: 1px solid {badge_color}; border-radius: 8px;
                    color: {badge_color}; font-weight: 500; display: inline-block;">
            ● {badge_text}
        </div>
        """,
        unsafe_allow_html=True,
    )
elif gismeteo:
    st.info(
        "Прогнозы Gismeteo есть, но ни один не совпадает по времени "
        "с нашим выбранным горизонтом — слайдер промахнулся мимо его 3-часовой сетки."
    )
else:
    st.info(
        "Прогнозов от Gismeteo пока нет в базе. Подождите ближайший "
        "запуск сборщика (раз в 6 часов) или перезапустите ingestor."
    )

# ---------------------------------------------------------------------------
# What-if form
# ---------------------------------------------------------------------------
st.divider()
st.subheader("🧪 Что если: задайте свои условия")
st.caption(
    "Введите текущие условия — модель использует их вместо последнего "
    "наблюдения и пересчитает прогноз. История за прошлые часы берётся "
    "из базы данных города."
)

obs_recent = get_observations(city["id"], hours=2, source="open_meteo")
defaults = obs_recent[-1] if obs_recent else {}

with st.form("manual_predict"):
    f1, f2, f3 = st.columns(3)
    in_temp = f1.number_input(
        "Температура, °C", -60.0, 55.0,
        float(defaults.get("temperature_c") or 15.0), 0.5,
    )
    in_humidity = f2.number_input(
        "Влажность, %", 0.0, 100.0,
        float(defaults.get("humidity") or 60.0), 1.0,
    )
    in_pressure = f3.number_input(
        "Давление, hPa", 900.0, 1080.0,
        float(defaults.get("pressure_hpa") or 1013.0), 1.0,
    )

    f4, f5, f6 = st.columns(3)
    in_wind = f4.number_input(
        "Ветер, м/с", 0.0, 60.0,
        float(defaults.get("wind_speed") or 3.0), 0.5,
    )
    in_cloud = f5.number_input(
        "Облачность, %", 0.0, 100.0,
        float(defaults.get("cloud_cover") or 50.0), 5.0,
    )
    in_precip = f6.number_input(
        "Осадки, мм", 0.0, 100.0,
        float(defaults.get("precipitation_mm") or 0.0), 0.1,
    )

    submitted = st.form_submit_button("Посчитать прогноз")

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
        m1, m2, m3 = st.columns(3)
        mt = manual["predicted_temperature_c"]
        mp = manual["predicted_rain_probability"]
        m1.metric(
            "Прогноз температуры, °C",
            f"{mt:.1f}" if mt is not None else "—",
            delta=f"{(mt - temp):+.1f} к авто-прогнозу" if mt is not None and temp is not None else None,
        )
        m2.metric("Вероятность дождя", f"{mp*100:.0f}%" if mp is not None else "—")
        m3.metric("Тип погоды", condition_ru(manual["predicted_condition"]))

# ---------------------------------------------------------------------------
# CV metrics
# ---------------------------------------------------------------------------
st.divider()
st.subheader(f"Качество модели на горизонте +{horizon} ч (кросс-валидация)")
try:
    metrics = get_metrics()
except Exception:  # noqa: BLE001
    metrics = {}

if metrics:
    version = metrics.get("model_version", "—")
    trained_at = metrics.get("trained_at", "—")
    st.caption(f"Версия модели: `{version}` · обучена: {trained_at}")

    h_str = str(horizon)
    t = (metrics.get("temperature", {}).get("horizons") or {}).get(h_str, {})
    r = (metrics.get("rain", {}).get("horizons") or {}).get(h_str, {})
    cnd = (metrics.get("condition", {}).get("horizons") or {}).get(h_str, {})

    c1, c2, c3 = st.columns(3)
    c1.metric(
        "Темп.: средняя ошибка, °C",
        f"{t.get('cv_mae_mean', float('nan')):.2f}" if t else "—",
        help=f"Naive baseline: {t.get('naive_mae', 0):.2f} °C" if t else None,
    )
    c2.metric(
        "Дождь: точность",
        f"{r.get('cv_accuracy_mean', float('nan'))*100:.1f}%" if r else "—",
        help=f"Naive baseline: {r.get('naive_accuracy', 0)*100:.1f}%" if r else None,
    )
    c3.metric(
        "Тип погоды: точность",
        f"{cnd.get('cv_accuracy_mean', float('nan'))*100:.1f}%" if cnd else "—",
        help=f"Naive baseline: {cnd.get('naive_accuracy', 0)*100:.1f}%" if cnd else None,
    )

    # MAE-vs-horizon mini-chart so the user sees how the curves look across all 8 models
    temp_horizons = (metrics.get("temperature", {}).get("horizons") or {})
    if len(temp_horizons) > 1:
        h_rows = []
        for h_key, met in temp_horizons.items():
            h_rows.append({
                "Горизонт, ч": int(h_key),
                "MAE модели": met.get("cv_mae_mean"),
                "MAE naive": met.get("naive_mae"),
            })
        df_h = pd.DataFrame(h_rows).sort_values("Горизонт, ч")
        fig_h = go.Figure()
        fig_h.add_trace(go.Scatter(
            x=df_h["Горизонт, ч"], y=df_h["MAE naive"],
            mode="lines+markers", name="Naive (T(t+H) = T(t))",
            line=dict(color=MUTED, dash="dash"),
        ))
        fig_h.add_trace(go.Scatter(
            x=df_h["Горизонт, ч"], y=df_h["MAE модели"],
            mode="lines+markers", name="CatBoost (наша модель)",
            line=dict(color=ACCENT, width=2.5),
        ))
        fig_h.add_vline(
            x=horizon, line_dash="dot", line_color=ACCENT_2,
            annotation_text=f"+{horizon} ч (сейчас)",
            annotation_position="top right",
        )
        fig_h.update_layout(
            height=320, margin=dict(t=30, b=20),
            xaxis_title="Горизонт прогноза, ч",
            yaxis_title="MAE, °C",
            legend=dict(orientation="h", y=-0.3),
        )
        st.plotly_chart(fig_h, use_container_width=True)
else:
    st.info("Метрики появятся после обучения моделей (см. README).")

# ---------------------------------------------------------------------------
# Feature importance for the currently selected horizon
# ---------------------------------------------------------------------------
st.subheader("Важность признаков (модель температуры)")
fi = get_feature_importance("temperature", horizon)
if fi:
    descriptions = (metrics or {}).get("feature_descriptions", {})
    df_fi = pd.DataFrame(fi).head(15)
    df_fi["Описание"] = df_fi["feature"].map(lambda f: descriptions.get(f, f))
    df_fi = df_fi.rename(columns={"feature": "Признак", "importance": "Важность"})
    fig = go.Figure(go.Bar(
        x=df_fi["Важность"], y=df_fi["Признак"], orientation="h",
        marker_color=ACCENT,
        hovertext=df_fi["Описание"], hoverinfo="y+x+text",
    ))
    fig.update_layout(height=450, margin=dict(t=30, b=20),
                      yaxis=dict(autorange="reversed"),
                      xaxis_title="Важность", yaxis_title="Признак")
    st.plotly_chart(fig, use_container_width=True)
    with st.expander("Расшифровка признаков"):
        st.dataframe(
            df_fi[["Признак", "Описание", "Важность"]],
            use_container_width=True, hide_index=True,
        )
else:
    st.info("Важность признаков появится после обучения моделей.")
