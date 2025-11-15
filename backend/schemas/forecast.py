from pydantic import BaseModel, Field
from typing import List
from datetime import datetime


class HourlyForecast(BaseModel):
    time_slot: datetime
    predicted_total_kwh: float
    predicted_active_sessions: int
    confidence_lower: float
    confidence_upper: float


class ForecastResponse(BaseModel):
    site_id: str
    forecasts: List[HourlyForecast]
    model_version: str = Field(default="v1.0")


class SiteAnalyticsResponse(BaseModel):
    site_id: str
    total_sessions: int
    total_energy_kwh: float
    total_revenue_eur: float
    avg_session_duration_hours: float
    peak_hour: int
    peak_demand_kwh: float
    cost_savings_eur: float
    incentive_acceptance_rate: float

