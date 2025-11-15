from sqlalchemy import Column, String, Float, Integer, DateTime, Index
from backend.database import Base
from datetime import datetime


class DemandForecast(Base):
    __tablename__ = "demand_forecasts"

    id = Column(String, primary_key=True, index=True)
    site_id = Column(String, nullable=False, index=True)
    time_slot = Column(DateTime, nullable=False, index=True)
    predicted_total_kwh = Column(Float, nullable=False)
    predicted_active_sessions = Column(Integer, nullable=False)
    confidence_lower = Column(Float, nullable=True)
    confidence_upper = Column(Float, nullable=True)
    model_version = Column(String, default="v1.0")
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_site_time', 'site_id', 'time_slot'),
        {'extend_existing': True}
    )

