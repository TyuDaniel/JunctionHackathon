"""
Verifiable Credential Schemas for Denso DID Gateway
These define the claims we provide to the Gateway for VC issuance
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class DriverMembershipClaims(BaseModel):
    """
    Claims for Driver Membership Credential
    Proves driver is authorized to charge at certain sites
    """
    driver_id: str = Field(..., description="Internal driver identifier")
    company_id: str = Field(..., description="Company or fleet ID")
    role: str = Field(..., description="employee, fleet_driver, tenant, guest")
    permission_level: str = Field(default="normal", description="normal, priority_eligible, vip")
    allowed_sites: List[str] = Field(default_factory=list, description="List of site IDs where authorized")
    issued_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(None, description="Expiration time if applicable")


class VehicleProfileClaims(BaseModel):
    """
    Claims for Vehicle Profile Credential
    Contains static vehicle characteristics
    """
    vehicle_id: str = Field(..., description="Internal vehicle identifier")
    battery_capacity_kwh: float = Field(..., gt=0, description="Battery capacity in kWh")
    nominal_consumption_wh_per_km: float = Field(..., gt=0, description="Energy consumption in Wh/km")
    max_charge_power_kw: float = Field(..., gt=0, description="Maximum charging power in kW")
    fleet_id: Optional[str] = Field(None, description="Fleet ID if part of fleet")
    company_id: Optional[str] = Field(None, description="Owner company ID")
    vehicle_type: str = Field(default="EV", description="EV, PHEV, etc.")
    issued_at: datetime = Field(default_factory=datetime.utcnow)


class ChargerSiteCredentialClaims(BaseModel):
    """
    Claims for Charger/Site Credential
    Proves charger is authorized and registered
    """
    charger_id: str = Field(..., description="Internal charger identifier")
    site_id: str = Field(..., description="Site identifier")
    location_lat: float = Field(..., description="Latitude")
    location_lon: float = Field(..., description="Longitude")
    max_power_kw: float = Field(..., gt=0, description="Maximum power output")
    tariff_group: str = Field(default="standard", description="Pricing tier: standard, premium, fleet")
    operator_id: str = Field(..., description="Charging network operator ID")
    issued_at: datetime = Field(default_factory=datetime.utcnow)


class PriorityChargingSlotClaims(BaseModel):
    """
    Claims for Priority Charging Slot Credential
    Issued by fleet/employer for urgent trips
    This is the innovative twist - guarantees charging even during peak demand
    """
    driver_id: str = Field(..., description="Driver this slot is issued to")
    site_id: str = Field(..., description="Site where priority applies")
    valid_from: datetime = Field(..., description="Slot becomes valid")
    valid_to: datetime = Field(..., description="Slot expires")
    max_energy_kwh: float = Field(..., gt=0, description="Maximum guaranteed energy")
    reason: str = Field(..., description="e.g. critical_trip, long_distance, urgent_delivery")
    issued_by: str = Field(..., description="Fleet manager or employer DID")
    issued_at: datetime = Field(default_factory=datetime.utcnow)


class IssueCredentialRequest(BaseModel):
    """
    Request to Denso DID Gateway to issue a credential
    """
    credential_type: str = Field(..., description="Type of credential to issue")
    subject_did: str = Field(..., description="DID of the subject (who receives this credential)")
    claims: dict = Field(..., description="Claims to include in the credential")
    issuer_did: Optional[str] = Field(None, description="DID of the issuer (defaults to system)")


class RequestPresentationRequest(BaseModel):
    """
    Request to Denso DID Gateway to get a verifiable presentation
    """
    holder_did: str = Field(..., description="DID of the holder (wallet owner)")
    requested_credentials: List[str] = Field(..., description="List of credential types requested")
    verifier_did: str = Field(..., description="DID of the verifier (your backend)")
    context: Optional[dict] = Field(None, description="Additional context for presentation")


class VerifiableCredential(BaseModel):
    """
    Response from Gateway after issuing a credential
    """
    credential_id: str
    credential_type: str
    subject_did: str
    issuer_did: str
    claims: dict
    proof: dict  # Cryptographic proof
    issued_at: datetime
    expires_at: Optional[datetime]


class VerifiablePresentation(BaseModel):
    """
    Response from Gateway when requesting presentation
    Contains multiple verified credentials
    """
    presentation_id: str
    holder_did: str
    credentials: List[VerifiableCredential]
    proof: dict  # Cryptographic proof of presentation
    presented_at: datetime

