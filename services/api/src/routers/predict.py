from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import ml_service
from ..db import get_session
from ..models import City
from ..schemas import PredictRequest, PredictResponse

router = APIRouter(prefix="/predict", tags=["predict"])


@router.post("", response_model=PredictResponse)
def predict(req: PredictRequest, session: Session = Depends(get_session)):
    city = session.get(City, req.city_id)
    if city is None:
        raise HTTPException(status_code=404, detail="city not found")
    try:
        result = ml_service.predict_for_city(session, req.city_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    target_ts = result["based_on_ts"] + timedelta(hours=req.horizon_hours)
    return PredictResponse(
        city_id=city.id,
        city_name=city.name,
        based_on_ts=result["based_on_ts"],
        horizon_hours=req.horizon_hours,
        target_ts=target_ts,
        predicted_temperature_c=result["predicted_temperature_c"],
        predicted_rain_probability=result["predicted_rain_probability"],
        predicted_rain=result["predicted_rain"],
        predicted_condition=result["predicted_condition"],
    )


@router.get("/metrics")
def model_metrics():
    bundle = ml_service.get_bundle()
    return bundle.metrics


@router.get("/feature-importance/{model_name}")
def feature_importance(model_name: str):
    bundle = ml_service.get_bundle()
    mapping = {"temperature": bundle.temp, "rain": bundle.rain, "condition": bundle.condition}
    b = mapping.get(model_name)
    if b is None:
        raise HTTPException(status_code=404, detail="model not loaded")
    model = b["model"]
    features = b["features"]
    importances = model.get_feature_importance()
    pairs = sorted(
        zip(features, [float(x) for x in importances]),
        key=lambda x: x[1],
        reverse=True,
    )
    return [{"feature": f, "importance": i} for f, i in pairs]
