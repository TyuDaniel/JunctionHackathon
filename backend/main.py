"""
TASCO - Trip-Aware Smart Charging Orchestrator
Main FastAPI application entry point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

from backend.database import init_db
from backend.routers import sessions_router, forecasts_router, chargers_router, demo_router

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="TASCO API",
    description="""
    Trip-Aware Smart Charging Orchestrator (TASCO)
    
    A DID-based system where driver, vehicle, and charger securely share data 
    to compute smart, destination-aware charging plans in real-time, while an 
    AI backend learns from sessions to forecast demand and offer incentives.
    
    ## Key Features
    
    - **DID-Based Authentication**: Secure identity verification for drivers, vehicles, and chargers
    - **Mathematical Planner**: Calculate optimal charging plans based on trip requirements
    - **AI Demand Forecasting**: Predict site demand using ML to optimize charging schedules
    - **Smart Incentives**: Offer discounts and rewards for optimal charging behavior
    - **Real-time Analytics**: Track energy usage, costs, and site performance
    
    ## Quick Start
    
    1. Generate demo data: `POST /api/v1/demo/generate-data`
    2. Train ML model: `POST /api/v1/forecasts/train`
    3. Start a session: `POST /api/v1/sessions/start`
    4. Get forecasts: `GET /api/v1/forecasts/site/{site_id}`
    
    Built for Junction 2025 Hackathon
    """,
    version="1.0.0",
    contact={
        "name": "TASCO Team",
        "url": "https://github.com/yourusername/tasco"
    }
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
@app.on_event("startup")
def startup_event():
    """Initialize database tables on startup"""
    print("Initializing database...")
    init_db()
    print("Database initialized!")
    
    # Create models directory if it doesn't exist
    os.makedirs("models", exist_ok=True)

# Include routers
app.include_router(sessions_router)
app.include_router(forecasts_router)
app.include_router(chargers_router)
app.include_router(demo_router)


@app.get("/")
def root():
    """Root endpoint with API information"""
    return {
        "name": "TASCO API",
        "version": "1.0.0",
        "description": "Trip-Aware Smart Charging Orchestrator",
        "docs": "/docs",
        "health": "healthy"
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "tasco-api"
    }


if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    
    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        reload=True
    )

