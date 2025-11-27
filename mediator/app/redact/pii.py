"""PII redaction using Presidio and custom rules."""

import re
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class PIIRedactor:
    """Handles PII detection and redaction."""
    
    def __init__(self):
        self.redaction_patterns = {
            'mask_emails': (
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                '[EMAIL]'
            ),
            'drop_phone': (
                r'(\+?[1-9]\d{0,2}[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}',
                '[PHONE]'
            ),
            'drop_exact_address': (
                r'\d+\s+[\w\s]+(?:street|st|avenue|ave|road|rd|highway|hwy|lane|ln|drive|dr|court|ct|circle|cir|boulevard|blvd)\b',
                '[ADDRESS]'
            ),
            'mask_ssn': (
                r'\b\d{3}-\d{2}-\d{4}\b',
                '[SSN]'
            ),
            'mask_credit_card': (
                r'\b(?:\d{4}[\s-]?){3}\d{4}\b',
                '[CREDIT_CARD]'
            ),
            'mask_ip': (
                r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
                '[IP_ADDRESS]'
            ),
        }
        
        self.presidio_analyzer = None
        self.presidio_anonymizer = None
        self._init_presidio()
    
    def _init_presidio(self) -> None:
        """Initialize Presidio if available."""
        try:
            from presidio_analyzer import AnalyzerEngine
            from presidio_anonymizer import AnonymizerEngine
            
            self.presidio_analyzer = AnalyzerEngine()
            self.presidio_anonymizer = AnonymizerEngine()
            logger.info("Presidio initialized successfully")
        except ImportError:
            logger.warning("Presidio not available, using regex-based redaction only")
    
    async def redact(
        self,
        text: str,
        profile: str,
        redaction_rules: List[str],
    ) -> str:
        """Apply redaction rules to text based on profile."""
        if not text:
            return text
        
        redacted_text = text
        
        # Apply regex-based redaction rules
        for rule in redaction_rules:
            if rule in self.redaction_patterns:
                pattern, replacement = self.redaction_patterns[rule]
                redacted_text = re.sub(pattern, replacement, redacted_text, flags=re.IGNORECASE)
        
        # Apply Presidio if available and requested
        if self.presidio_analyzer and 'presidio_full' in redaction_rules:
            redacted_text = self._presidio_redact(redacted_text)
        
        # Apply custom masking for specific profiles
        if profile == 'work':
            # Mask personal details but keep professional info
            redacted_text = self._mask_personal_details(redacted_text)
        elif profile == 'public':
            # Maximum redaction for public profiles
            redacted_text = self._maximum_redaction(redacted_text)
        
        return redacted_text
    
    def _presidio_redact(self, text: str) -> str:
        """Use Presidio for advanced PII detection."""
        try:
            # Analyze text for PII
            results = self.presidio_analyzer.analyze(
                text=text,
                language='en',
                entities_to_recognize=[
                    "PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER",
                    "US_SSN", "CREDIT_CARD", "LOCATION",
                ],
            )
            
            # Anonymize detected PII
            anonymized = self.presidio_anonymizer.anonymize(
                text=text,
                analyzer_results=results,
            )
            
            return anonymized.text
            
        except Exception as e:
            logger.error(f"Presidio redaction failed: {e}")
            return text
    
    def _mask_personal_details(self, text: str) -> str:
        """Mask personal details while keeping professional info."""
        # Mask dates of birth
        text = re.sub(
            r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',
            '[DATE]',
            text,
            flags=re.IGNORECASE
        )
        
        # Mask age references
        text = re.sub(r'\b\d{1,2}\s+years?\s+old\b', '[AGE]', text, flags=re.IGNORECASE)
        
        # Mask family references
        text = re.sub(
            r'\b(?:wife|husband|spouse|partner|child|children|son|daughter|mother|father|parent)\b',
            '[FAMILY]',
            text,
            flags=re.IGNORECASE
        )
        
        return text
    
    def _maximum_redaction(self, text: str) -> str:
        """Apply maximum redaction for public profiles."""
        # Redact all numbers
        text = re.sub(r'\b\d+\b', '[NUMBER]', text)
        
        # Redact all proper nouns (simple heuristic)
        text = re.sub(r'\b[A-Z][a-z]+\b', '[NAME]', text)
        
        # Redact URLs
        text = re.sub(
            r'https?://[^\s]+',
            '[URL]',
            text,
            flags=re.IGNORECASE
        )
        
        return text
    
    def get_available_rules(self) -> List[str]:
        """Get list of available redaction rules."""
        rules = list(self.redaction_patterns.keys())
        if self.presidio_analyzer:
            rules.append('presidio_full')
        return rules