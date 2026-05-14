from datetime import datetime
from sqlalchemy import String, Float, DateTime, Integer, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class City(Base):
    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)

    observations: Mapped[list["WeatherObservation"]] = relationship(back_populates="city")
    forecasts: Mapped[list["ExternalForecast"]] = relationship(back_populates="city")


class WeatherObservation(Base):
    """Historical/current observations, source=open_meteo or openweather."""
    __tablename__ = "weather_observations"
    __table_args__ = (
        UniqueConstraint("city_id", "ts", "source", name="uq_obs_city_ts_source"),
        Index("ix_obs_city_ts", "city_id", "ts"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)

    temperature_c: Mapped[float | None] = mapped_column(Float)
    humidity: Mapped[float | None] = mapped_column(Float)
    pressure_hpa: Mapped[float | None] = mapped_column(Float)
    wind_speed: Mapped[float | None] = mapped_column(Float)
    wind_direction: Mapped[float | None] = mapped_column(Float)
    cloud_cover: Mapped[float | None] = mapped_column(Float)
    precipitation_mm: Mapped[float | None] = mapped_column(Float)
    weather_code: Mapped[int | None] = mapped_column(Integer)
    weather_main: Mapped[str | None] = mapped_column(String(64))

    city: Mapped[City] = relationship(back_populates="observations")


class ExternalForecast(Base):
    """Forecast from an external provider (e.g. Gismeteo) to compare with our model."""
    __tablename__ = "external_forecasts"
    __table_args__ = (
        UniqueConstraint("city_id", "target_ts", "source", name="uq_fc_city_target_source"),
        Index("ix_fc_city_target", "city_id", "target_ts"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    target_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)

    temperature_c: Mapped[float | None] = mapped_column(Float)
    precipitation_mm: Mapped[float | None] = mapped_column(Float)
    weather_main: Mapped[str | None] = mapped_column(String(64))

    city: Mapped[City] = relationship(back_populates="forecasts")


class IngestRun(Base):
    """Log of each collector invocation for /monitoring page."""
    __tablename__ = "ingest_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running")
    rows_inserted: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(String(500))
