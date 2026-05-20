import time
import hashlib
import asyncio
import os
from fastapi import Security, HTTPException, status, Depends
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import load_der_public_key
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from cryptography.exceptions import InvalidSignature

from src.database import get_db
import src.models as models
import src.schemas as schemas

# --- CONFIGURATION ---
IOT_API_KEY = os.getenv("IOT_API_KEY")

# Define the Security Scheme for Swagger UI
api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)
if not IOT_API_KEY:
    raise RuntimeError("🚨 CRITICAL STARTUP ERROR: 'IOT_API_KEY' environment variable is not set!")

def verify_api_key(api_key: str = Security(api_key_scheme)):
    """Dependency that checks the API Key and throws a 401 if invalid."""
    if not api_key or api_key != IOT_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Invalid or missing X-API-Key header"
        )
    return api_key

def verify_device_signature(public_key_hex: str, message: str, signature_hex: str) -> bool:
    """Validates the ECDSA signature from the IoT device using the cryptography library."""
    if not public_key_hex or not signature_hex:
        return False
        
    try:
        key_bytes = bytes.fromhex(public_key_hex)
        sig_bytes = bytes.fromhex(signature_hex)
        message_bytes = message.encode('utf-8')

        # 1. Load the Public Key (Handle DER vs Raw String)
        try:
            public_key = load_der_public_key(key_bytes)
        except ValueError:
            # Fallback for older sensors: Raw uncompressed 64-byte point
            if len(key_bytes) == 64:
                key_bytes = b'\x04' + key_bytes # Prepend standard uncompressed marker
            public_key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), key_bytes)
        
        # 2. Verify the Signature (Handle DER vs Raw String)
        try:
            # Try standard DER encoded signature
            public_key.verify(sig_bytes, message_bytes, ec.ECDSA(hashes.SHA256()))
            return True
        except (InvalidSignature, Exception):
            pass
            
        # Fallback for older sensors: Try Raw Signature (r || s)
        if len(sig_bytes) == 64:
            r = int.from_bytes(sig_bytes[:32], 'big')
            s = int.from_bytes(sig_bytes[32:], 'big')
            der_sig = encode_dss_signature(r, s) # Convert raw to DER
            try:
                public_key.verify(der_sig, message_bytes, ec.ECDSA(hashes.SHA256()))
                return True
            except InvalidSignature:
                return False
                
    except Exception:
        return False
        
    return False

async def validate_iot_payload(
    misuration: schemas.MisurationCreate,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """
    Dependency that performs complete business-logic validation:
    1. Validates the API Key.
    2. Validates the Sensor exists and is active.
    3. Prevents Replay Attacks.
    4. Verifies the ECDSA Digital Signature.
    """
    misurator = db.query(models.Misurator).filter(models.Misurator.id == misuration.misurator_id).first()
    if not misurator or not misurator.active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sensor unauthorized")

    # Check Replay Attack
    if abs(time.time() - misuration.device_timestamp) > 60:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Replay Attack Detected: Timestamp invalid")

    # Verify Signature
    message = f"{misuration.value}:{int(misuration.device_timestamp)}"
    loop = asyncio.get_running_loop()
    is_valid = await loop.run_in_executor(None, verify_device_signature, misurator.public_key_hex, message, misuration.signature_hex)

    if not is_valid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid digital signature")

    # If everything is valid, return the data so the endpoint can use it!
    return {"misurator": misurator, "misuration": misuration}