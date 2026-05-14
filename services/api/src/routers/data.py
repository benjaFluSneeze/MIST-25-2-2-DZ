from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from ..db import get_session
from ..models import City, ExternalForecast, IngestRun, WeatherObservation
from ..schemas import CityOut, ExternalForecastOut, IngestRunOut, ObservationOut

router = APIRouter(prefix="/data", tags=["data"])


@router.get("/cities", response_model=list[CityOut])
def list_cities(session: Session = Depends(get_session)):
    return session.execute(select(City).order_by(City.name)).scalars().all()


@router.get("/observations", response_model=list[ObservationOut])
def list_observations(
    city_id: int = Query(..., description="City id"),
    hours: int = Query(168, ge=1, le=24 * 365, description="Lookback window in hours"),
    source: str | None = Query(None, description="Filter by source"),
    session: Session = Depends(get_session),
):
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    stmt = (
        select(WeatherObservation)
        .where(WeatherObservation.city_id == city_id)
        .where(WeatherObservation.ts >= since)
        .order_by(WeatherObservation.ts)
    )
    if source:
        stmt = stmt.where(WeatherObservation.source == source)
    rows = session.execute(stmt).scalars().all()
    if not rows:
        raise HTTPException(status_code=404, detail="no observations for given filters")
    return rows


@router.get("/forecasts", response_model=list[ExternalForecastOut])
def list_external_forecasts(
    city_id: int = Query(..., description="City id"),
    limit: int = Query(30, ge=1, le=200),
    session: Session = Depends(get_session),
):
    rows = session.execute(
        select(ExternalForecast)
        .where(ExternalForecast.city_id == city_id)
        .order_by(desc(ExternalForecast.target_ts))
        .limit(limit)
    ).scalars().all()
    return rows


@router.get("/ingest-runs", response_model=list[IngestRunOut])
def list_ingest_runs(
    limit: int = Query(30, ge=1, le=200),
    session: Session = Depends(get_session),
):
    rows = session.execute(
        select(IngestRun).order_by(desc(IngestRun.started_at)).limit(limit)
    ).scalars().all()
    return rows
