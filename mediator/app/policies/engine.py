"""Policy engine for access control and redaction rules."""

import os
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
import yaml

logger = logging.getLogger(__name__)


class PolicyEngine:
    """Manages access policies and redaction rules."""
    
    def __init__(self, policy_dir: str = "app/policies"):
        self.policy_dir = Path(policy_dir)
        self.policies: Dict[str, Any] = {}
        self.profiles: Dict[str, Any] = {}
        self.scopes: Dict[str, Any] = {}
        self.defaults: Dict[str, Any] = {}
    
    def load_policies(self) -> None:
        """Load all policy files from the policy directory."""
        if not self.policy_dir.exists():
            logger.warning(f"Policy directory {self.policy_dir} does not exist")
            return
        
        for policy_file in self.policy_dir.glob("*.yaml"):
            try:
                with open(policy_file, 'r') as f:
                    policy_data = yaml.safe_load(f)
                    
                if policy_data:
                    # Merge profiles
                    if 'profiles' in policy_data:
                        self.profiles.update(policy_data['profiles'])
                    
                    # Merge scopes
                    if 'scopes' in policy_data:
                        self.scopes.update(policy_data['scopes'])
                    
                    # Update defaults
                    if 'defaults' in policy_data:
                        self.defaults.update(policy_data['defaults'])
                    
                    logger.info(f"Loaded policy file: {policy_file.name}")
                    
            except Exception as e:
                logger.error(f"Failed to load policy file {policy_file}: {e}")
    
    def check_access(self, profile: str, requested_scopes: List[str]) -> bool:
        """Check if a profile has access to the requested scopes."""
        if profile not in self.profiles:
            logger.warning(f"Unknown profile: {profile}")
            return False
        
        profile_config = self.profiles[profile]
        allowed_scopes = profile_config.get('allowed_scopes', [])
        
        # Check if all requested scopes are allowed
        for scope in requested_scopes:
            if scope not in allowed_scopes:
                logger.info(f"Profile {profile} denied access to scope {scope}")
                return False
        
        return True
    
    def get_redaction_rules(self, profile: str) -> List[str]:
        """Get redaction rules for a profile."""
        if profile not in self.profiles:
            return ['mask_all']  # Default to maximum redaction
        
        return self.profiles[profile].get('redactions', [])
    
    def get_scope_config(self, scope: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific scope."""
        return self.scopes.get(scope)
    
    def get_default_ttl(self) -> int:
        """Get default TTL in minutes."""
        return self.defaults.get('ttl_minutes', 20)
    
    def get_allowed_profiles(self) -> List[str]:
        """Get list of all configured profiles."""
        return list(self.profiles.keys())
    
    def get_allowed_scopes(self, profile: str) -> List[str]:
        """Get allowed scopes for a profile."""
        if profile not in self.profiles:
            return []
        
        return self.profiles[profile].get('allowed_scopes', [])