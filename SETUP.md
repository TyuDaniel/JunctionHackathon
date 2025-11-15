# TASCO Setup Guide

## Quick Start (2 minutes)

### 1. Install Dependencies
```bash
cd hackjunction
pip install -r requirements.txt
```

### 2. Start the Server
```bash
python run_server.py
```

The server will start on `http://localhost:8000`

### 3. Open Interactive API Documentation
Open your browser and navigate to:
```
http://localhost:8000/docs
```

## Complete Demo Flow

### Step 1: Generate Demo Data (10 seconds)

**Using curl:**
```bash
curl -X POST http://localhost:8000/api/v1/demo/generate-data?days=30
```

**Using browser:** Navigate to http://localhost:8000/docs and use the `/api/v1/demo/generate-data` endpoint

**Expected result:** ~1200+ charging sessions created across 5 sites with 33 chargers

### Step 2: Train ML Model (30 seconds)

**Using curl:**
```bash
curl -X POST http://localhost:8000/api/v1/forecasts/train
```

**Using browser:** Use the `/api/v1/forecasts/train` endpoint in Swagger UI

**Expected result:** Model trained with R² > 0.85

### Step 3: Start a Charging Session

**Sample request** (copy-paste into Swagger UI or use with curl):

```json
{
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
}
```

**Expected result:**
- Charging plan with calculated energy needs
- Target SoC percentage
- Estimated duration and cost
- Feasibility check
- Possible incentive offers

### Step 4: View Demand Forecast

```bash
curl http://localhost:8000/api/v1/forecasts/site/site_hq?hours_ahead=24
```

**Expected result:** Hourly predictions for next 24 hours

### Step 5: View Site Analytics

```bash
curl http://localhost:8000/api/v1/sites/site_hq/analytics
```

**Expected result:**
- Total sessions and energy
- Revenue metrics
- Peak demand analysis
- Incentive acceptance rate

## Testing

### Quick Core Test (no server needed)
```bash
python quick_test.py
```

Tests:
- Database initialization
- Mathematical planner
- DID validation
- Data generator
- ML forecaster

### Full Integration Test (requires running server)
```bash
python test_api.py
```

Tests the complete flow end-to-end.

## Troubleshooting

### Server won't start
- Check if port 8000 is already in use
- Try: `python -m backend.main` instead

### Database errors
- Delete `tasco.db` and restart server (it will recreate)

### Import errors
- Ensure you're in the `hackjunction` directory
- Reinstall dependencies: `pip install -r requirements.txt`

### Model not trained
- Run `/api/v1/demo/generate-data` first
- Then run `/api/v1/forecasts/train`
- Model needs at least 100 sessions to train

## File Structure

```
hackjunction/
├── backend/              # Main application code
│   ├── main.py          # FastAPI app
│   ├── database.py      # Database setup
│   ├── models/          # SQLAlchemy models
│   ├── schemas/         # Pydantic schemas (DID payloads)
│   ├── services/        # Business logic (planner, forecaster)
│   ├── routers/         # API endpoints
│   └── utils/           # Demo data generator
├── models/              # Saved ML models
│   └── demand_forecast.pkl (created after training)
├── tasco.db            # SQLite database (auto-created)
├── requirements.txt    # Python dependencies
├── run_server.py       # Simple server startup
├── quick_test.py       # Core functionality tests
├── test_api.py         # Integration tests
├── README.md           # Full documentation
└── SETUP.md            # This file
```

## Available Sites

After generating demo data, you'll have these sites:

1. **site_hq** - Corporate HQ (8 chargers, 600 kW)
2. **site_depot** - Fleet Depot (10 chargers, 800 kW)
3. **site_mall** - Shopping Mall (5 chargers, 400 kW)
4. **site_office** - Tech Office Park (6 chargers, 450 kW)
5. **site_retail** - Retail Center (4 chargers, 300 kW)

## Sample DIDs

**Driver DIDs:** did:denso:driver:driver001 to driver020
**Vehicle DIDs:** did:denso:vehicle:vehicle001 to vehicle030
**Charger DIDs:** did:denso:charger:site_{site}_chr{num}

## API Documentation

Full interactive API docs available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Environment Variables

Create `.env` file (optional, defaults work):
```
DATABASE_URL=sqlite:///./tasco.db
ML_MODEL_PATH=models/demand_forecast.pkl
API_HOST=0.0.0.0
API_PORT=8000
```

## Next Steps

1. Explore the API documentation at `/docs`
2. Try different scenarios (peak hours, low battery, long trips)
3. View forecasts for different sites
4. Compare analytics across sites
5. Test with different driver preferences

## Support

For issues or questions, refer to:
- README.md - Full documentation
- /docs endpoint - API reference
- quick_test.py - Verify core functionality

