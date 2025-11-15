from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, Text
from backend.database import Base
from datetime import datetime


class ChargingSession(Base):
    __tablename__ = "charging_sessions"

    id = Column(String, primary_key=True, index=True)
    driver_did = Column(String, nullable=False, index=True)
    vehicle_did = Column(String, nullable=False, index=True)
    charger_did = Column(String, nullable=False, index=True)
    site_id = Column(String, nullable=False, index=True)
    
    # Timing
    start_time = Column(DateTime, default=datetime.utcnow, index=True)
    end_time = Column(DateTime, nullable=True)
    departure_time = Column(DateTime, nullable=True)
    planned_finish_time = Column(DateTime, nullable=True)
    
    # Energy and battery
    battery_capacity_kwh = Column(Float, nullable=False)
    initial_soc_percent = Column(Float, nullable=False)
    target_soc_percent = Column(Float, nullable=False)
    final_soc_percent = Column(Float, nullable=True)
    energy_delivered_kwh = Column(Float, nullable=True)
    planned_energy_kwh = Column(Float, nullable=False)
    
    # Trip details
    trip_distance_km = Column(Float, nullable=False)
    consumption_wh_per_km = Column(Float, nullable=False)
    
    # Charging details
    max_charge_power_kw = Column(Float, nullable=False)
    effective_charge_power_kw = Column(Float, nullable=False)
    planned_duration_hours = Column(Float, nullable=False)
    
    # Cost and pricing
    tariff_eur_per_kwh = Column(Float, nullable=False)
    planned_cost_eur = Column(Float, nullable=False)
    final_cost_eur = Column(Float, nullable=True)
    discount_applied_percent = Column(Float, default=0.0)
    
    # Status and feasibility
    status = Column(String, default="active")  # active, completed, cancelled
    is_feasible = Column(Boolean, default=True)
    feasibility_warning = Column(Text, nullable=True)
    
    # Plan metadata
    plan_version = Column(String, default="v1.0")
    plan_type = Column(String, default="STANDARD")  # STANDARD, FAST, ECONOMY, GREEN
    incentive_offered = Column(Text, nullable=True)
    
    # Driver preferences
    driver_priority = Column(String, default="cost")  # cost, speed, carbon
    carbon_conscious = Column(Boolean, default=False)

