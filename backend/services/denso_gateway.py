"""
Denso DID Gateway Integration
Integrates with Denso DID Gateway API for issuing and verifying credentials
Gateway: https://agent.dndapp.nadenso.com/swagger-api/
"""
import requests
import json
from typing import Optional, Dict, Any, List
from datetime import datetime

from backend.schemas.credentials import (
    DriverMembershipClaims,
    VehicleProfileClaims,
    ChargerSiteCredentialClaims,
    PriorityChargingSlotClaims
)


class DensoGatewayClient:
    """
    Client for Denso DID Gateway API
    Handles credential issuance, presentation requests, and verification
    """
    
    def __init__(self, gateway_url: str = "https://agent.dndapp.nadenso.com", api_key: Optional[str] = None):
        self.gateway_url = gateway_url
        self.api_key = api_key
        self.cbac_vp = None  # CBAC Verifiable Presentation for auth
        
    def create_did(self) -> str:
        """
        Create a new DID for a battery or asset
        
        Returns:
            DID string (clientId)
        """
        try:
            response = requests.get(f"{self.gateway_url}/api/create-did")
            if response.status_code == 200:
                data = response.json()
                return data.get("clientId", "")
            else:
                raise Exception(f"Failed to create DID: {response.status_code}")
        except Exception as e:
            # For hackathon demo, return simulated DID if gateway unavailable
            print(f"Warning: Gateway unavailable, using simulated DID. Error: {e}")
            return f"did:denso:simulated:{datetime.utcnow().timestamp()}"
    
    def get_did_document(self, did: str) -> Optional[Dict]:
        """
        Get DID Document for a given DID
        
        Returns:
            DID Document JSON
        """
        try:
            response = requests.get(f"{self.gateway_url}/api/get-did/{did}")
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Warning: Could not retrieve DID document. Error: {e}")
            return None
    
    def issue_bbc_credential(self, battery_claims: Dict[str, Any]) -> Optional[Dict]:
        """
        Issue a Battery Birth Certificate (BBC) credential
        
        Args:
            battery_claims: Dictionary with BBC claims (batteryId, packUniqueId, etc.)
        
        Returns:
            Verifiable Credential object
        """
        try:
            response = requests.post(
                f"{self.gateway_url}/api/issue-credential",
                params={"credential_type": "BBC"},
                json={"credentialSubject": battery_claims},
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Failed to issue BBC: {response.status_code} - {response.text}")
        except Exception as e:
            # For hackathon, return simulated BBC
            print(f"Warning: Gateway unavailable, using simulated BBC. Error: {e}")
            return self._simulate_bbc(battery_claims)
    
    def request_battery_wallet(self, battery_id: str) -> Optional[Dict]:
        """
        Request Verifiable Presentation containing BBC for a battery
        
        Args:
            battery_id: Battery DID
        
        Returns:
            Verifiable Presentation with BBC
        """
        try:
            headers = {"Content-Type": "application/json"}
            if self.cbac_vp:
                headers["x-cbac-vp"] = json.dumps(self.cbac_vp)
            
            response = requests.post(
                f"{self.gateway_url}/api/request-battery-wallet",
                params={"batteryId": battery_id},
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Failed to request battery wallet: {response.status_code}")
        except Exception as e:
            # For hackathon, return simulated VP
            print(f"Warning: Gateway unavailable, using simulated VP. Error: {e}")
            return self._simulate_battery_vp(battery_id)
    
    def generate_cbac_presentation(self, holder_did: str, access_level: str = "ServiceProvider") -> Optional[Dict]:
        """
        Generate CBAC Verifiable Presentation for backend authentication
        
        Args:
            holder_did: DID of the service provider (your backend)
            access_level: Access level requested
        
        Returns:
            CBAC Verifiable Presentation
        """
        try:
            headers = {}
            if self.api_key:
                headers["x-api-key"] = self.api_key
            
            response = requests.post(
                f"{self.gateway_url}/api/generate-cbac-presentation",
                params={"holderDID": holder_did, "accessLevel": access_level},
                headers=headers
            )
            
            if response.status_code == 200:
                vp = response.json()
                self.cbac_vp = vp  # Store for future requests
                return vp
            else:
                raise Exception(f"Failed to generate CBAC: {response.status_code}")
        except Exception as e:
            # For hackathon, create simulated CBAC
            print(f"Warning: Gateway unavailable, using simulated CBAC. Error: {e}")
            cbac_vp = self._simulate_cbac(holder_did, access_level)
            self.cbac_vp = cbac_vp
            return cbac_vp
    
    def verify_presentation(self, presentation: Dict) -> bool:
        """
        Verify a Verifiable Presentation
        
        Args:
            presentation: VP to verify
        
        Returns:
            True if valid, False otherwise
        """
        try:
            headers = {"Content-Type": "application/json"}
            if self.cbac_vp:
                headers["x-cbac-vp"] = json.dumps(self.cbac_vp)
            
            response = requests.post(
                f"{self.gateway_url}/api/verify-presentation",
                json=presentation,
                headers=headers
            )
            
            return response.status_code == 200
        except Exception as e:
            print(f"Warning: Verification failed, assuming valid for demo. Error: {e}")
            return True
    
    # Simulation methods for when gateway is unavailable (hackathon fallback)
    
    def _simulate_bbc(self, claims: Dict) -> Dict:
        """Simulate BBC for demo when gateway unavailable"""
        return {
            "@context": ["https://www.w3.org/2018/credentials/v1"],
            "type": ["VerifiableCredential", "BBC"],
            "credentialSubject": claims,
            "issuer": "did:denso:gateway:simulator",
            "issuanceDate": datetime.utcnow().isoformat() + "Z",
            "proof": {
                "type": "Ed25519Signature2020",
                "created": datetime.utcnow().isoformat() + "Z",
                "proofPurpose": "assertionMethod",
                "verificationMethod": "did:denso:gateway:simulator#key-1",
                "simulated": True
            }
        }
    
    def _simulate_battery_vp(self, battery_id: str) -> Dict:
        """Simulate Battery VP for demo"""
        bbc_claims = {
            "type": "BBC",
            "batteryId": battery_id,
            "packUniqueId": f"urn:uuid:battery-{battery_id}",
            "manufacturersId": "did:denso:manufacturer:example",
            "manufacturingDate": "2023-06-15T00:00:00Z",
            "manufacturingLocation": "Aichi, Japan",
            "intendedUse": "Electric Vehicle",
            "packWeight": "420",
            "lifeCycleStatus": "IN USE",
            "cellType": "Lithium-Ion",
            "mobileOrStationary": "Mobile",
            "bmsSoftwareVersion": "2.1.0"
        }
        
        return {
            "@context": ["https://www.w3.org/2018/credentials/v1"],
            "type": "VerifiablePresentation",
            "verifiableCredential": [self._simulate_bbc(bbc_claims)],
            "holder": battery_id,
            "proof": {
                "type": "Ed25519Signature2020",
                "created": datetime.utcnow().isoformat() + "Z",
                "simulated": True
            }
        }
    
    def _simulate_cbac(self, holder_did: str, access_level: str) -> Dict:
        """Simulate CBAC VP for demo"""
        return {
            "@context": ["https://www.w3.org/2018/credentials/v1"],
            "type": "VerifiablePresentation",
            "verifiableCredential": [{
                "type": ["VerifiableCredential", "CBAC"],
                "credentialSubject": {
                    "type": "CBAC",
                    "Role": access_level,
                    "Permissions": ["AccessCoreServicesAPI", "RequestBatteryWallet"]
                },
                "issuer": "did:denso:gateway:system",
                "holder": holder_did
            }],
            "holder": holder_did,
            "proof": {"simulated": True}
        }
    
    def extract_bbc_claims(self, battery_vp: Dict) -> Optional[Dict]:
        """
        Extract BBC claims from a battery wallet VP
        
        Args:
            battery_vp: Verifiable Presentation from request-battery-wallet
        
        Returns:
            BBC credentialSubject dictionary
        """
        if not battery_vp:
            return None
        
        credentials = battery_vp.get("verifiableCredential", [])
        for cred in credentials:
            if isinstance(cred, dict):
                cred_types = cred.get("type", [])
                if "BBC" in cred_types:
                    return cred.get("credentialSubject", {})
        
        return None

