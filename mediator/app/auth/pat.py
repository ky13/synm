"""Personal Access Token (PAT) authentication."""

import os
import hashlib
import hmac
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def verify_pat(token: str) -> bool:
    """Verify a Personal Access Token."""
    if not token:
        return False
    
    # Get expected PAT from environment
    expected_pat = os.getenv("MEDIATOR_PAT", "")
    
    if not expected_pat:
        logger.warning("MEDIATOR_PAT not configured, rejecting all requests")
        return False
    
    # Use constant-time comparison to prevent timing attacks
    return hmac.compare_digest(token, expected_pat)


def hash_token(token: str) -> str:
    """Hash a token for storage."""
    salt = os.getenv("API_KEY_SALT", "default-salt")
    return hashlib.pbkdf2_hmac('sha256', token.encode(), salt.encode(), 100000).hex()


class MTLSAuth:
    """mTLS authentication handler (placeholder for future implementation)."""
    
    def __init__(self):
        self.enabled = os.getenv("MTLS_ENABLED", "false").lower() == "true"
        self.ca_file = os.getenv("MTLS_CA_FILE", "./certs/ca.crt")
        self.cert_file = os.getenv("TLS_CERT_FILE", "./certs/server.crt")
        self.key_file = os.getenv("TLS_KEY_FILE", "./certs/server.key")
    
    def verify_client_cert(self, cert_data: Optional[str]) -> bool:
        """Verify client certificate for mTLS."""
        if not self.enabled:
            return True  # mTLS disabled, allow all
        
        if not cert_data:
            logger.warning("mTLS enabled but no client certificate provided")
            return False
        
        # TODO: Implement actual certificate verification
        # This would involve:
        # 1. Parsing the certificate
        # 2. Verifying it against the CA
        # 3. Checking validity dates
        # 4. Checking revocation status
        
        logger.info("mTLS verification placeholder - would verify cert here")
        return True
    
    def get_client_identity(self, cert_data: Optional[str]) -> Optional[str]:
        """Extract client identity from certificate."""
        if not cert_data:
            return None
        
        # TODO: Extract CN or SAN from certificate
        return "client-identity-placeholder"