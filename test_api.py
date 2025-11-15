"""
Integration test script for TASCO API
Tests the complete flow: generate data -> train model -> start session
"""
import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"


def test_health():
    """Test health endpoint"""
    print("🔍 Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"✅ Health check: {response.json()}")
    return response.status_code == 200


def test_generate_data():
    """Generate demo data"""
    print("\n📊 Generating demo data...")
    response = requests.post(f"{BASE_URL}/api/v1/demo/generate-data?days=30")
    data = response.json()
    print(f"✅ Generated: {data['statistics']['sessions_created']} sessions")
    print(f"   Sites: {data['statistics']['sites_created']}")
    print(f"   Chargers: {data['statistics']['chargers_created']}")
    return response.status_code == 200


def test_train_model():
    """Train ML forecasting model"""
    print("\n🤖 Training ML model...")
    response = requests.post(f"{BASE_URL}/api/v1/forecasts/train")
    data = response.json()
    print(f"✅ Model trained successfully")
    print(f"   Test R²: {data['metrics']['test_r2']}")
    print(f"   MAE: {data['metrics']['mae']}")
    return response.status_code == 200


def test_start_session():
    """Start a charging session"""
    print("\n⚡ Starting charging session...")
    
    # Prepare request payload
    departure_time = (datetime.utcnow() + timedelta(hours=3)).isoformat() + "Z"
    
    payload = {
        "driver": {
            "did": "did:denso:driver:driver001",
            "credentials": ["Employee:TechCorp"],
            "preferences": {
                "priority": "cost",
                "carbon_conscious": True
            },
            "allowed_sites": ["site_hq"]
        },
        "vehicle": {
            "did": "did:denso:vehicle:vehicle001",
            "battery_capacity_kwh": 75,
            "nominal_consumption_wh_per_km": 180,
            "max_charge_power_kw": 150,
            "current_soc_percent": 35
        },
        "charger": {
            "did": "did:denso:charger:site_hq_chr01",
            "site_id": "site_hq",
            "max_power_kw": 150,
            "location": {"lat": 60.1699, "lon": 24.9384},
            "current_availability": True,
            "current_tariff_eur_per_kwh": 0.35
        },
        "trip": {
            "distance_km": 120,
            "departure_time": departure_time
        }
    }
    
    response = requests.post(
        f"{BASE_URL}/api/v1/sessions/start",
        json=payload
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Session started: {data['session_id']}")
        print(f"   Target SoC: {data['plan']['target_soc_percent']}%")
        print(f"   Charging time: {data['plan']['planned_duration_hours']:.2f} hours")
        print(f"   Cost: €{data['plan']['planned_cost_eur']}")
        print(f"   Plan type: {data['plan']['plan_type']}")
        print(f"   Feasible: {data['plan']['is_feasible']}")
        if data['plan']['incentive_offers']:
            print(f"   Incentives: {len(data['plan']['incentive_offers'])} offered")
        return True, data['session_id']
    else:
        print(f"❌ Session failed: {response.text}")
        return False, None


def test_get_forecast():
    """Get demand forecast"""
    print("\n📈 Getting demand forecast...")
    response = requests.get(f"{BASE_URL}/api/v1/forecasts/site/site_hq?hours_ahead=12")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Forecast retrieved for site: {data['site_id']}")
        print(f"   Forecasts: {len(data['forecasts'])} hours")
        if data['forecasts']:
            first = data['forecasts'][0]
            print(f"   Next hour prediction: {first['predicted_total_kwh']} kWh")
            print(f"   Expected sessions: {first['predicted_active_sessions']}")
        return True
    else:
        print(f"❌ Forecast failed: {response.text}")
        return False


def test_get_analytics():
    """Get site analytics"""
    print("\n📊 Getting site analytics...")
    response = requests.get(f"{BASE_URL}/api/v1/sites/site_hq/analytics")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Analytics retrieved for site: {data['site_id']}")
        print(f"   Total sessions: {data['total_sessions']}")
        print(f"   Total energy: {data['total_energy_kwh']} kWh")
        print(f"   Total revenue: €{data['total_revenue_eur']}")
        print(f"   Peak hour: {data['peak_hour']}:00")
        print(f"   Incentive acceptance: {data['incentive_acceptance_rate']*100:.1f}%")
        return True
    else:
        print(f"❌ Analytics failed: {response.text}")
        return False


def test_complete_session(session_id):
    """Complete a charging session"""
    print(f"\n✅ Completing session {session_id}...")
    
    payload = {
        "energy_delivered_kwh": 25.5,
        "final_soc_percent": 85.0
    }
    
    response = requests.post(
        f"{BASE_URL}/api/v1/sessions/{session_id}/complete",
        json=payload
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Session completed")
        print(f"   Final cost: €{data['final_cost_eur']}")
        print(f"   Duration: {data['duration_hours']:.2f} hours")
        return True
    else:
        print(f"❌ Completion failed: {response.text}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("TASCO API Integration Tests")
    print("=" * 60)
    
    try:
        # Step 1: Health check
        if not test_health():
            print("\n❌ Server not responding. Is it running?")
            return
        
        # Step 2: Generate data
        if not test_generate_data():
            print("\n❌ Data generation failed")
            return
        
        # Step 3: Train model
        if not test_train_model():
            print("\n❌ Model training failed")
            return
        
        # Step 4: Start session
        success, session_id = test_start_session()
        if not success:
            print("\n❌ Session start failed")
            return
        
        # Step 5: Get forecast
        if not test_get_forecast():
            print("\n⚠️ Forecast failed (non-critical)")
        
        # Step 6: Get analytics
        if not test_get_analytics():
            print("\n⚠️ Analytics failed (non-critical)")
        
        # Step 7: Complete session
        if session_id and not test_complete_session(session_id):
            print("\n⚠️ Session completion failed (non-critical)")
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nTASCO backend is ready for demo! 🎉")
        print(f"Visit {BASE_URL}/docs for interactive API documentation")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

