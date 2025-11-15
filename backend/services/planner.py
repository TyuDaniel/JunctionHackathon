"""
Mathematical Charging Planner
Calculates optimal charging plan based on vehicle state, trip requirements, and charger capabilities
Now with Battery Birth Certificate (BBC) awareness for lifecycle-informed charging
"""
from datetime import datetime, timedelta
from typing import Optional, Dict
from backend.schemas.did import VehicleDID, ChargerDID, DriverPreferences
from backend.schemas.session import ChargingPlan, TripDetails, IncentiveOffer


SAFETY_BUFFER = 1.2  # 20% extra energy for safety
EFFICIENCY_FACTOR = 0.85  # 85% charging efficiency (heat loss, etc.)

# Battery lifecycle C-rate limits (for battery health protection)
LIFECYCLE_CRATE_LIMITS = {
    "IN USE": 1.5,  # New batteries can handle faster charging
    "SECOND_LIFE": 0.7,  # Degraded batteries need gentler charging
    "END_OF_LIFE": 0.3,  # Very limited charging
    "UNKNOWN": 1.0  # Conservative default
}


def calculate_charging_plan(
    vehicle: VehicleDID,
    trip: TripDetails,
    charger: ChargerDID,
    driver_preferences: DriverPreferences,
    forecasted_demand: Optional[float] = None,
    site_capacity: Optional[float] = None,
    bbc_claims: Optional[Dict] = None
) -> ChargingPlan:
    """
    Core mathematical planner that calculates the charging plan
    Now with Battery Birth Certificate (BBC) awareness
    
    Args:
        vehicle: Vehicle DID with battery state and capabilities
        trip: Trip details (distance and departure time)
        charger: Charger DID with power and pricing
        driver_preferences: Driver preferences for optimization
        forecasted_demand: Predicted demand at this site (kWh)
        site_capacity: Total site capacity (kW)
        bbc_claims: Battery Birth Certificate claims from Denso DID Gateway
    
    Returns:
        ChargingPlan with all calculations and recommendations
    """
    
    # Extract BBC lifecycle status for battery-aware charging
    lifecycle_status = "UNKNOWN"
    cell_type = "Lithium-Ion"
    if bbc_claims:
        lifecycle_status = bbc_claims.get("lifeCycleStatus", "UNKNOWN")
        cell_type = bbc_claims.get("cellType", "Lithium-Ion")
        manufacturing_date = bbc_claims.get("manufacturingDate", "")
    
    # Step 1: Calculate energy needed for trip
    trip_distance_km = trip.distance_km
    consumption = vehicle.nominal_consumption_wh_per_km
    needed_trip_energy = (trip_distance_km * consumption / 1000) * SAFETY_BUFFER
    
    # Step 2: Calculate current energy in battery
    current_energy = vehicle.battery_capacity_kwh * vehicle.current_soc_percent / 100
    
    # Step 3: Calculate extra energy needed
    extra_energy = max(0, needed_trip_energy - current_energy)
    
    # If battery is already sufficient, minimal charging
    if extra_energy == 0:
        target_soc = vehicle.current_soc_percent
        extra_energy = 0
    else:
        # Calculate target SoC
        target_energy = current_energy + extra_energy
        target_soc = min(100.0, (target_energy / vehicle.battery_capacity_kwh) * 100)
    
    # Step 4: Calculate charging time with BBC-aware power limiting
    # Get C-rate limit based on battery lifecycle status
    crate_limit = LIFECYCLE_CRATE_LIMITS.get(lifecycle_status, 1.0)
    
    # Calculate max safe power for this battery based on lifecycle
    # C-rate = power / capacity, so max_safe_power = crate * capacity
    max_safe_power_kw = crate_limit * vehicle.battery_capacity_kwh
    
    # Effective power is limited by charger, vehicle, lifecycle, AND efficiency
    effective_power = min(
        charger.max_power_kw,
        vehicle.max_charge_power_kw,
        max_safe_power_kw  # BBC-informed limit
    ) * EFFICIENCY_FACTOR
    
    if effective_power > 0 and extra_energy > 0:
        charge_time_hours = extra_energy / effective_power
    else:
        charge_time_hours = 0.0
    
    # Step 5: Calculate finish time
    start_time = datetime.utcnow()
    finish_time = start_time + timedelta(hours=charge_time_hours)
    
    # Step 6: Feasibility check
    is_feasible = finish_time <= trip.departure_time
    feasibility_warning = None
    
    if not is_feasible:
        time_deficit = (finish_time - trip.departure_time).total_seconds() / 3600
        feasibility_warning = (
            f"Charging will take {charge_time_hours:.2f} hours but you only have "
            f"{(trip.departure_time - start_time).total_seconds() / 3600:.2f} hours. "
            f"Short by {time_deficit:.2f} hours. Consider a faster charger or reduce trip distance."
        )
    
    # Step 7: Calculate cost
    base_cost = extra_energy * charger.current_tariff_eur_per_kwh
    
    # Step 8: Determine plan type and incentives based on driver preferences and forecasts
    plan_type = "STANDARD"
    incentive_offers = []
    
    # Check if site is predicted to be overloaded
    is_peak_demand = False
    if forecasted_demand and site_capacity:
        demand_ratio = forecasted_demand / site_capacity
        is_peak_demand = demand_ratio > 0.8  # > 80% capacity
    
    # Generate incentive offers based on conditions
    if is_peak_demand and is_feasible:
        # Offer incentive to delay charging
        hours_until_departure = (trip.departure_time - start_time).total_seconds() / 3600
        
        if hours_until_departure > charge_time_hours + 2:  # Has flexibility to delay
            incentive_offers.append(IncentiveOffer(
                type="discount",
                value=15.0,  # 15% discount
                reason="Delay charging by 2 hours to help balance grid load during peak demand",
                time_slot=start_time + timedelta(hours=2)
            ))
    
    # If driver is carbon conscious, offer green charging option
    if driver_preferences.carbon_conscious:
        # Simulate off-peak green energy (simplified for hackathon)
        current_hour = start_time.hour
        if 10 <= current_hour <= 16:  # Daytime solar available
            plan_type = "GREEN"
            incentive_offers.append(IncentiveOffer(
                type="reward_points",
                value=50.0,
                reason="Charging during solar peak hours (renewable energy available)",
                time_slot=None
            ))
    
    # If driver prefers speed, offer fast charging
    if driver_preferences.priority == "speed" and effective_power < charger.max_power_kw:
        plan_type = "FAST"
    
    # If driver prefers cost, suggest economy mode
    if driver_preferences.priority == "cost" and not is_peak_demand:
        plan_type = "ECONOMY"
        incentive_offers.append(IncentiveOffer(
            type="discount",
            value=10.0,
            reason="Off-peak charging discount available",
            time_slot=None
        ))
    
    # Step 9: Build and return the charging plan
    return ChargingPlan(
        needed_trip_energy_kwh=needed_trip_energy,
        current_energy_kwh=current_energy,
        extra_energy_needed_kwh=extra_energy,
        target_soc_percent=round(target_soc, 2),
        planned_duration_hours=round(charge_time_hours, 3),
        planned_finish_time=finish_time,
        is_feasible=is_feasible,
        feasibility_warning=feasibility_warning,
        planned_cost_eur=round(base_cost, 2),
        effective_charge_power_kw=round(effective_power, 2),
        plan_type=plan_type,
        incentive_offers=incentive_offers
    )


def calculate_actual_cost(
    planned_cost: float,
    energy_delivered_kwh: float,
    planned_energy_kwh: float,
    discount_percent: float = 0.0
) -> float:
    """
    Calculate actual cost based on delivered energy and applied discounts
    """
    if planned_energy_kwh > 0:
        cost_ratio = energy_delivered_kwh / planned_energy_kwh
        actual_cost = planned_cost * cost_ratio
    else:
        actual_cost = 0.0
    
    # Apply discount
    if discount_percent > 0:
        actual_cost = actual_cost * (1 - discount_percent / 100)
    
    return round(actual_cost, 2)

