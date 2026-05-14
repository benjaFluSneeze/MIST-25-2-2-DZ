import logging
from fastapi import FastAPI
from sqlalchemy import text

from . import ml_service
from .db import engine
from .routers import data as data_router
from .routers import predict as predict_router
from .schemas import HealthResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s | %(message)s")

app = FastAPI(
    title="WeatherML API",
    description="Weather data and ML forecasts. See /docs for Swagger UI.",
    version="0.1.0",
)

app.include_router(data_router.router)
app.include_router(predict_router.router)


@app.get("/health", response_model=HealthResponse, tags=["meta"])
def health():
    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:  # noqa: BLE001
        db_status = f"error: {e.__class__.__name__}"
    return HealthResponse(
        status="ok",
        db=db_status,
        models_loaded=ml_service.get_bundle().status,
    )


@app.get("/", tags=["meta"])
def root():
    return {"service": "weatherml-api", "docs": "/docs"}


@app.post("/admin/reload-models", tags=["meta"])
def reload_models():
    ml_service.reload_bundle()
    return {"reloaded": True, "loaded": ml_service.get_bundle().status}
