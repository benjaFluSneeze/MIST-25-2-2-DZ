import pandas as pd
import plotly.express as px
import streamlit as st

from common import (
    city_ru,
    city_selector,
    condition_ru,
    get_external_forecasts,
    get_feature_importance,
    get_metrics,
    get_observations,
    post_predict,
    post_predict_manual,
)

city = city_selector()
if city is None:
    st.stop()

st.title(f"🔮 Прогноз · {city_ru(city['name'])}")

horizon = st.sidebar.slider("Горизонт прогноза, часов", 1, 24, 6)

with st.spinner("Считаем прогноз..."):
    try:
        pred = post_predict(city["id"], horizon)
    except Exception as e:  # noqa: BLE001
        st.error(f"Не удалось получить прогноз: {e}")
        st.stop()

c1, c2, c3 = st.columns(3)
temp = pred["predicted_temperature_c"]
c1.metric(
    "Прогноз температуры, °C",
    f"{temp:.1f}" if temp is not None else "—",
    help=f"На {pred['target_ts']} UTC",
)
p_rain = pred["predicted_rain_probability"]
c2.metric("Вероятность дождя", f"{p_rain*100:.0f}%" if p_rain is not None else "—")
c3.metric("Тип погоды", condition_ru(pred["predicted_condition"]))

st.caption(f"Прогноз построен на основе наблюдения от {pred['based_on_ts']} UTC")

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

st.divider()
st.subheader("Наш прогноз vs Gismeteo (на завтра)")
ext = get_external_forecasts(city["id"], limit=14)
if ext:
    df_ext = pd.DataFrame(ext)
    df_ext["target_ts"] = pd.to_datetime(df_ext["target_ts"], utc=True)
    df_ext = df_ext.sort_values("target_ts")
    df_ext["Тип погоды"] = df_ext["weather_main"].map(condition_ru)
    df_show = df_ext[["target_ts", "temperature_c", "precipitation_mm", "Тип погоды"]].copy()
    df_show.columns = ["Целевое время (UTC)", "Темп. Gismeteo, °C", "Осадки Gismeteo, мм", "Тип погоды"]
    st.dataframe(df_show, use_container_width=True, hide_index=True)
else:
    st.info("Внешних прогнозов пока нет.")

st.subheader("Прогноз и факт (за последние 7 дней)")
obs = get_observations(city["id"], hours=168, source="open_meteo")
if obs:
    df = pd.DataFrame(obs)
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df = df.sort_values("ts")
    fig = px.line(
        df, x="ts", y="temperature_c",
        labels={"ts": "Время (UTC)", "temperature_c": "Температура, °C"},
    )
    fig.add_scatter(
        x=[pd.to_datetime(pred["target_ts"])],
        y=[temp] if temp is not None else [None],
        mode="markers", marker=dict(size=14, color="#ec4899"),
        name=f"Наш прогноз (+{horizon} ч)",
    )
    fig.update_layout(height=400, margin=dict(t=30, b=20))
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Качество моделей (кросс-валидация)")
try:
    metrics = get_metrics()
except Exception:  # noqa: BLE001
    metrics = {}

if metrics:
    version = metrics.get("model_version", "—")
    trained_at = metrics.get("trained_at", "—")
    st.caption(f"Версия модели: `{version}` · обучена: {trained_at}")

    c1, c2, c3 = st.columns(3)
    t = metrics.get("temperature", {})
    c1.metric(
        "Темп.: средняя ошибка, °C",
        f"{t.get('cv_mae_mean', float('nan')):.2f}" if t else "—",
        help=f"Naive baseline: {t.get('naive_mae'):.2f}" if t.get("naive_mae") else None,
    )
    r = metrics.get("rain", {})
    c2.metric(
        "Дождь: точность",
        f"{r.get('cv_accuracy_mean', float('nan'))*100:.1f}%" if r else "—",
        help=f"Naive baseline: {r.get('naive_accuracy', 0)*100:.1f}%" if r else None,
    )
    cnd = metrics.get("condition", {})
    c3.metric(
        "Тип погоды: точность",
        f"{cnd.get('cv_accuracy_mean', float('nan'))*100:.1f}%" if cnd else "—",
        help=f"Naive baseline: {cnd.get('naive_accuracy', 0)*100:.1f}%" if cnd else None,
    )
else:
    st.info("Метрики появятся после обучения моделей (см. README).")

st.subheader("Важность признаков (модель температуры)")
fi = get_feature_importance("temperature")
if fi:
    descriptions = (metrics or {}).get("feature_descriptions", {})
    df_fi = pd.DataFrame(fi).head(15)
    df_fi["Описание"] = df_fi["feature"].map(lambda f: descriptions.get(f, f))
    df_fi = df_fi.rename(columns={"feature": "Признак", "importance": "Важность"})
    fig = px.bar(
        df_fi, x="Важность", y="Признак", orientation="h",
        hover_data=["Описание"],
    )
    fig.update_layout(height=450, margin=dict(t=30, b=20))
    st.plotly_chart(fig, use_container_width=True)
    with st.expander("Расшифровка признаков"):
        st.dataframe(
            df_fi[["Признак", "Описание", "Важность"]],
            use_container_width=True, hide_index=True,
        )
else:
    st.info("Важность признаков появится после обучения моделей.")
