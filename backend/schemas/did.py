from pydantic import BaseModel, Field
from typing import List, Optional


class Location(BaseModel):
    lat: float = Field(..., description="Latitude")
    lon: float = Field(..., description="Longitude")


class DriverPreferences(BaseModel):
    priority: str = Field(default="cost", description="Driver priority: cost, speed, carbon")
    carbon_conscious: bool = Field(default=False, description="Willing to delay for greener energy")


class DriverDID(BaseModel):
    """
    Driver DID - simulated decentralized identity for the driver
    Contains credentials, preferences, and site access permissions
    """
    did: str = Field(..., description="DID identifier, e.g., did:denso:driver:abc123")
    credentials: List[str] = Field(
        default_factory=list,
        description="List of credentials like 'Employee:CompanyX', 'FleetDriver:FleetY'"
    )
    preferences: DriverPreferences = Field(default_factory=DriverPreferences)
    allowed_sites: List[str] = Field(
        default_factory=list,
        description="List of site IDs where driver is allowed to charge"
    )


class VehicleDID(BaseModel):
    """
    Vehicle DID - simulated decentralized identity for the vehicle
    Contains static properties (capacity, consumption) and dynamic state (SoC)
    """
    did: str = Field(..., description="DID identifier, e.g., did:denso:vehicle:xyz789")
    battery_capacity_kwh: float = Field(..., gt=0, description="Battery capacity in kWh")
    nominal_consumption_wh_per_km: float = Field(
        ...,
        gt=0,
        description="Average energy consumption in Wh per km"
    )
    max_charge_power_kw: float = Field(..., gt=0, description="Maximum charging power in kW")
    current_soc_percent: float = Field(
        ...,
        ge=0,
        le=100,
        description="Current state of charge in percent"
    )
    battery_health_percent: Optional[float] = Field(
        default=100.0,
        ge=0,
        le=100,
        description="Battery health percentage"
    )


class ChargerDID(BaseModel):
    """
    Charger DID - simulated decentralized identity for the charging station
    Contains static properties (max power, location) and dynamic state (availability, tariff)
    """
    did: str = Field(..., description="DID identifier, e.g., did:denso:charger:chr456")
    site_id: str = Field(..., description="ID of the site where charger is located")
    max_power_kw: float = Field(..., gt=0, description="Maximum power output in kW")
    location: Location = Field(..., description="Geographic location")
    current_availability: bool = Field(default=True, description="Is charger currently available")
    current_tariff_eur_per_kwh: float = Field(
        ...,
        gt=0,
        description="Current electricity tariff in EUR per kWh"
    )

