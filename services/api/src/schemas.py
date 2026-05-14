from datetime import datetime
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    db: str
    models_loaded: dict[str, bool]


class CityOut(BaseModel):
    id: int
    name: str
    lat: float
    lon: float
    timezone: str

    model_config = {"from_attributes": True}


class ObservationOut(BaseModel):
    ts: datetime
    city_id: int
    source: str
    temperature_c: float | None
    humidity: float | None
    pressure_hpa: float | None
    wind_speed: float | None
    wind_direction: float | None
    cloud_cover: float | None
    precipitation_mm: float | None
    weather_main: str | None

    model_config = {"from_attributes": True}


class ExternalForecastOut(BaseModel):
    fetched_at: datetime
    target_ts: datetime
    source: str
    temperature_c: float | None
    precipitation_mm: float | None
    weather_main: str | None

    model_config = {"from_attributes": True}


class IngestRunOut(BaseModel):
    source: str
    started_at: datetime
    finished_at: datetime | None
    status: str
    rows_inserted: int
    error: str | None

    model_config = {"from_attributes": True}


class PredictRequest(BaseModel):
    city_id: int = Field(..., description="City id to predict for")
    horizon_hours: int = Field(6, ge=1, le=24, description="Forecast horizon in hours")


class ManualPredictRequest(BaseModel):
    city_id: int = Field(..., description="City id (used for lag history)")
    horizon_hours: int = Field(6, ge=1, le=24)
    temperature_c: float | None = Field(None, ge=-80, le=60, description="Current temperature, °C")
    humidity: float | None = Field(None, ge=0, le=100, description="Relative humidity, %")
    pressure_hpa: float | None = Field(None, ge=800, le=1100, description="Pressure, hPa")
    wind_speed: float | None = Field(None, ge=0, le=80, description="Wind speed, m/s")
    wind_direction: float | None = Field(None, ge=0, le=360, description="Wind direction, degrees")
    cloud_cover: float | None = Field(None, ge=0, le=100, description="Cloud cover, %")
    precipitation_mm: float | None = Field(None, ge=0, le=200, description="Precipitation, mm")


class PredictResponse(BaseModel):
    city_id: int
    city_name: str
    based_on_ts: datetime
    horizon_hours: int
    target_ts: datetime
    predicted_temperature_c: float | None
    predicted_rain_probability: float | None
    predicted_rain: bool | None
    predicted_condition: str | None
