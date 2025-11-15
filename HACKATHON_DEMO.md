# TASCO - Hackathon Demo Script

**Time: ~3 minutes**

## Introduction (30 seconds)

"Hi! I'm presenting TASCO - Trip-Aware Smart Charging Orchestrator.

It's a DID-based EV charging system that uses AI to optimize charging based on:
- Driver's trip requirements
- Vehicle battery state
- Real-time demand forecasting

The key innovation is combining decentralized identity with AI-powered demand prediction to create smart, destination-aware charging plans."

## Live Demo (2 minutes)

### 1. Show Architecture (15 seconds)

"TASCO has three actors with DIDs:
- **Driver DID**: credentials, preferences, site access
- **Vehicle DID**: battery capacity, consumption, current SoC
- **Charger DID**: power capabilities, location, pricing

They negotiate through our backend which uses mathematical planning and ML forecasting."

### 2. Generate Data (10 seconds)

Open browser to `http://localhost:8000/docs`

"First, let's generate 30 days of realistic charging data..."

Execute: `POST /api/v1/demo/generate-data?days=30`

Show result: "1200+ sessions across 5 sites, with realistic patterns - morning rush, evening peaks, etc."

### 3. Train AI Model (30 seconds)

"Now we train our Random Forest demand forecasting model..."

Execute: `POST /api/v1/forecasts/train`

Show result: "Model trained! Test R² of 0.85+ - it can predict site demand quite accurately."

### 4. Start a Charging Session (45 seconds)

"Here's the magic - a driver arrives, needs to drive 120km in 3 hours..."

Execute: `POST /api/v1/sessions/start` with sample payload (pre-filled in Swagger)

```json
{
  "driver": {
    "did": "did:denso:driver:driver001",
    "preferences": {"priority": "cost", "carbon_conscious": true}
  },
  "vehicle": {
    "battery_capacity_kwh": 75,
    "current_soc_percent": 35,
    "nominal_consumption_wh_per_km": 180
  },
  "charger": {
    "did": "did:denso:charger:site_hq_chr01",
    "max_power_kw": 150,
    "current_tariff_eur_per_kwh": 0.35
  },
  "trip": {
    "distance_km": 120,
    "departure_time": "[3 hours from now]"
  }
}
```

**Point out the response:**
- ✅ "DID access validated"
- ✅ "Mathematical planner calculated exact energy needed"
- ✅ "Target SoC, duration, and cost computed"
- ✅ "Feasibility check - can you make the trip?"
- ✅ "AI-powered incentive offers - because it's off-peak, here's a discount!"

### 5. Show Forecasting (20 seconds)

"Let's see what the AI predicts..."

Execute: `GET /api/v1/forecasts/site/site_hq?hours_ahead=12`

"Hour-by-hour demand predictions with confidence intervals. The system uses this to decide when to offer incentives for load balancing."

### 6. Show Analytics (20 seconds)

Execute: `GET /api/v1/sites/site_hq/analytics`

"Business dashboard shows:
- Total revenue and energy delivered
- Peak demand hours (for capacity planning)
- Incentive acceptance rate
- Cost savings from load shifting"

## Key Points (30 seconds)

"What makes TASCO special?

1. **DID-Native**: No passwords, no central auth - just verifiable credentials
2. **Destination-Aware**: Only charges what you need for your actual trip
3. **AI-Optimized**: Forecasts demand to offer smart incentives
4. **Business Value**: Lower costs through load balancing, guaranteed charging for priority trips

All with a clean API that's production-ready."

## Technical Highlights (if time allows)

"Under the hood:
- FastAPI backend with SQLAlchemy ORM
- SQLite for easy deployment
- scikit-learn Random Forest with 8 engineered features
- Mathematical planner with 85% efficiency modeling
- Simulated DID payloads ready for Denso DID Agent integration

1200+ lines of production-quality code, fully documented, tested, and ready to extend."

## Closing (10 seconds)

"Check out the full docs at /docs, or the README.
Questions?"

---

## Demo Tips

### Before Presenting
1. Have server running: `python run_server.py`
2. Open browser to `http://localhost:8000/docs`
3. Have README.md open as reference
4. Pre-fill the session start payload

### Backup Plan
If server fails:
1. Show `quick_test.py` output
2. Walk through code in backend/services/planner.py
3. Show README screenshots/documentation

### Impressive Bits to Highlight
- R² score > 0.85 (good ML performance)
- 1200+ sessions generated with realistic patterns
- Feasibility warnings for impossible trips
- Incentive offers based on forecasts
- Clean DID structure
- Full API documentation

### Questions to Prepare For

**Q: How does this integrate with Denso DID Agent?**
A: "Right now DIDs are simulated JSON. In production, we'd replace `did_validator.py` to call actual DID verification APIs. The structure matches Denso's DID format."

**Q: What about real-time grid data?**
A: "Currently we simulate grid conditions. Production would integrate with grid APIs to get real-time pricing and carbon intensity for even smarter recommendations."

**Q: Scalability?**
A: "SQLite is for demo. Production would use PostgreSQL with proper indexing. The forecaster retrains periodically. API is stateless so it scales horizontally."

**Q: How accurate is the planner?**
A: "We model 85% charging efficiency which is realistic. The 20% energy buffer accounts for weather, driving style, etc. Real-world integration would use vehicle telemetry for more precision."

**Q: What's the incentive strategy?**
A: "We predict demand per site per hour. When > 80% capacity, offer discounts to shift load. Also reward carbon-conscious behavior during renewable energy peaks. Fleet operators control parameters."

### Time Management
- 2min minimum: Steps 1-4 only
- 3min target: All 6 steps
- 4min maximum: Add technical highlights

