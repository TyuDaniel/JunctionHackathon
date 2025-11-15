# Denso DID Gateway Integration Guide

## Overview

TASCO integrates with **Denso DID Gateway** (https://agent.dndapp.nadenso.com/swagger-api/) to provide DID-based identity and trust for EV charging orchestration.

## Key Concepts

### Battery Birth Certificate (BBC)
- **What**: A Verifiable Credential containing battery pack identity, manufacturing details, and lifecycle status
- **Why**: Enables battery-aware charging decisions that protect battery health and extend lifetime
- **How**: Issued via `/api/issue-credential`, retrieved via `/api/request-battery-wallet`

### CBAC (Capability-Based Access Control)
- **What**: A credential proving your backend has permission to call Gateway APIs
- **Why**: Establishes trust chain for accessing sensitive operations
- **How**: Generated via `/api/generate-cbac-presentation`, passed as `x-cbac-vp` header

### Verifiable Presentation (VP)
- **What**: A cryptographically signed bundle of credentials presented for verification
- **Why**: Proves claims without sharing raw data or requiring central authority
- **How**: Requested via `/api/request-presentation` or `/api/request-battery-wallet`

## Architecture

```
┌──────────────────┐
│   Denso DID      │
│     Gateway      │
│  (agent.dndapp   │
│   .nadenso.com)  │
└────────┬─────────┘
         │
         │ REST API
         │ (issue-credential, request-battery-wallet, etc.)
         │
┌────────▼─────────┐
│  TASCO Backend   │
│                  │
│  ┌────────────┐  │
│  │   Denso    │  │
│  │  Gateway   │  │
│  │   Client   │  │
│  └─────┬──────┘  │
│        │         │
│  ┌─────▼──────┐  │
│  │  Planner   │  │──► BBC-aware charging
│  │  + AI      │  │
│  └────────────┘  │
└──────────────────┘
```

## Credential Types Used

### 1. Battery Birth Certificate (BBC)

**Issued at**: Manufacturing or battery onboarding  
**Subject**: Battery DID (e.g., `did:itn:NiHW21TcdTkW8zk6ruhpfv`)  
**Claims**:
```json
{
  "type": "BBC",
  "batteryId": "did:itn:...",
  "packUniqueId": "urn:uuid:98b46d2b-...",
  "manufacturersId": "did:denso:manufacturer:001",
  "manufacturingDate": "2023-06-15T00:00:00Z",
  "manufacturingLocation": "Aichi, Japan",
  "intendedUse": "Electric Vehicle",
  "packWeight": "420",
  "lifeCycleStatus": "IN USE",
  "cellType": "Lithium-Ion",
  "mobileOrStationary": "Mobile",
  "bmsSoftwareVersion": "2.1.0"
}
```

**Usage in TASCO**:
- `lifeCycleStatus` determines safe C-rate limits:
  - `IN USE`: 1.5C (fast charging allowed)
  - `SECOND_LIFE`: 0.7C (gentler charging)
  - `END_OF_LIFE`: 0.3C (very limited)
- `cellType` may influence charging curves
- Manufacturing date helps estimate age-based degradation

### 2. CBAC (Capability-Based Access Control)

**Issued to**: TASCO Backend (Service Provider)  
**Claims**:
```json
{
  "type": "CBAC",
  "Role": "ServiceProvider",
  "Permissions": [
    "AccessCoreServicesAPI",
    "RequestBatteryWallet",
    "IssueCBAC"
  ]
}
```

**Usage in TASCO**:
- Presented in `x-cbac-vp` header when calling protected Gateway endpoints
- Proves TASCO is authorized to request battery information

### 3. Asset Ownership (Optional Extension)

**Issued at**: Charger deployment  
**Subject**: Charger DID  
**Claims**:
```json
{
  "previousOwner": "Initial Owner Corp",
  "currentOwner": "Charging Network Operator",
  "assetInformation": {
    "id": "did:denso:charger:chr456",
    "manufacturer": "Denso",
    "name": "DC Fast Charger 150kW",
    "jurisdiction": "EU"
  }
}
```

**Usage in TASCO**:
- Verifies charger ownership for trust
- Enables multi-operator scenarios

## Integration Flow

### Onboarding Phase (One-time Setup)

1. **Create Battery DID**
```python
battery_did = gateway_client.create_did()
# Returns: "did:itn:NiHW21TcdTkW8zk6ruhpfv"
```

2. **Issue BBC**
```python
bbc_credential = gateway_client.issue_bbc_credential({
    "batteryId": battery_did,
    "lifeCycleStatus": "IN USE",
    # ... other claims
})
```

3. **Generate Backend CBAC**
```python
cbac_vp = gateway_client.generate_cbac_presentation(
    holder_did="did:denso:tasco:backend",
    access_level="ServiceProvider"
)
```

### Runtime (Every Charging Session)

1. **EV Arrives at Charger**
   - BMS provides battery DID
   - Driver inputs trip details (destination, departure time)

2. **TASCO Requests BBC**
```python
battery_vp = gateway_client.request_battery_wallet(battery_did)
bbc_claims = gateway_client.extract_bbc_claims(battery_vp)
```

3. **Calculate Charging Plan**
```python
plan = calculate_charging_plan(
    vehicle=vehicle_state,
    trip=trip_details,
    charger=charger_capabilities,
    driver_preferences=preferences,
    bbc_claims=bbc_claims  # BBC-aware!
)
```

4. **Plan Includes BBC Awareness**
   - Power limited by lifecycle status
   - Cost optimized with forecasting
   - Battery health protected

## API Endpoints (Denso Gateway)

### Used in TASCO

| Endpoint | Purpose | TASCO Usage |
|----------|---------|-------------|
| `GET /api/create-did` | Create new DID | Create battery DIDs during onboarding |
| `POST /api/issue-credential?credential_type=BBC` | Issue BBC | Issue BBC for each battery pack |
| `POST /api/generate-cbac-presentation` | Get CBAC for backend | Authenticate TASCO backend |
| `POST /api/request-battery-wallet` | Get BBC VP | Retrieve BBC at session start |
| `POST /api/verify-presentation` | Verify VP | Validate received credentials |

### Authentication Pattern

All protected Gateway calls require `x-cbac-vp` header:
```python
headers = {
    "Content-Type": "application/json",
    "x-cbac-vp": json.dumps(cbac_vp)
}
```

## Battery-Aware Charging Logic

### C-Rate Limits by Lifecycle Status

Defined in `backend/services/planner.py`:

```python
LIFECYCLE_CRATE_LIMITS = {
    "IN USE": 1.5,         # 112.5 kW for 75 kWh battery
    "SECOND_LIFE": 0.7,    # 52.5 kW for 75 kWh battery
    "END_OF_LIFE": 0.3,    # 22.5 kW for 75 kWh battery
    "UNKNOWN": 1.0         # Conservative default
}
```

### Calculation

```python
crate_limit = LIFECYCLE_CRATE_LIMITS[bbc_claims["lifeCycleStatus"]]
max_safe_power_kw = crate_limit * battery_capacity_kwh

effective_power = min(
    charger.max_power_kw,
    vehicle.max_charge_power_kw,
    max_safe_power_kw  # BBC-informed limit
) * 0.85  # Efficiency factor
```

### Result
- **IN USE** batteries get full power (within charger/vehicle limits)
- **SECOND_LIFE** batteries charge at ~47% speed (battery health protection)
- **END_OF_LIFE** batteries charge at ~20% speed (maximum protection)

## Business Value

### 1. Battery Lifetime Extension
- By respecting lifecycle status, reduce degradation
- Estimated 15-20% longer usable life for SECOND_LIFE batteries

### 2. Total Cost of Ownership (TCO) Reduction
- Lower replacement costs
- Better residual value
- Smoother transition to second-life applications

### 3. Fleet Optimization
- Track all batteries by DID across vehicles
- Predict maintenance needs
- Plan second-life deployment based on BBC history

### 4. Trust & Compliance
- Cryptographic proof of battery provenance
- Audit trail for safety compliance
- No central identity database (privacy-preserving)

## Demo vs Production

### Current Demo Mode (Hackathon)
- Gateway calls use fallback simulation when offline
- Returns realistic BBC structures for testing
- No actual cryptographic verification
- Perfect for demos without internet/credentials

### Production Mode
- Replace simulation with real Gateway API credentials
- Full cryptographic verification
- Real-time DID document resolution
- Integration with vehicle BMS and charger firmware

## Sample Output from `auto_demo.py`

```
[4/7] Creating battery DID and issuing BBC credential...
[OK] Battery DID created: did:denso:simulated:1700000000
[OK] BBC issued for battery
      Lifecycle Status: IN USE
      Cell Type: Lithium-Ion
      Manufacturing: Aichi, Japan

[5/7] Requesting battery wallet VP from gateway...
[OK] BBC retrieved from battery wallet
      Verified lifecycle status: IN USE

[6/7] Calculating BBC-aware charging plan...
[OK] BBC-Aware Charging Plan:
  Battery:
    - DID: did:denso:simulated:1700000000
    - Lifecycle: IN USE
    - Current SoC: 35.0% (26.25 kWh)
  Charging:
    - Effective Power: 95.6 kW (BBC lifecycle-limited)
```

## Implementation Checklist

- ✅ Denso Gateway client (`backend/services/denso_gateway.py`)
- ✅ Credential schemas (`backend/schemas/credentials.py`)
- ✅ BBC-aware planner (`backend/services/planner.py`)
- ✅ Simulation fallback for offline demos
- ✅ Auto demo showcasing full flow
- ⏳ Real Gateway API credentials (for production)
- ⏳ Frontend UI showing BBC details
- ⏳ WebSocket for real-time BMS integration

## Testing with Real Gateway

When ready to test with actual Denso Gateway:

1. **Get API credentials** from Denso
2. **Update `.env`**:
   ```
   DENSO_GATEWAY_URL=https://agent.dndapp.nadenso.com
   DENSO_API_KEY=your_api_key_here
   ```
3. **Update client initialization**:
   ```python
   gateway = DensoGatewayClient(
       gateway_url=os.getenv("DENSO_GATEWAY_URL"),
       api_key=os.getenv("DENSO_API_KEY")
   )
   ```
4. **Run**: `python auto_demo.py`

The code will automatically use real Gateway instead of simulation!

## References

- Denso DID Gateway Swagger: https://agent.dndapp.nadenso.com/swagger-api/
- W3C VC Data Model: https://www.w3.org/TR/vc-data-model/
- W3C DID Core: https://www.w3.org/TR/did-core/

---

**Built for Junction 2025 Hackathon**  
**TASCO - Battery-Aware Smart Charging with Denso DID Gateway**

