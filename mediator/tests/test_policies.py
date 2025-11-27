"""Tests for policy engine."""

import pytest
import tempfile
from pathlib import Path
import yaml

from app.policies.engine import PolicyEngine


@pytest.fixture
def temp_policy_dir():
    """Create temporary policy directory with test policies."""
    with tempfile.TemporaryDirectory() as temp_dir:
        policy_dir = Path(temp_dir)
        
        # Create test policy file
        test_policy = {
            "profiles": {
                "test_profile": {
                    "allowed_scopes": ["test.scope1", "test.scope2"],
                    "redactions": ["mask_emails", "drop_phone"],
                },
                "restricted_profile": {
                    "allowed_scopes": ["test.scope1"],
                    "redactions": ["mask_all"],
                },
            },
            "scopes": {
                "test.scope1": {
                    "includes": ["notes/test1.md"],
                },
                "test.scope2": {
                    "query": "type:test",
                },
            },
            "defaults": {
                "ttl_minutes": 15,
            },
        }
        
        policy_file = policy_dir / "test.yaml"
        with open(policy_file, 'w') as f:
            yaml.dump(test_policy, f)
        
        yield policy_dir


def test_policy_loading(temp_policy_dir):
    """Test policy loading from directory."""
    engine = PolicyEngine(str(temp_policy_dir))
    engine.load_policies()
    
    assert "test_profile" in engine.profiles
    assert "restricted_profile" in engine.profiles
    assert "test.scope1" in engine.scopes
    assert "test.scope2" in engine.scopes
    assert engine.defaults["ttl_minutes"] == 15


def test_check_access_allowed(temp_policy_dir):
    """Test access check for allowed scopes."""
    engine = PolicyEngine(str(temp_policy_dir))
    engine.load_policies()
    
    # Should allow access to permitted scopes
    assert engine.check_access("test_profile", ["test.scope1"]) is True
    assert engine.check_access("test_profile", ["test.scope1", "test.scope2"]) is True


def test_check_access_denied(temp_policy_dir):
    """Test access check for denied scopes."""
    engine = PolicyEngine(str(temp_policy_dir))
    engine.load_policies()
    
    # Should deny access to unpermitted scopes
    assert engine.check_access("restricted_profile", ["test.scope2"]) is False
    assert engine.check_access("test_profile", ["forbidden.scope"]) is False
    assert engine.check_access("nonexistent_profile", ["test.scope1"]) is False


def test_get_redaction_rules(temp_policy_dir):
    """Test redaction rules retrieval."""
    engine = PolicyEngine(str(temp_policy_dir))
    engine.load_policies()
    
    rules = engine.get_redaction_rules("test_profile")
    assert "mask_emails" in rules
    assert "drop_phone" in rules
    
    restricted_rules = engine.get_redaction_rules("restricted_profile")
    assert "mask_all" in restricted_rules


def test_get_scope_config(temp_policy_dir):
    """Test scope configuration retrieval."""
    engine = PolicyEngine(str(temp_policy_dir))
    engine.load_policies()
    
    scope_config = engine.get_scope_config("test.scope1")
    assert scope_config is not None
    assert "includes" in scope_config
    assert "notes/test1.md" in scope_config["includes"]