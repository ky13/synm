"""Tests for PII redaction."""

import pytest
from app.redact.pii import PIIRedactor


@pytest.fixture
def redactor():
    """Create PIIRedactor instance."""
    return PIIRedactor()


def test_email_redaction(redactor):
    """Test email address redaction."""
    text = "Contact me at user@example.com for more info."
    result = redactor.redact(text, "work", ["mask_emails"])
    assert "[EMAIL]" in result
    assert "user@example.com" not in result


def test_phone_redaction(redactor):
    """Test phone number redaction."""
    text = "Call me at (555) 123-4567 or 555-987-6543."
    result = redactor.redact(text, "work", ["drop_phone"])
    assert "[PHONE]" in result
    assert "555-123-4567" not in result


def test_address_redaction(redactor):
    """Test address redaction."""
    text = "I live at 123 Main Street in downtown."
    result = redactor.redact(text, "work", ["drop_exact_address"])
    assert "[ADDRESS]" in result
    assert "123 Main Street" not in result


def test_multiple_redactions(redactor):
    """Test multiple redaction rules."""
    text = "Contact John at john@example.com or call (555) 123-4567."
    result = redactor.redact(text, "work", ["mask_emails", "drop_phone"])
    assert "[EMAIL]" in result
    assert "[PHONE]" in result
    assert "john@example.com" not in result
    assert "555-123-4567" not in result


def test_no_redaction(redactor):
    """Test text with no PII."""
    text = "This is a clean text with no sensitive information."
    result = redactor.redact(text, "work", ["mask_emails", "drop_phone"])
    assert result == text


def test_work_profile_redaction(redactor):
    """Test work profile specific redaction."""
    text = "John is 30 years old and his wife Sarah works here."
    result = redactor.redact(text, "work", [])
    # Work profile should mask personal details
    assert "[AGE]" in result or "[FAMILY]" in result


def test_public_profile_redaction(redactor):
    """Test public profile maximum redaction."""
    text = "John Smith works at Company Inc with 5 years experience."
    result = redactor.redact(text, "public", [])
    # Public profile should apply maximum redaction
    assert "[NAME]" in result or "[NUMBER]" in result