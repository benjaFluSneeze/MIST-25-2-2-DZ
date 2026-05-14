import pandas as pd
import plotly.express as px
import streamlit as st

from _common import (
    city_selector,
    get_external_forecasts,
    get_feature_importance,
    get_metrics,
    get_observations,
    post_predict,
)

st.title("🔮 Predictions")

city = city_selector()
if city is None:
    st.stop()

horizon = st.sidebar.slider("Горизонт прогноза, часов", 1, 24, 6)

with st.spinner("Считаем прогноз..."):
    try:
        pred = post_predict(city["id"], horizon)
    except Exception as e:  # noqa: BLE001
        st.error(f"Не удалось получить прогноз: {e}")
        st.stop()

c1, c2, c3 = st.columns(3)
temp = pred["predicted_temperature_c"]
c1.metric("Темп. прогноз, °C", f"{temp:.1f}" if temp is not None else "—",
          help=f"На {pred['target_ts']} UTC")
p_rain = pred["predicted_rain_probability"]
c2.metric("Вероятность дождя", f"{p_rain*100:.0f}%" if p_rain is not None else "—")
c3.metric("Тип погоды", pred["predicted_condition"] or "—")

st.caption(f"Прогноз построен на основе наблюдения от {pred['based_on_ts']} UTC")

st.subheader("Наш прогноз vs Gismeteo")
ext = get_external_forecasts(city["id"], limit=14)
if ext:
    df_ext = pd.DataFrame(ext)
    df_ext["target_ts"] = pd.to_datetime(df_ext["target_ts"], utc=True)
    df_ext = df_ext.sort_values("target_ts")
    df_show = df_ext[["target_ts", "temperature_c", "precipitation_mm", "weather_main"]].copy()
    df_show.columns = ["target_ts (UTC)", "Gismeteo °C", "Gismeteo осадки", "Gismeteo условие"]
    st.dataframe(df_show, use_container_width=True)
else:
    st.info("Внешних прогнозов пока нет.")

st.subheader("Прогноз vs факт (за последние 7 дней)")
obs = get_observations(city["id"], hours=168, source="open_meteo")
if obs:
    df = pd.DataFrame(obs)
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df = df.sort_values("ts")
    fig = px.line(df, x="ts", y="temperature_c",
                  labels={"ts": "Время (UTC)", "temperature_c": "Температура, °C"})
    fig.add_scatter(
        x=[pd.to_datetime(pred["target_ts"])],
        y=[temp] if temp is not None else [None],
        mode="markers", marker=dict(size=14, color="red"),
        name=f"Наш прогноз (+{horizon}ч)",
    )
    fig.update_layout(height=400, margin=dict(t=30, b=20))
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Качество моделей (CV)")
try:
    metrics = get_metrics()
except Exception:  # noqa: BLE001
    metrics = {}

if metrics:
    c1, c2, c3 = st.columns(3)
    t = metrics.get("temperature", {})
    c1.metric(
        "Темп. CV-MAE, °C",
        f"{t.get('cv_mae_mean', float('nan')):.2f}" if t else "—",
        help=f"Naive baseline MAE: {t.get('naive_mae'):.2f}" if t.get("naive_mae") else None,
    )
    r = metrics.get("rain", {})
    c2.metric(
        "Дождь CV-Accuracy",
        f"{r.get('cv_accuracy_mean', float('nan'))*100:.1f}%" if r else "—",
        help=f"Naive baseline: {r.get('naive_accuracy', 0)*100:.1f}%" if r else None,
    )
    cnd = metrics.get("condition", {})
    c3.metric(
        "Условие CV-Accuracy",
        f"{cnd.get('cv_accuracy_mean', float('nan'))*100:.1f}%" if cnd else "—",
        help=f"Naive baseline: {cnd.get('naive_accuracy', 0)*100:.1f}%" if cnd else None,
    )
else:
    st.info("Метрики появятся после обучения моделей (см. README).")

st.subheader("Feature importance (температурная модель)")
fi = get_feature_importance("temperature")
if fi:
    df_fi = pd.DataFrame(fi).head(15)
    fig = px.bar(df_fi, x="importance", y="feature", orientation="h")
    fig.update_layout(height=450, margin=dict(t=30, b=20))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Feature importance появится после обучения моделей.")
