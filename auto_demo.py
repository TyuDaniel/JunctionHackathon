import sys
import os
from datetime import datetime, timedelta

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from database import init_db, SessionLocal
from utils.demo_data import DemoDataGenerator
from services.forecasting import DemandForecaster
from services.planner import calculate_charging_plan
from services.denso_gateway import DensoGatewayClient
from schemas.did import DriverDID, VehicleDID, ChargerDID, Location, DriverPreferences
from schemas.session import TripDetails
from models import ChargingSession, Site
from sqlalchemy import func
import warnings
warnings.filterwarnings('ignore', category=UserWarning)

def main():
    print("=" * 70)
    print("TASCO Auto Demo - With Denso DID Gateway Integration")
    print("Trip-Aware Smart Charging Orchestrator + Battery Birth Certificates")
    print("=" * 70)
    
    # Initialize DB
    init_db()
    db = SessionLocal()
    
    # Initialize Denso Gateway Client
    print("\n[1/7] Initializing Denso DID Gateway client...")
    gateway = DensoGatewayClient()
    
    # Generate CBAC for backend (Service Provider authentication)
    backend_did = "did:denso:tasco:backend-001"
    cbac_vp = gateway.generate_cbac_presentation(backend_did, "ServiceProvider")
    print("[OK] CBAC VP generated for backend authentication")
    print(f"      Backend DID: {backend_did}")
    print(f"      Role: ServiceProvider")
    
    # Generate sample data
    print("\n[2/7] Generating sample charging session data...")
    generator = DemoDataGenerator(db)
    stats = generator.generate_all(days=30)
    print(f"[OK] Generated: {stats['sessions_created']} sessions across {stats['sites_created']} sites")
    
    # Train AI model
    print("\n[3/7] Training AI demand forecasting model...")
    forecaster = DemandForecaster()
    metrics = forecaster.train(db)
    print(f"[OK] Model trained! Test R2: {metrics['test_r2']:.4f}, MAE: {metrics['mae']:.2f} kWh")
    
    # Create/retrieve battery DID and BBC
    print("\n[4/7] Creating battery DID and issuing BBC credential...")
    battery_did = gateway.create_did()
    print(f"[OK] Battery DID created: {battery_did}")
    
    # Issue BBC for this battery
    bbc_claims = {
        "type": "BBC",
        "batteryId": battery_did,
        "packUniqueId": f"urn:uuid:battery-pack-{battery_did[-8:]}",
        "manufacturersId": "did:denso:manufacturer:example",
        "manufacturingDate": "2023-06-15T00:00:00Z",
        "manufacturingLocation": "Aichi, Japan",
        "intendedUse": "Electric Vehicle - Fleet Use",
        "packWeight": "420",
        "lifeCycleStatus": "IN USE",  # Can be: IN USE, SECOND_LIFE, END_OF_LIFE
        "cellType": "Lithium-Ion",
        "mobileOrStationary": "Mobile",
        "bmsSoftwareVersion": "2.1.0"
    }
    
    bbc_credential = gateway.issue_bbc_credential(bbc_claims)
    print(f"[OK] BBC issued for battery")
    print(f"      Lifecycle Status: {bbc_claims['lifeCycleStatus']}")
    print(f"      Cell Type: {bbc_claims['cellType']}")
    print(f"      Manufacturing: {bbc_claims['manufacturingLocation']}")
    
    # Request battery wallet VP (simulates runtime credential retrieval)
    print("\n[5/7] Requesting battery wallet VP from gateway...")
    battery_vp = gateway.request_battery_wallet(battery_did)
    extracted_bbc = gateway.extract_bbc_claims(battery_vp)
    print(f"[OK] BBC retrieved from battery wallet")
    print(f"      Verified lifecycle status: {extracted_bbc.get('lifeCycleStatus', 'UNKNOWN')}")
    
    # Create sample session context
    vehicle = VehicleDID(
        did=battery_did,  # Use battery DID as vehicle identifier
        battery_capacity_kwh=75,
        nominal_consumption_wh_per_km=180,
        max_charge_power_kw=150,
        current_soc_percent=35,
        battery_health_percent=95
    )
    
    charger = ChargerDID(
        did="did:denso:charger:site_hq_chr01",
        site_id="site_hq",
        max_power_kw=150,
        location=Location(lat=60.1699, lon=24.9384),
        current_availability=True,
        current_tariff_eur_per_kwh=0.35
    )
    
    trip = TripDetails(
        distance_km=120,
        departure_time=datetime.utcnow() + timedelta(hours=3)
    )
    
    driver_preferences = DriverPreferences(priority="cost", carbon_conscious=True)
    
    # Calculate plan with BBC awareness
    print("\n[6/7] Calculating BBC-aware charging plan...")
    plan = calculate_charging_plan(
        vehicle=vehicle,
        trip=trip,
        charger=charger,
        driver_preferences=driver_preferences,
        bbc_claims=extracted_bbc
    )
    print("[OK] BBC-Aware Charging Plan:")
    print(f"  Battery:")
    print(f"    - DID: {battery_did}")
    print(f"    - Lifecycle: {extracted_bbc.get('lifeCycleStatus', 'UNKNOWN')}")
    print(f"    - Current SoC: {vehicle.current_soc_percent}% ({plan.current_energy_kwh:.2f} kWh)")
    print(f"  Trip:")
    print(f"    - Distance: {trip.distance_km}km")
    print(f"    - Needed Energy: {plan.needed_trip_energy_kwh:.2f} kWh (with 20% safety buffer)")
    print(f"    - Departure: 3 hours from now")
    print(f"  Charging:")
    print(f"    - Target SoC: {plan.target_soc_percent}%")
    print(f"    - Duration: {plan.planned_duration_hours:.2f} hours ({plan.planned_duration_hours*60:.0f} min)")
    print(f"    - Effective Power: {plan.effective_charge_power_kw:.1f} kW (BBC lifecycle-limited)")
    print(f"    - Cost: EUR {plan.planned_cost_eur:.2f}")
    print(f"  Optimization:")
    print(f"    - Plan Type: {plan.plan_type}")
    print(f"    - Feasible: {plan.is_feasible}")
    if plan.incentive_offers:
        offer = plan.incentive_offers[0]
        print(f"    - Incentive: {offer.value} {offer.type}")
        print(f"      Reason: {offer.reason}")
    
    # Get forecast
    print("\n[7/7] Getting AI demand forecast and site analytics...")
    forecasts = forecaster.predict("site_hq", datetime.utcnow(), db, hours_ahead=3)
    print("[OK] Demand Forecast (next 3 hours):")
    for i, f in enumerate(forecasts, 1):
        print(f"  Hour {i}: {f['predicted_total_kwh']:.2f} kWh ({f['predicted_active_sessions']} sessions predicted)")
    
    # Get analytics (simplified from routers/chargers.py)
    sessions = db.query(ChargingSession).filter(
        ChargingSession.site_id == "site_hq",
        ChargingSession.status == "completed"
    ).all()
    
    total_sessions = len(sessions)
    total_energy = sum(s.energy_delivered_kwh or 0 for s in sessions)
    total_revenue = sum(s.final_cost_eur or 0 for s in sessions)
    
    print(f"\n[OK] Site Analytics (site_hq):")
    print(f"  - Total Sessions: {total_sessions}")
    print(f"  - Total Energy Delivered: {total_energy:.2f} kWh")
    print(f"  - Total Revenue: EUR {total_revenue:.2f}")
    
    db.close()
    
    print("\n" + "=" * 70)
    print("DEMO COMPLETE - All Features Working!")
    print("=" * 70)
    print("\nKey Innovations Demonstrated:")
    print("  1. Battery DID + BBC integration with Denso DID Gateway")
    print("  2. Lifecycle-aware charging (protects degraded batteries)")
    print("  3. AI demand forecasting for site optimization")
    print("  4. Destination-aware planning (exact energy calculation)")
    print("  5. Smart incentives based on forecasts and preferences")
    print("\nNext Steps:")
    print("  - Run server: python run_server.py")
    print("  - API docs: http://localhost:8000/docs")
    print("  - Test with real Denso Gateway when credentials available")
    print("=" * 70)

if __name__ == "__main__":
    main()
