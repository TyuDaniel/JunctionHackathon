"""
Forecasts API Router
Handles demand forecasting and model training
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from backend.database import get_db
from backend.schemas.forecast import ForecastResponse, HourlyForecast
from backend.services.forecasting import DemandForecaster


router = APIRouter(prefix="/api/v1/forecasts", tags=["forecasts"])


@router.post("/train")
def train_forecast_model(db: Session = Depends(get_db)):
    """
    Train the demand forecasting model on historical data
    
    This should be called after generating demo data or when sufficient
    real session data is available
    """
    forecaster = DemandForecaster()
    
    try:
        metrics = forecaster.train(db)
        return {
            "status": "success",
            "message": "Model trained successfully",
            "metrics": metrics
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")


@router.get("/site/{site_id}", response_model=ForecastResponse)
def get_site_forecast(
    site_id: str,
    hours_ahead: int = 24,
    db: Session = Depends(get_db)
):
    """
    Get demand forecast for a specific site
    
    Args:
        site_id: Site identifier
        hours_ahead: Number of hours to forecast (default: 24)
    
    Returns:
        Hourly forecasts with confidence intervals
    """
    forecaster = DemandForecaster()
    
    if not forecaster.load_model():
        raise HTTPException(
            status_code=503,
            detail="Forecasting model not available. Please train the model first."
        )
    
    try:
        predictions = forecaster.predict(
            site_id=site_id,
            target_time=datetime.utcnow(),
            db=db,
            hours_ahead=min(hours_ahead, 48)  # Cap at 48 hours
        )
        
        # Save forecasts to database
        forecaster.save_forecasts_to_db(predictions, site_id, db)
        
        # Convert to response format
        hourly_forecasts = [
            HourlyForecast(
                time_slot=pred['time_slot'],
                predicted_total_kwh=pred['predicted_total_kwh'],
                predicted_active_sessions=pred['predicted_active_sessions'],
                confidence_lower=pred['confidence_lower'],
                confidence_upper=pred['confidence_upper']
            )
            for pred in predictions
        ]
        
        return ForecastResponse(
            site_id=site_id,
            forecasts=hourly_forecasts,
            model_version="v1.0"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Forecasting failed: {str(e)}")

