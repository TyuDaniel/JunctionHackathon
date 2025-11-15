# TASCO - Trip-Aware Smart Charging Orchestrator

A DID-based smart charging system that uses AI to optimize EV charging based on trip requirements, vehicle state, and site demand. Built for Junction 2025 Hackathon.

## 🎯 Concept

TASCO orchestrates intelligent EV charging by:
- **DID-Based Identity**: Secure, decentralized authentication for drivers, vehicles, and chargers
- **Mathematical Planning**: Calculate optimal charging plans based on trip distance, battery state, and departure time
- **AI Forecasting**: Predict site demand to optimize charging schedules and offer incentives
- **Smart Incentives**: Reward drivers for charging during off-peak hours

## 🏗️ Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Driver DID │     │ Vehicle DID │     │ Charger DID │
│             │     │             │     │             │
│ • Credentials│    │ • Battery   │     │ • Max Power │
│ • Preferences│    │ • SoC       │     │ • Tariff    │
│ • Site Access│    │ • Consumption│    │ • Location  │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           ▼
                  ┌────────────────┐
                  │  TASCO Backend │
                  │                │
                  │ • Math Planner │
                  │ • AI Forecaster│
                  │ • DID Validator│
                  └────────┬───────┘
                           │
                           ▼
                  ┌────────────────┐
                  │  SQLite DB     │
                  │                │
                  │ • Sessions     │
                  │ • Forecasts    │
                  │ • Analytics    │
                  └────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- pip

### Installation

1. **Clone the repository**
```bash
cd hackjunction
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment** (optional)
```bash
cp .env.example .env
# Edit .env if needed (defaults work fine)
```

4. **Run the server**
```bash
python -m backend.main
```

The API will start on `http://localhost:8000`

Visit `http://localhost:8000/docs` for interactive API documentation.

## 📊 Usage Flow

### Step 1: Generate Demo Data

Generate 30 days of realistic charging session data:

```bash
curl -X POST http://localhost:8000/api/v1/demo/generate-data?days=30
```

**Response:**
```json
{
  "status": "success",
  "message": "Generated 30 days of demo data",
  "statistics": {
    "sites_created": 5,
    "chargers_created": 33,
    "driver_dids": 20,
    "vehicle_dids": 30,
    "sessions_created": 1200+
  }
}
```

### Step 2: Train ML Model

Train the demand forecasting model:

```bash
curl -X POST http://localhost:8000/api/v1/forecasts/train
```

**Response:**
```json
{
  "status": "success",
  "message": "Model trained successfully",
  "metrics": {
    "train_r2": 0.92,
    "test_r2": 0.85,
    "mae": 5.23,
    "rmse": 7.45
  }
}
```

### Step 3: Start a Charging Session

Create a charging session with DID payloads:

```bash
curl -X POST http://localhost:8000/api/v1/sessions/start \
  -H "Content-Type: application/json" \
  -d '{
    "driver": {
      "did": "did:denso:driver:driver001",
      "credentials": ["Employee:TechCorp"],
      "preferences": {
        "priority": "cost",
        "carbon_conscious": true
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
      "current_availability": true,
      "current_tariff_eur_per_kwh": 0.35
    },
    "trip": {
      "distance_km": 120,
      "departure_time": "2025-11-15T18:00:00Z"
    }
  }'
```

**Response:**
```json
{
  "session_id": "uuid-here",
  "plan": {
    "needed_trip_energy_kwh": 25.92,
    "current_energy_kwh": 26.25,
    "extra_energy_needed_kwh": 0.0,
    "target_soc_percent": 35.0,
    "planned_duration_hours": 0.0,
    "planned_finish_time": "2025-11-15T15:30:00Z",
    "is_feasible": true,
    "feasibility_warning": null,
    "planned_cost_eur": 0.0,
    "effective_charge_power_kw": 127.5,
    "plan_type": "GREEN",
    "incentive_offers": [
      {
        "type": "reward_points",
        "value": 50.0,
        "reason": "Charging during solar peak hours (renewable energy available)"
      }
    ]
  },
  "message": "Session started successfully. Access granted - all DID credentials verified"
}
```

### Step 4: Get Demand Forecast

Query predicted demand for a site:

```bash
curl http://localhost:8000/api/v1/forecasts/site/site_hq?hours_ahead=24
```

### Step 5: Complete Session

Mark a session as complete:

```bash
curl -X POST http://localhost:8000/api/v1/sessions/{session_id}/complete \
  -H "Content-Type: application/json" \
  -d '{
    "energy_delivered_kwh": 25.5,
    "final_soc_percent": 85.0
  }'
```

### Step 6: View Analytics

Get site analytics:

```bash
curl http://localhost:8000/api/v1/sites/site_hq/analytics
```

**Response:**
```json
{
  "site_id": "site_hq",
  "total_sessions": 245,
  "total_energy_kwh": 7352.40,
  "total_revenue_eur": 2573.34,
  "avg_session_duration_hours": 1.85,
  "peak_hour": 17,
  "peak_demand_kwh": 456.20,
  "cost_savings_eur": 128.50,
  "incentive_acceptance_rate": 0.68
}
```

## 🔌 API Endpoints

### Sessions
- `POST /api/v1/sessions/start` - Start a new charging session
- `GET /api/v1/sessions/{session_id}` - Get session details
- `POST /api/v1/sessions/{session_id}/complete` - Complete a session

### Forecasts
- `POST /api/v1/forecasts/train` - Train ML forecasting model
- `GET /api/v1/forecasts/site/{site_id}` - Get demand forecast

### Chargers & Sites
- `GET /api/v1/chargers` - List all chargers
- `GET /api/v1/sites` - List all sites
- `GET /api/v1/sites/{site_id}/analytics` - Get site analytics

### Demo
- `POST /api/v1/demo/generate-data` - Generate synthetic demo data
- `GET /api/v1/demo/sample-dids` - Get sample DIDs for testing

## 🧮 Mathematical Planner

The core algorithm calculates optimal charging plans:

```python
# 1. Energy needed for trip (with 20% safety buffer)
needed_energy = (distance_km * consumption_wh_per_km / 1000) * 1.2

# 2. Current energy in battery
current_energy = battery_capacity_kwh * soc_percent / 100

# 3. Additional energy required
extra_energy = max(0, needed_energy - current_energy)

# 4. Charging time (with 85% efficiency)
effective_power = min(charger_max_kw, vehicle_max_kw) * 0.85
charge_time_hours = extra_energy / effective_power

# 5. Feasibility check
finish_time = now + charge_time_hours
is_feasible = finish_time <= departure_time

# 6. Cost calculation
cost = extra_energy * tariff_eur_per_kwh
```

## 🤖 AI Forecasting

Uses scikit-learn Random Forest with features:
- Hour of day, day of week
- Is weekend / holiday
- Site ID (encoded)
- Historical average kWh (last 7 days)
- Historical session count
- Temperature (simulated)

**Model Performance:**
- Training R²: ~0.92
- Test R²: ~0.85
- MAE: ~5.2 kWh
- RMSE: ~7.5 kWh

## 🎭 DID Simulation

DIDs are simulated as JSON structures:

**Driver DID:**
```json
{
  "did": "did:denso:driver:abc123",
  "credentials": ["Employee:CompanyX", "FleetDriver:FleetY"],
  "preferences": {"priority": "cost", "carbon_conscious": true},
  "allowed_sites": ["site_hq", "site_depot"]
}
```

**Vehicle DID:**
```json
{
  "did": "did:denso:vehicle:xyz789",
  "battery_capacity_kwh": 75,
  "nominal_consumption_wh_per_km": 180,
  "max_charge_power_kw": 150,
  "current_soc_percent": 35
}
```

**Charger DID:**
```json
{
  "did": "did:denso:charger:chr456",
  "site_id": "site_hq",
  "max_power_kw": 150,
  "location": {"lat": 60.1699, "lon": 24.9384},
  "current_availability": true,
  "current_tariff_eur_per_kwh": 0.35
}
```

## 🎯 Challenge Alignment

### Semi-Public B2B2C EV Charging ✅
Designed for workplaces, fleet depots, and retail locations.

### AI & Decentralized Identity ✅
- DID-based authentication for all actors
- ML forecasting for demand prediction
- Smart incentive recommendations

### Tri-Party Negotiation ✅
Driver, vehicle, and charger data combined to compute optimal plans.

### Demand Prediction ✅
Random Forest model predicts hourly demand per site.

### Business Value ✅
- Lower energy costs via off-peak charging
- Guaranteed charging for critical trips
- Predictive maintenance insights
- Usage analytics per site

## 📁 Project Structure

```
hackjunction/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── database.py          # SQLAlchemy setup
│   ├── models/              # Database models
│   │   ├── site.py
│   │   ├── charger.py
│   │   ├── session.py
│   │   ├── forecast.py
│   │   └── incentive.py
│   ├── schemas/             # Pydantic schemas
│   │   ├── did.py
│   │   ├── session.py
│   │   └── forecast.py
│   ├── services/            # Business logic
│   │   ├── planner.py       # Mathematical planner
│   │   ├── forecasting.py   # ML forecasting
│   │   └── did_validator.py
│   ├── routers/             # API endpoints
│   │   ├── sessions.py
│   │   ├── forecasts.py
│   │   ├── chargers.py
│   │   └── demo.py
│   └── utils/
│       └── demo_data.py     # Data generator
├── models/                  # Saved ML models
│   └── demand_forecast.pkl
├── requirements.txt
├── .env.example
└── README.md
```

## 🧪 Testing Scenarios

### Scenario 1: Insufficient Time
```json
{
  "vehicle": {"current_soc_percent": 20, ...},
  "trip": {"distance_km": 200, "departure_time": "1 hour from now"}
}
```
**Result:** Warning about infeasibility

### Scenario 2: Peak Demand Incentive
Start session during predicted peak hours (5-7 PM)
**Result:** Offered discount to delay charging

### Scenario 3: Green Charging
```json
{
  "driver": {"preferences": {"carbon_conscious": true}}
}
```
**Result:** GREEN plan type with reward points

### Scenario 4: Already Charged
```json
{
  "vehicle": {"current_soc_percent": 80, ...},
  "trip": {"distance_km": 50}
}
```
**Result:** Minimal/no charging needed

## 🎓 Key Innovations

1. **Priority Slot Credentials** (conceptual extension)
   - Fleet operators issue priority credentials
   - Guaranteed charging for urgent trips
   - DID-based, no central scheduler needed

2. **Destination-Aware Planning**
   - Calculates exact energy needed
   - Only charges what's necessary + buffer
   - Saves time and money

3. **AI-Driven Incentives**
   - Forecasts predict congestion
   - Dynamic discounts for load balancing
   - Rewards for green behavior

## 📊 Demo Data Patterns

Generated data includes realistic patterns:
- **Morning rush** (7-9 AM): High demand
- **Lunch** (12-1 PM): Medium demand  
- **Evening peak** (5-7 PM): Highest demand
- **Night/weekend**: Low demand

## 🔧 Development

### Run with auto-reload
```bash
python -m backend.main
```

### Test API
Interactive docs: http://localhost:8000/docs

### Database
SQLite database: `tasco.db` (created automatically)

## 🎬 Demo Script for Judges

1. **Setup** (30 seconds)
   ```bash
   pip install -r requirements.txt
   python -m backend.main &
   ```

2. **Generate Data** (10 seconds)
   ```bash
   curl -X POST http://localhost:8000/api/v1/demo/generate-data?days=30
   ```

3. **Train Model** (30 seconds)
   ```bash
   curl -X POST http://localhost:8000/api/v1/forecasts/train
   ```

4. **Show Interactive Docs**
   Open http://localhost:8000/docs

5. **Run Session** (30 seconds)
   Use Swagger UI to POST `/api/v1/sessions/start` with sample payload

6. **Show Forecast** (10 seconds)
   GET `/api/v1/forecasts/site/site_hq`

7. **Show Analytics** (10 seconds)
   GET `/api/v1/sites/site_hq/analytics`

**Total: ~2 minutes**

## 🏆 Success Criteria

- ✅ Mathematical planner calculates energy, time, cost correctly
- ✅ API endpoints functional and well-documented
- ✅ ML model trains with R² > 0.7
- ✅ Forecasts influence charging recommendations
- ✅ DID payloads structured and validated
- ✅ Demo data covers realistic usage patterns
- ✅ Clear documentation for judges

## 🚀 Future Enhancements

- Real DID integration with Denso DID Agent
- Live weather API integration
- WebSocket for real-time session updates
- Mobile app for drivers
- Dashboard for fleet operators
- Blockchain for credential verification
- Integration with grid APIs
- Multi-currency support

## 📝 License

Built for Junction 2025 Hackathon

## 👥 Team

TASCO Team @ Junction 2025

---

**Built with:** FastAPI, SQLAlchemy, scikit-learn, PostgreSQL → SQLite, Pydantic

**Challenge:** Junction 2025 - Smart EV Charging with AI and DID

