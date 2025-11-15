"""
Sessions API Router
Handles charging session creation, retrieval, and completion
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import uuid

from backend.database import get_db
from backend.schemas.session import (
    StartSessionRequest,
    StartSessionResponse,
    SessionResponse,
    CompleteSessionRequest,
    CompleteSessionResponse,
    ChargingPlan
)
from backend.services.planner import calculate_charging_plan, calculate_actual_cost
from backend.services.did_validator import validate_did_access
from backend.services.forecasting import DemandForecaster
from backend.models import ChargingSession, Charger, Site


router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


@router.post("/start", response_model=StartSessionResponse)
def start_session(
    request: StartSessionRequest,
    db: Session = Depends(get_db)
):
    """
    Start a new charging session
    
    This endpoint:
    1. Validates DID-based access control
    2. Calculates the optimal charging plan using mathematical planner
    3. Checks demand forecasts to offer incentives
    4. Creates and returns the charging session
    """
    
    # Step 1: Validate DID access
    is_valid, message = validate_did_access(
        request.driver,
        request.vehicle,
        request.charger
    )
    
    if not is_valid:
        raise HTTPException(status_code=403, detail=message)
    
    # Step 2: Get site information for forecasting
    charger = db.query(Charger).filter(Charger.did == request.charger.did).first()
    if not charger:
        raise HTTPException(status_code=404, detail="Charger not found in database")
    
    site = db.query(Site).filter(Site.id == charger.site_id).first()
    
    # Step 3: Get demand forecast (if model is trained)
    forecasted_demand = None
    site_capacity = site.total_capacity_kw if site else None
    
    try:
        forecaster = DemandForecaster()
        if forecaster.load_model():
            # Get forecast for the current hour
            forecasts = forecaster.predict(
                site_id=charger.site_id,
                target_time=datetime.utcnow(),
                db=db,
                hours_ahead=3
            )
            if forecasts:
                forecasted_demand = forecasts[0]['predicted_total_kwh']
    except Exception as e:
        # If forecasting fails, continue without it
        print(f"Forecasting error: {e}")
    
    # Step 4: Calculate charging plan
    plan = calculate_charging_plan(
        vehicle=request.vehicle,
        trip=request.trip,
        charger=request.charger,
        driver_preferences=request.driver.preferences,
        forecasted_demand=forecasted_demand,
        site_capacity=site_capacity
    )
    
    # Step 5: Create session record
    session_id = str(uuid.uuid4())
    
    # Extract discount if offered
    discount_percent = 0.0
    incentive_text = None
    if plan.incentive_offers:
        for offer in plan.incentive_offers:
            if offer.type == "discount":
                discount_percent = offer.value
                incentive_text = offer.reason
                break
        if not incentive_text:
            incentive_text = "; ".join([f"{o.type}: {o.reason}" for o in plan.incentive_offers])
    
    session = ChargingSession(
        id=session_id,
        driver_did=request.driver.did,
        vehicle_did=request.vehicle.did,
        charger_did=request.charger.did,
        site_id=charger.site_id,
        start_time=datetime.utcnow(),
        departure_time=request.trip.departure_time,
        planned_finish_time=plan.planned_finish_time,
        battery_capacity_kwh=request.vehicle.battery_capacity_kwh,
        initial_soc_percent=request.vehicle.current_soc_percent,
        target_soc_percent=plan.target_soc_percent,
        planned_energy_kwh=plan.extra_energy_needed_kwh,
        trip_distance_km=request.trip.distance_km,
        consumption_wh_per_km=request.vehicle.nominal_consumption_wh_per_km,
        max_charge_power_kw=request.vehicle.max_charge_power_kw,
        effective_charge_power_kw=plan.effective_charge_power_kw,
        planned_duration_hours=plan.planned_duration_hours,
        tariff_eur_per_kwh=request.charger.current_tariff_eur_per_kwh,
        planned_cost_eur=plan.planned_cost_eur,
        discount_applied_percent=discount_percent,
        status="active",
        is_feasible=plan.is_feasible,
        feasibility_warning=plan.feasibility_warning,
        plan_version="v1.0",
        plan_type=plan.plan_type,
        incentive_offered=incentive_text,
        driver_priority=request.driver.preferences.priority,
        carbon_conscious=request.driver.preferences.carbon_conscious
    )
    
    db.add(session)
    db.commit()
    db.refresh(session)
    
    return StartSessionResponse(
        session_id=session_id,
        plan=plan,
        message=f"Session started successfully. {message}"
    )


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Get details of a charging session
    """
    session = db.query(ChargingSession).filter(ChargingSession.id == session_id).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Reconstruct the plan from session data
    plan = ChargingPlan(
        needed_trip_energy_kwh=(session.trip_distance_km * session.consumption_wh_per_km / 1000) * 1.2,
        current_energy_kwh=session.battery_capacity_kwh * session.initial_soc_percent / 100,
        extra_energy_needed_kwh=session.planned_energy_kwh,
        target_soc_percent=session.target_soc_percent,
        planned_duration_hours=session.planned_duration_hours,
        planned_finish_time=session.planned_finish_time,
        is_feasible=session.is_feasible,
        feasibility_warning=session.feasibility_warning,
        planned_cost_eur=session.planned_cost_eur,
        effective_charge_power_kw=session.effective_charge_power_kw,
        plan_type=session.plan_type,
        incentive_offers=[]  # Could reconstruct from incentive_offered text if needed
    )
    
    return SessionResponse(
        session_id=session.id,
        driver_did=session.driver_did,
        vehicle_did=session.vehicle_did,
        charger_did=session.charger_did,
        site_id=session.site_id,
        status=session.status,
        start_time=session.start_time,
        end_time=session.end_time,
        plan=plan,
        energy_delivered_kwh=session.energy_delivered_kwh,
        final_cost_eur=session.final_cost_eur
    )


@router.post("/{session_id}/complete", response_model=CompleteSessionResponse)
def complete_session(
    session_id: str,
    request: CompleteSessionRequest,
    db: Session = Depends(get_db)
):
    """
    Complete a charging session
    
    Records the actual energy delivered and calculates final cost
    """
    session = db.query(ChargingSession).filter(ChargingSession.id == session_id).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.status == "completed":
        raise HTTPException(status_code=400, detail="Session already completed")
    
    # Update session with actual values
    session.end_time = datetime.utcnow()
    session.energy_delivered_kwh = request.energy_delivered_kwh
    session.final_soc_percent = request.final_soc_percent
    session.status = "completed"
    
    # Calculate actual cost
    actual_cost = calculate_actual_cost(
        planned_cost=session.planned_cost_eur,
        energy_delivered_kwh=request.energy_delivered_kwh,
        planned_energy_kwh=session.planned_energy_kwh,
        discount_percent=session.discount_applied_percent
    )
    
    session.final_cost_eur = actual_cost
    
    # Calculate actual duration
    duration_hours = (session.end_time - session.start_time).total_seconds() / 3600
    
    db.commit()
    
    return CompleteSessionResponse(
        session_id=session_id,
        final_cost_eur=actual_cost,
        energy_delivered_kwh=request.energy_delivered_kwh,
        duration_hours=round(duration_hours, 3),
        message="Session completed successfully"
    )

