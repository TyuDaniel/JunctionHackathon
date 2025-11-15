from sqlalchemy import Column, String, Float, Boolean, ForeignKey
from backend.database import Base


class Charger(Base):
    __tablename__ = "chargers"

    did = Column(String, primary_key=True, index=True)
    site_id = Column(String, ForeignKey("sites.id"), nullable=False, index=True)
    max_power_kw = Column(Float, nullable=False)
    current_availability = Column(Boolean, default=True)
    current_tariff_eur_per_kwh = Column(Float, nullable=False)
    location_lat = Column(Float, nullable=False)
    location_lon = Column(Float, nullable=False)
    charger_type = Column(String, default="DC")  # AC or DC
    __table_args__ = {'extend_existing': True}

