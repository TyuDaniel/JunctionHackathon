from sqlalchemy import Column, String, Float, Integer
from backend.database import Base


class Site(Base):
    __tablename__ = "sites"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    location_lat = Column(Float, nullable=False)
    location_lon = Column(Float, nullable=False)
    total_capacity_kw = Column(Float, nullable=False)
    site_type = Column(String, nullable=False)  # workplace, fleet_depot, retail
    charger_count = Column(Integer, default=0)
    __table_args__ = {'extend_existing': True}

