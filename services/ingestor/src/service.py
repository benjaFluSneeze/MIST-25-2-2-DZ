import logging
import os
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .cities import CITIES
from .collectors import gismeteo_parser, open_meteo, openweather
from .db import SessionLocal
from .models import City, ExternalForecast, IngestRun, WeatherObservation

log = logging.getLogger(__name__)


def ensure_cities() -> dict[str, City]:
    """Make sure all CITIES exist in DB. Return name -> City map."""
    with SessionLocal() as s:
        existing = {c.name: c for c in s.execute(select(City)).scalars().all()}
        for cfg in CITIES:
            if cfg["name"] not in existing:
                city = City(
                    name=cfg["name"], lat=cfg["lat"], lon=cfg["lon"], timezone=cfg["tz"]
                )
                s.add(city)
        s.commit()
        return {c.name: c for c in s.execute(select(City)).scalars().all()}


def _upsert_observations(rows: list[dict], city_id: int, source: str) -> int:
    if not rows:
        return 0
    payload = [{**r, "city_id": city_id, "source": source} for r in rows]
    with SessionLocal() as s:
        stmt = pg_insert(WeatherObservation).values(payload)
        stmt = stmt.on_conflict_do_nothing(index_elements=["city_id", "ts", "source"])
        result = s.execute(stmt)
        s.commit()
        return result.rowcount or 0


def _log_run(source: str, fn) -> None:
    started = datetime.now(timezone.utc)
    with SessionLocal() as s:
        run = IngestRun(source=source, started_at=started, status="running")
        s.add(run)
        s.commit()
        run_id = run.id
    try:
        inserted = fn()
        status = "ok"
        err = None
    except Exception as e:  # noqa: BLE001
        log.exception("ingest %s failed", source)
        inserted = 0
        status = "error"
        err = str(e)[:500]
    with SessionLocal() as s:
        run = s.get(IngestRun, run_id)
        run.finished_at = datetime.now(timezone.utc)
        run.status = status
        run.rows_inserted = inserted
        run.error = err
        s.commit()


def backfill_history():
    years = int(os.environ.get("INGEST_BACKFILL_YEARS", "2"))
    start_date, end_date = open_meteo.backfill_range(years)
    log.info("backfill open-meteo history %s..%s", start_date, end_date)
    cities = ensure_cities()

    def _do():
        total = 0
        for cfg in CITIES:
            city = cities[cfg["name"]]
            with SessionLocal() as s:
                already = s.execute(
                    select(WeatherObservation.id)
                    .where(WeatherObservation.city_id == city.id)
                    .where(WeatherObservation.source == "open_meteo_archive")
                    .limit(1)
                ).first()
            if already:
                log.info("skip backfill for %s (already present)", cfg["name"])
                continue
            try:
                rows = open_meteo.fetch_history(
                    cfg["lat"], cfg["lon"], start_date, end_date, cfg["tz"]
                )
            except Exception as e:  # noqa: BLE001
                log.warning("open-meteo history failed for %s: %s", cfg["name"], e)
                continue
            total += _upsert_observations(rows, city.id, "open_meteo_archive")
            log.info("%s: backfilled %d hourly rows", cfg["name"], len(rows))
        return total

    _log_run("open_meteo_backfill", _do)


def ingest_recent():
    cities = ensure_cities()
    api_key = os.environ.get("OPENWEATHER_API_KEY", "").strip()

    def _do():
        total = 0
        for cfg in CITIES:
            city = cities[cfg["name"]]
            try:
                rows = open_meteo.fetch_recent(cfg["lat"], cfg["lon"], cfg["tz"], past_days=2)
                total += _upsert_observations(rows, city.id, "open_meteo")
            except Exception as e:  # noqa: BLE001
                log.warning("open-meteo recent failed for %s: %s", cfg["name"], e)

            if api_key:
                ow = openweather.fetch_current(cfg["lat"], cfg["lon"], api_key)
                if ow:
                    total += _upsert_observations([ow], city.id, "openweather")
        return total

    _log_run("recent", _do)


def ingest_external_forecast():
    cities = ensure_cities()

    def _do():
        total = 0
        for cfg in CITIES:
            city = cities[cfg["name"]]
            data = gismeteo_parser.fetch_tomorrow(cfg["gismeteo_slug"])
            if not data:
                continue
            with SessionLocal() as s:
                stmt = pg_insert(ExternalForecast).values(
                    city_id=city.id, source="gismeteo", **data
                )
                stmt = stmt.on_conflict_do_nothing(
                    index_elements=["city_id", "target_ts", "source"]
                )
                result = s.execute(stmt)
                s.commit()
                total += result.rowcount or 0
        return total

    _log_run("gismeteo", _do)
