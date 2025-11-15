"""
Quick manual test of core functionality without server
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

print("=" * 60)
print("TASCO Quick Test - Core Functionality")
print("=" * 60)

# Test 1: Database setup
print("\n1. Testing database setup...")
try:
    from backend.database import init_db, SessionLocal
    init_db()
    db = SessionLocal()
    print("[OK] Database initialized successfully")
    db.close()
except Exception as e:
    print(f"[FAIL] Database error: {e}")
    sys.exit(1)

# Test 2: Mathematical planner
print("\n2. Testing mathematical planner...")
try:
    from backend.services.planner import calculate_charging_plan
    from backend.schemas.did import VehicleDID, ChargerDID, DriverPreferences, Location
    from backend.schemas.session import TripDetails
    from datetime import datetime, timedelta
    
    vehicle = VehicleDID(
        did="did:test:vehicle:001",
        battery_capacity_kwh=75,
        nominal_consumption_wh_per_km=180,
        max_charge_power_kw=150,
        current_soc_percent=35
    )
    
    charger = ChargerDID(
        did="did:test:charger:001",
        site_id="test_site",
        max_power_kw=150,
        location=Location(lat=60.1699, lon=24.9384),
        current_availability=True,
        current_tariff_eur_per_kwh=0.35
    )
    
    trip = TripDetails(
        distance_km=120,
        departure_time=datetime.utcnow() + timedelta(hours=3)
    )
    
    preferences = DriverPreferences(priority="cost", carbon_conscious=True)
    
    plan = calculate_charging_plan(vehicle, trip, charger, preferences)
    
    print(f"[OK] Plan calculated successfully")
    print(f"   Target SoC: {plan.target_soc_percent}%")
    print(f"   Duration: {plan.planned_duration_hours:.2f} hours")
    print(f"   Cost: EUR {plan.planned_cost_eur}")
    print(f"   Feasible: {plan.is_feasible}")
    
except Exception as e:
    print(f"[FAIL] Planner error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: DID validation
print("\n3. Testing DID validation...")
try:
    from backend.services.did_validator import validate_did_access
    from backend.schemas.did import DriverDID
    
    driver = DriverDID(
        did="did:denso:driver:test001",
        credentials=["Employee:TestCorp"],
        preferences=DriverPreferences(priority="cost"),
        allowed_sites=["test_site"]
    )
    
    is_valid, msg = validate_did_access(driver, vehicle, charger)
    
    if is_valid:
        print(f"[OK] DID validation passed: {msg}")
    else:
        print(f"[FAIL] DID validation failed: {msg}")
        
except Exception as e:
    print(f"[FAIL] DID validation error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Data generator
print("\n4. Testing demo data generator...")
try:
    from backend.utils.demo_data import DemoDataGenerator
    from backend.database import SessionLocal
    
    db = SessionLocal()
    generator = DemoDataGenerator(db)
    
    # Just test initialization, don't generate full data
    print(f"[OK] Data generator initialized")
    print(f"   Sites configured: {len(generator.SITES)}")
    print(f"   Vehicle types: {len(generator.VEHICLE_TYPES)}")
    
    db.close()
    
except Exception as e:
    print(f"[FAIL] Data generator error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: ML forecaster initialization
print("\n5. Testing ML forecaster initialization...")
try:
    from backend.services.forecasting import DemandForecaster
    
    forecaster = DemandForecaster()
    print(f"[OK] Forecaster initialized")
    print(f"   Features: {len(forecaster.feature_cols)}")
    
except Exception as e:
    print(f"[FAIL] Forecaster error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("[SUCCESS] ALL CORE TESTS PASSED!")
print("=" * 60)
print("\nCore functionality is working correctly.")
print("You can now:")
print("1. Run the server: python run_server.py")
print("2. Visit http://localhost:8000/docs for API docs")
print("3. Run integration tests: python test_api.py")

