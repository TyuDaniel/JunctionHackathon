from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from .did import DriverDID, VehicleDID, ChargerDID


class TripDetails(BaseModel):
    distance_km: float = Field(..., gt=0, description="Trip distance in kilometers")
    departure_time: datetime = Field(..., description="Planned departure time")


class IncentiveOffer(BaseModel):
    type: str = Field(..., description="Type of incentive: discount, reward_points, priority_slot")
    value: float = Field(..., description="Incentive value (percent for discount, points for rewards)")
    reason: str = Field(..., description="Why this incentive is offered")
    time_slot: Optional[datetime] = Field(None, description="Recommended charging time slot")


class ChargingPlan(BaseModel):
    """
    The calculated charging plan from the mathematical planner
    """
    # Energy calculations
    needed_trip_energy_kwh: float = Field(..., description="Energy needed for the trip (with buffer)")
    current_energy_kwh: float = Field(..., description="Current energy in battery")
    extra_energy_needed_kwh: float = Field(..., description="Additional energy needed")
    
    # Target and timing
    target_soc_percent: float = Field(..., description="Target state of charge")
    planned_duration_hours: float = Field(..., description="Estimated charging duration in hours")
    planned_finish_time: datetime = Field(..., description="Expected charging completion time")
    
    # Feasibility
    is_feasible: bool = Field(..., description="Can charging complete before departure")
    feasibility_warning: Optional[str] = Field(None, description="Warning if not feasible")
    
    # Cost
    planned_cost_eur: float = Field(..., description="Estimated cost in EUR")
    effective_charge_power_kw: float = Field(..., description="Effective charging power")
    
    # Plan type
    plan_type: str = Field(default="STANDARD", description="STANDARD, FAST, ECONOMY, GREEN")
    incentive_offers: list[IncentiveOffer] = Field(
        default_factory=list,
        description="Available incentives"
    )


class StartSessionRequest(BaseModel):
    """
    Request to start a new charging session
    Contains all three DID payloads and trip details
    """
    driver: DriverDID
    vehicle: VehicleDID
    charger: ChargerDID
    trip: TripDetails


class StartSessionResponse(BaseModel):
    """
    Response when starting a session
    Contains session ID and the calculated charging plan
    """
    session_id: str
    plan: ChargingPlan
    message: str = Field(default="Session started successfully")


class SessionResponse(BaseModel):
    """
    Response for getting session details
    """
    session_id: str
    driver_did: str
    vehicle_did: str
    charger_did: str
    site_id: str
    status: str
    start_time: datetime
    end_time: Optional[datetime]
    plan: ChargingPlan
    energy_delivered_kwh: Optional[float]
    final_cost_eur: Optional[float]


class CompleteSessionRequest(BaseModel):
    """
    Request to complete a charging session
    """
    energy_delivered_kwh: float = Field(..., gt=0, description="Actual energy delivered")
    final_soc_percent: Optional[float] = Field(None, ge=0, le=100, description="Final SoC")


class CompleteSessionResponse(BaseModel):
    """
    Response when completing a session
    """
    session_id: str
    final_cost_eur: float
    energy_delivered_kwh: float
    duration_hours: float
    message: str = Field(default="Session completed successfully")

