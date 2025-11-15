from sqlalchemy import Column, String, Float, DateTime, Text, Boolean, Index
from backend.database import Base
from datetime import datetime


class Incentive(Base):
    __tablename__ = "incentives"

    id = Column(String, primary_key=True, index=True)
    site_id = Column(String, nullable=False, index=True)
    time_slot = Column(DateTime, nullable=False, index=True)
    discount_percent = Column(Float, default=0.0)
    reward_points = Column(Float, default=0.0)
    reason = Column(Text, nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_site_time_active', 'site_id', 'time_slot', 'active'),
    )

