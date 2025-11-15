"""
Demo API Router
Handles demo data generation and test utilities
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.utils.demo_data import DemoDataGenerator


router = APIRouter(prefix="/api/v1/demo", tags=["demo"])


@router.post("/generate-data")
def generate_demo_data(
    days: int = 30,
    db: Session = Depends(get_db)
):
    """
    Generate synthetic demo data for training and testing
    
    Args:
        days: Number of days of historical data to generate (default: 30)
    
    Returns:
        Statistics about generated data
    """
    generator = DemoDataGenerator(db)
    stats = generator.generate_all(days=days)
    
    # Get sample DIDs for testing
    samples = generator.get_sample_dids()
    stats["sample_dids"] = samples
    
    return {
        "status": "success",
        "message": f"Generated {days} days of demo data",
        "statistics": stats
    }


@router.get("/sample-dids")
def get_sample_dids(db: Session = Depends(get_db)):
    """
    Get sample DIDs for manual testing
    
    This is useful for constructing test requests
    """
    generator = DemoDataGenerator(db)
    
    # Need to populate lists from database
    from backend.models import Charger
    chargers = db.query(Charger).limit(5).all()
    
    return {
        "driver_dids": [f"did:denso:driver:driver{i:03d}" for i in range(1, 6)],
        "vehicle_dids": [f"did:denso:vehicle:vehicle{i:03d}" for i in range(1, 6)],
        "charger_dids": [c.did for c in chargers],
        "example_vehicle_configs": [
            {"battery_capacity_kwh": 50, "consumption_wh_per_km": 150, "max_charge_power_kw": 100},
            {"battery_capacity_kwh": 75, "consumption_wh_per_km": 180, "max_charge_power_kw": 150},
            {"battery_capacity_kwh": 100, "consumption_wh_per_km": 220, "max_charge_power_kw": 250},
        ]
    }

