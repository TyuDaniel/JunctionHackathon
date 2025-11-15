"""
Demo Data Generator
Creates realistic synthetic data for training and demonstration
"""
import random
import uuid
from datetime import datetime, timedelta
from typing import List, Tuple
from sqlalchemy.orm import Session

from backend.models import Site, Charger, ChargingSession


class DemoDataGenerator:
    """
    Generate synthetic but realistic demo data for TASCO
    """
    
    # Site configurations
    SITES = [
        {"id": "site_hq", "name": "Corporate HQ", "type": "workplace", "lat": 60.1699, "lon": 24.9384, "chargers": 8, "capacity": 600},
        {"id": "site_depot", "name": "Fleet Depot", "type": "fleet_depot", "lat": 60.2055, "lon": 24.6522, "chargers": 10, "capacity": 800},
        {"id": "site_mall", "name": "Shopping Mall", "type": "retail", "lat": 60.1841, "lon": 24.8301, "chargers": 5, "capacity": 400},
        {"id": "site_office", "name": "Tech Office Park", "type": "workplace", "lat": 60.2208, "lon": 24.7580, "chargers": 6, "capacity": 450},
        {"id": "site_retail", "name": "Retail Center", "type": "retail", "lat": 60.1621, "lon": 24.9207, "chargers": 4, "capacity": 300},
    ]
    
    # Vehicle types (battery capacity, consumption, max power)
    VEHICLE_TYPES = [
        (50, 150, 100),   # Small EV: 50 kWh, 150 Wh/km, 100 kW
        (64, 170, 125),   # Compact EV: 64 kWh, 170 Wh/km, 125 kW
        (75, 180, 150),   # Mid-size EV: 75 kWh, 180 Wh/km, 150 kW
        (82, 200, 150),   # Large EV: 82 kWh, 200 Wh/km, 150 kW
        (100, 220, 250),  # Premium EV: 100 kWh, 220 Wh/km, 250 kW
    ]
    
    # Charging patterns by hour (probability multiplier)
    HOURLY_DEMAND = {
        0: 0.1, 1: 0.05, 2: 0.05, 3: 0.05, 4: 0.05, 5: 0.1,
        6: 0.3, 7: 0.8, 8: 1.2, 9: 0.9, 10: 0.6, 11: 0.5,
        12: 0.7, 13: 0.6, 14: 0.5, 15: 0.6, 16: 0.8, 17: 1.5,
        18: 1.3, 19: 0.9, 20: 0.6, 21: 0.4, 22: 0.3, 23: 0.2
    }
    
    def __init__(self, db: Session):
        self.db = db
        self.driver_dids: List[str] = []
        self.vehicle_dids: List[str] = []
        self.charger_dids: List[str] = []
        
    def generate_all(self, days: int = 30) -> dict:
        """
        Generate complete demo dataset
        
        Args:
            days: Number of days of historical data to generate
        
        Returns:
            Dictionary with generation statistics
        """
        
        # Clear existing data (optional, for clean slate)
        # self._clear_existing_data()
        
        # Step 1: Create sites
        sites_created = self._create_sites()
        
        # Step 2: Create chargers
        chargers_created = self._create_chargers()
        
        # Step 3: Create DIDs
        self._create_dids()
        
        # Step 4: Create charging sessions
        sessions_created = self._create_sessions(days)
        
        return {
            "sites_created": sites_created,
            "chargers_created": chargers_created,
            "driver_dids": len(self.driver_dids),
            "vehicle_dids": len(self.vehicle_dids),
            "sessions_created": sessions_created,
            "days_of_data": days
        }
    
    def _create_sites(self) -> int:
        """Create site records"""
        count = 0
        for site_config in self.SITES:
            site = Site(
                id=site_config["id"],
                name=site_config["name"],
                location_lat=site_config["lat"],
                location_lon=site_config["lon"],
                total_capacity_kw=site_config["capacity"],
                site_type=site_config["type"],
                charger_count=site_config["chargers"]
            )
            self.db.merge(site)
            count += 1
        
        self.db.commit()
        return count
    
    def _create_chargers(self) -> int:
        """Create charger records for each site"""
        count = 0
        
        for site_config in self.SITES:
            site_id = site_config["id"]
            num_chargers = site_config["chargers"]
            
            # Distribute charger powers
            power_options = [50, 100, 150, 150, 250]  # Mix of charger types
            tariff_options = [0.30, 0.35, 0.40, 0.45]  # Different pricing tiers
            
            for i in range(num_chargers):
                charger_did = f"did:denso:charger:{site_id}_chr{i+1:02d}"
                self.charger_dids.append(charger_did)
                
                # Add small random offset to location
                lat_offset = random.uniform(-0.001, 0.001)
                lon_offset = random.uniform(-0.001, 0.001)
                
                charger = Charger(
                    did=charger_did,
                    site_id=site_id,
                    max_power_kw=random.choice(power_options),
                    current_availability=True,
                    current_tariff_eur_per_kwh=random.choice(tariff_options),
                    location_lat=site_config["lat"] + lat_offset,
                    location_lon=site_config["lon"] + lon_offset,
                    charger_type="DC"
                )
                self.db.merge(charger)
                count += 1
        
        self.db.commit()
        return count
    
    def _create_dids(self):
        """Generate DID identifiers"""
        # Create 20 driver DIDs
        for i in range(20):
            self.driver_dids.append(f"did:denso:driver:driver{i+1:03d}")
        
        # Create 30 vehicle DIDs
        for i in range(30):
            self.vehicle_dids.append(f"did:denso:vehicle:vehicle{i+1:03d}")
    
    def _create_sessions(self, days: int) -> int:
        """
        Create realistic charging sessions over the specified number of days
        """
        count = 0
        base_date = datetime.utcnow() - timedelta(days=days)
        
        for day in range(days):
            current_date = base_date + timedelta(days=day)
            is_weekend = current_date.weekday() >= 5
            
            # Adjust session count based on day type
            base_sessions_per_day = 40 if not is_weekend else 20
            sessions_today = random.randint(
                int(base_sessions_per_day * 0.8),
                int(base_sessions_per_day * 1.2)
            )
            
            for _ in range(sessions_today):
                # Random hour weighted by demand pattern
                hour = random.choices(
                    list(self.HOURLY_DEMAND.keys()),
                    weights=list(self.HOURLY_DEMAND.values())
                )[0]
                
                # Random minute
                minute = random.randint(0, 59)
                start_time = current_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                # Select random entities
                driver_did = random.choice(self.driver_dids)
                vehicle_did = random.choice(self.vehicle_dids)
                charger_did = random.choice(self.charger_dids)
                
                # Get charger to determine site
                charger = self.db.query(Charger).filter(Charger.did == charger_did).first()
                if not charger:
                    continue
                
                # Select vehicle type
                battery_capacity, consumption, max_vehicle_power = random.choice(self.VEHICLE_TYPES)
                
                # Random initial SoC (typically arrive with 20-60%)
                initial_soc = random.uniform(20, 60)
                
                # Random trip distance (5-200 km, weighted towards shorter trips)
                trip_distance = random.choices(
                    [10, 30, 50, 80, 120, 200],
                    weights=[30, 25, 20, 15, 7, 3]
                )[0] + random.uniform(-5, 5)
                trip_distance = max(5, trip_distance)
                
                # Calculate energy needed
                needed_energy = (trip_distance * consumption / 1000) * 1.2  # With buffer
                current_energy = battery_capacity * initial_soc / 100
                extra_energy = max(0, needed_energy - current_energy)
                
                # Calculate charging
                effective_power = min(charger.max_power_kw, max_vehicle_power) * 0.85
                charge_time_hours = extra_energy / effective_power if effective_power > 0 else 0
                
                # Target SoC
                target_energy = current_energy + extra_energy
                target_soc = min(100, (target_energy / battery_capacity) * 100)
                
                # Actual delivered (add some variance)
                energy_delivered = extra_energy * random.uniform(0.95, 1.05)
                final_soc = min(100, (current_energy + energy_delivered) / battery_capacity * 100)
                
                # End time
                actual_duration = charge_time_hours * random.uniform(0.95, 1.1)
                end_time = start_time + timedelta(hours=actual_duration)
                
                # Cost
                cost = energy_delivered * charger.current_tariff_eur_per_kwh
                
                # Departure time (typically 1-4 hours after start)
                departure_offset_hours = random.uniform(1, 4)
                departure_time = start_time + timedelta(hours=departure_offset_hours)
                planned_finish = start_time + timedelta(hours=charge_time_hours)
                
                # Driver preferences
                priorities = ["cost", "speed", "carbon"]
                driver_priority = random.choice(priorities)
                carbon_conscious = random.choice([True, False])
                
                # Determine plan type
                plan_types = ["STANDARD", "FAST", "ECONOMY", "GREEN"]
                plan_type = random.choices(plan_types, weights=[50, 20, 20, 10])[0]
                
                # Create session
                session = ChargingSession(
                    id=str(uuid.uuid4()),
                    driver_did=driver_did,
                    vehicle_did=vehicle_did,
                    charger_did=charger_did,
                    site_id=charger.site_id,
                    start_time=start_time,
                    end_time=end_time,
                    departure_time=departure_time,
                    planned_finish_time=planned_finish,
                    battery_capacity_kwh=battery_capacity,
                    initial_soc_percent=initial_soc,
                    target_soc_percent=target_soc,
                    final_soc_percent=final_soc,
                    energy_delivered_kwh=energy_delivered,
                    planned_energy_kwh=extra_energy,
                    trip_distance_km=trip_distance,
                    consumption_wh_per_km=consumption,
                    max_charge_power_kw=max_vehicle_power,
                    effective_charge_power_kw=effective_power,
                    planned_duration_hours=charge_time_hours,
                    tariff_eur_per_kwh=charger.current_tariff_eur_per_kwh,
                    planned_cost_eur=cost * 0.98,  # Planned slightly different
                    final_cost_eur=cost,
                    discount_applied_percent=random.choice([0, 0, 0, 10, 15]),
                    status="completed",
                    is_feasible=True,
                    plan_version="v1.0",
                    plan_type=plan_type,
                    driver_priority=driver_priority,
                    carbon_conscious=carbon_conscious
                )
                
                self.db.add(session)
                count += 1
                
                # Commit in batches
                if count % 100 == 0:
                    self.db.commit()
        
        # Final commit
        self.db.commit()
        return count
    
    def get_sample_dids(self) -> dict:
        """
        Get sample DIDs for testing
        """
        return {
            "driver_dids": self.driver_dids[:5] if self.driver_dids else [],
            "vehicle_dids": self.vehicle_dids[:5] if self.vehicle_dids else [],
            "charger_dids": self.charger_dids[:5] if self.charger_dids else []
        }

