"""
Chargers API Router
Handles charger queries and site analytics
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional

from backend.database import get_db
from backend.models import Charger, Site, ChargingSession
from backend.schemas.forecast import SiteAnalyticsResponse


router = APIRouter(prefix="/api/v1", tags=["chargers", "sites"])


@router.get("/chargers")
def list_chargers(
    site_id: Optional[str] = None,
    available_only: bool = False,
    db: Session = Depends(get_db)
):
    """
    List all chargers, optionally filtered by site or availability
    """
    query = db.query(Charger)
    
    if site_id:
        query = query.filter(Charger.site_id == site_id)
    
    if available_only:
        query = query.filter(Charger.current_availability == True)
    
    chargers = query.all()
    
    return {
        "count": len(chargers),
        "chargers": [
            {
                "did": c.did,
                "site_id": c.site_id,
                "max_power_kw": c.max_power_kw,
                "available": c.current_availability,
                "tariff_eur_per_kwh": c.current_tariff_eur_per_kwh,
                "location": {
                    "lat": c.location_lat,
                    "lon": c.location_lon
                },
                "type": c.charger_type
            }
            for c in chargers
        ]
    }


@router.get("/sites")
def list_sites(db: Session = Depends(get_db)):
    """
    List all charging sites
    """
    sites = db.query(Site).all()
    
    return {
        "count": len(sites),
        "sites": [
            {
                "id": s.id,
                "name": s.name,
                "type": s.site_type,
                "location": {
                    "lat": s.location_lat,
                    "lon": s.location_lon
                },
                "total_capacity_kw": s.total_capacity_kw,
                "charger_count": s.charger_count
            }
            for s in sites
        ]
    }


@router.get("/sites/{site_id}/analytics", response_model=SiteAnalyticsResponse)
def get_site_analytics(
    site_id: str,
    db: Session = Depends(get_db)
):
    """
    Get aggregated analytics for a site
    
    Includes:
    - Total sessions and energy
    - Revenue metrics
    - Peak demand analysis
    - Cost savings from incentive acceptance
    """
    # Check site exists
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    
    # Get all completed sessions for this site
    sessions = db.query(ChargingSession).filter(
        ChargingSession.site_id == site_id,
        ChargingSession.status == "completed"
    ).all()
    
    if not sessions:
        return SiteAnalyticsResponse(
            site_id=site_id,
            total_sessions=0,
            total_energy_kwh=0.0,
            total_revenue_eur=0.0,
            avg_session_duration_hours=0.0,
            peak_hour=0,
            peak_demand_kwh=0.0,
            cost_savings_eur=0.0,
            incentive_acceptance_rate=0.0
        )
    
    # Calculate metrics
    total_sessions = len(sessions)
    total_energy = sum(s.energy_delivered_kwh or 0 for s in sessions)
    total_revenue = sum(s.final_cost_eur or 0 for s in sessions)
    
    # Average duration
    durations = []
    for s in sessions:
        if s.end_time and s.start_time:
            duration = (s.end_time - s.start_time).total_seconds() / 3600
            durations.append(duration)
    avg_duration = sum(durations) / len(durations) if durations else 0
    
    # Peak hour analysis
    hour_energy = {}
    for s in sessions:
        hour = s.start_time.hour
        energy = s.energy_delivered_kwh or 0
        hour_energy[hour] = hour_energy.get(hour, 0) + energy
    
    if hour_energy:
        peak_hour = max(hour_energy, key=hour_energy.get)
        peak_demand = hour_energy[peak_hour]
    else:
        peak_hour = 0
        peak_demand = 0.0
    
    # Incentive analysis
    sessions_with_incentive = [s for s in sessions if s.incentive_offered]
    sessions_accepted_incentive = [s for s in sessions if s.discount_applied_percent > 0]
    
    incentive_acceptance_rate = (
        len(sessions_accepted_incentive) / len(sessions_with_incentive)
        if sessions_with_incentive else 0.0
    )
    
    # Cost savings (from discounts applied)
    cost_savings = sum(
        (s.planned_cost_eur - (s.final_cost_eur or s.planned_cost_eur))
        for s in sessions
    )
    
    return SiteAnalyticsResponse(
        site_id=site_id,
        total_sessions=total_sessions,
        total_energy_kwh=round(total_energy, 2),
        total_revenue_eur=round(total_revenue, 2),
        avg_session_duration_hours=round(avg_duration, 2),
        peak_hour=peak_hour,
        peak_demand_kwh=round(peak_demand, 2),
        cost_savings_eur=round(cost_savings, 2),
        incentive_acceptance_rate=round(incentive_acceptance_rate, 2)
    )

