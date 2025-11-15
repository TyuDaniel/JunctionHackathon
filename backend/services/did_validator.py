"""
DID Validator
Simulates DID-based access control and credential verification
In production, this would integrate with actual DID verification libraries
"""
from typing import Tuple
from backend.schemas.did import DriverDID, VehicleDID, ChargerDID


def validate_did_access(
    driver: DriverDID,
    vehicle: VehicleDID,
    charger: ChargerDID
) -> Tuple[bool, str]:
    """
    Validate that the driver has access to charge this vehicle at this charger
    
    Returns:
        (is_valid, message)
    """
    
    # Check 1: Driver must have valid DID
    if not driver.did or not driver.did.startswith("did:denso:driver:"):
        return False, "Invalid driver DID format"
    
    # Check 2: Vehicle must have valid DID
    if not vehicle.did or not vehicle.did.startswith("did:denso:vehicle:"):
        return False, "Invalid vehicle DID format"
    
    # Check 3: Charger must have valid DID
    if not charger.did or not charger.did.startswith("did:denso:charger:"):
        return False, "Invalid charger DID format"
    
    # Check 4: Driver must be allowed at this site
    if charger.site_id not in driver.allowed_sites and len(driver.allowed_sites) > 0:
        return False, f"Driver not authorized to charge at site {charger.site_id}"
    
    # Check 5: Charger must be available
    if not charger.current_availability:
        return False, "Charger is currently unavailable"
    
    # Check 6: Vehicle battery state must be valid
    if not (0 <= vehicle.current_soc_percent <= 100):
        return False, "Invalid vehicle state of charge"
    
    if vehicle.battery_capacity_kwh <= 0:
        return False, "Invalid battery capacity"
    
    # All checks passed
    return True, "Access granted - all DID credentials verified"


def extract_credentials(driver: DriverDID) -> dict:
    """
    Extract and parse driver credentials
    Returns a dictionary of credential types and values
    """
    credentials_dict = {}
    
    for cred in driver.credentials:
        if ":" in cred:
            cred_type, cred_value = cred.split(":", 1)
            credentials_dict[cred_type] = cred_value
    
    return credentials_dict

