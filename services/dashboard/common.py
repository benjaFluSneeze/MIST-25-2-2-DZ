import os
import requests
import streamlit as st

API_URL = os.environ.get("API_URL", "http://api:8000")


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


def post_predict(city_id: int, horizon_hours: int = 6) -> dict:
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
def get_feature_importance(model_name: str) -> list[dict]:
    r = requests.get(f"{API_URL}/predict/feature-importance/{model_name}", timeout=10)
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
        st.warning("В базе пока нет городов. Подождите первого запуска ingestor.")
        return None
    names = [c["name"] for c in cities]
    idx = st.sidebar.selectbox(label, range(len(names)), format_func=lambda i: names[i])
    return cities[idx]
