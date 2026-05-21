import os
import requests
import streamlit as st

API_URL = os.environ.get("API_URL", "http://api:8000")


CITY_NAMES_RU = {
    "Moscow": "Москва",
    "Saint Petersburg": "Санкт-Петербург",
    "Yekaterinburg": "Екатеринбург",
    "Novosibirsk": "Новосибирск",
    "Kazan": "Казань",
    "Sochi": "Сочи",
    "Vladivostok": "Владивосток",
}


def city_ru(name: str) -> str:
    return CITY_NAMES_RU.get(name, name)


SOURCE_NAMES_RU = {
    "open_meteo": "Open-Meteo (свежие)",
    "open_meteo_archive": "Open-Meteo (история)",
    "openweather": "OpenWeatherMap",
    "gismeteo": "Gismeteo",
}


def source_ru(name: str) -> str:
    return SOURCE_NAMES_RU.get(name, name)


CONDITION_NAMES_RU = {
    "Clear": "Ясно",
    "Clouds": "Облачно",
    "Rain": "Дождь",
    "Snow": "Снег",
    "Fog": "Туман",
    "Thunderstorm": "Гроза",
    "Unknown": "—",
}


def condition_ru(name: str | None) -> str:
    if not name:
        return "—"
    return CONDITION_NAMES_RU.get(name, name)


@st.cache_data(ttl=60)
def get_cities() -> list[dict]:
    r = requests.get(f"{API_URL}/data/cities", timeout=10)
    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=60)
def get_observations(city_id: int, hours: int = 168, source: str | None = None) -> list[dict]:
    params = {"city_id": city_id, "hours": hours}
    if source:
        params["source"] = source
    r = requests.get(f"{API_URL}/data/observations", params=params, timeout=20)
    if r.status_code == 404:
        return []
    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=120)
def get_external_forecasts(city_id: int, limit: int = 30) -> list[dict]:
    r = requests.get(
        f"{API_URL}/data/forecasts",
        params={"city_id": city_id, "limit": limit},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=30)
def get_ingest_runs(limit: int = 30) -> list[dict]:
    r = requests.get(f"{API_URL}/data/ingest-runs", params={"limit": limit}, timeout=10)
    r.raise_for_status()
    return r.json()


def post_predict(city_id: int, horizon_hours: int = 12) -> dict:
    r = requests.post(
        f"{API_URL}/predict",
        json={"city_id": city_id, "horizon_hours": horizon_hours},
        timeout=20,
    )
    r.raise_for_status()
    return r.json()


def post_predict_manual(payload: dict) -> dict:
    r = requests.post(f"{API_URL}/predict/manual", json=payload, timeout=20)
    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=300)
def get_metrics() -> dict:
    r = requests.get(f"{API_URL}/predict/metrics", timeout=10)
    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=300)
def get_horizons() -> dict:
    try:
        r = requests.get(f"{API_URL}/predict/horizons", timeout=10)
        if r.status_code != 200:
            return {"horizons": [12], "default": 12}
        return r.json()
    except Exception:  # noqa: BLE001
        return {"horizons": [12], "default": 12}


@st.cache_data(ttl=300)
def get_feature_importance(model_name: str, horizon: int = 12) -> list[dict]:
    r = requests.get(
        f"{API_URL}/predict/feature-importance/{model_name}",
        params={"horizon": horizon},
        timeout=10,
    )
    if r.status_code != 200:
        return []
    return r.json()


def city_selector(label: str = "Город") -> dict | None:
    try:
        cities = get_cities()
    except Exception as e:  # noqa: BLE001
        st.error(f"Не удалось получить список городов: {e}")
        return None
    if not cities:
        st.warning("В базе пока нет городов. Подождите первого сбора данных.")
        return None
    cities_sorted = sorted(cities, key=lambda c: city_ru(c["name"]))
    idx = st.sidebar.selectbox(
        label,
        range(len(cities_sorted)),
        format_func=lambda i: city_ru(cities_sorted[i]["name"]),
    )
    return cities_sorted[idx]
