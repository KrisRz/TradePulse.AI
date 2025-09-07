"""
Log filtering utilities for TradePulse.AI
Filters sensitive information from logs in production environments
"""

import logging
import re
from typing import Any, Dict, List, Optional
from app.backend.core.config import get_settings

# Sensitive patterns to redact in logs
SENSITIVE_PATTERNS = [
    # AWS V4 Signatures
    (r'Signature=[a-f0-9]{64}', 'Signature=***REDACTED***'),
    (r'Authorization: AWS4-HMAC-SHA256[^,]*Signature=[a-f0-9]{64}', 'Authorization: AWS4-HMAC-SHA256 ***REDACTED***'),
    
    # AWS Credentials
    (r'aws_access_key_id=[A-Z0-9]{20}', 'aws_access_key_id=***REDACTED***'),
    (r'aws_secret_access_key=[A-Za-z0-9/+=]{40}', 'aws_secret_access_key=***REDACTED***'),
    (r'aws_session_token=[A-Za-z0-9/+=]+', 'aws_session_token=***REDACTED***'),
    
    # API Keys
    (r'api[_-]?key[\'"\s]*[:=][\'"\s]*[A-Za-z0-9]{32,}', 'api_key=***REDACTED***'),
    (r'secret[_-]?key[\'"\s]*[:=][\'"\s]*[A-Za-z0-9]{32,}', 'secret_key=***REDACTED***'),
    
    # DynamoDB Request Details (in development, keep some info; in prod, redact more)
    (r'CanonicalRequest:\n[^\n]*\n[^\n]*\n[^\n]*\n[^\n]*\n[^\n]*\n[^\n]*\n[^\n]*\n[a-f0-9]{64}', 'CanonicalRequest: ***REDACTED***'),
    (r'StringToSign:\n[^\n]*\n[^\n]*\n[^\n]*\n[a-f0-9]{64}', 'StringToSign: ***REDACTED***'),
    
    # Other sensitive data
    (r'password[\'"\s]*[:=][\'"\s]*[^\s\'",]+', 'password=***REDACTED***'),
    (r'token[\'"\s]*[:=][\'"\s]*[A-Za-z0-9._-]{20,}', 'token=***REDACTED***'),
]

# Patterns that are OK in development but should be redacted in production
DEV_ONLY_PATTERNS = [
    (r'X-Amz-Date: \d{8}T\d{6}Z', 'X-Amz-Date: ***REDACTED***'),
    (r'amz-sdk-invocation-id: [a-f0-9-]+', 'amz-sdk-invocation-id: ***REDACTED***'),
]


class SensitiveDataFilter(logging.Filter):
    """
    Logging filter to redact sensitive information from log messages
    """
    
    def __init__(self, name: str = "", redact_in_development: bool = False):
        super().__init__(name)
        self.redact_in_development = redact_in_development
        self.settings = get_settings()
        
        # Compile regex patterns for better performance
        self.patterns = []
        for pattern, replacement in SENSITIVE_PATTERNS:
            self.patterns.append((re.compile(pattern, re.IGNORECASE | re.MULTILINE), replacement))
        
        # Add development-only patterns if not in development or if explicitly requested
        if not self.settings.is_development or redact_in_development:
            for pattern, replacement in DEV_ONLY_PATTERNS:
                self.patterns.append((re.compile(pattern, re.IGNORECASE | re.MULTILINE), replacement))
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter log record to redact sensitive information
        
        Args:
            record: Log record to filter
            
        Returns:
            bool: Always True (don't suppress the log, just modify it)
        """
        try:
            # Redact sensitive data from the message
            if hasattr(record, 'msg') and record.msg:
                record.msg = self._redact_sensitive_data(str(record.msg))
            
            # Redact from args if present
            if hasattr(record, 'args') and record.args:
                record.args = tuple(
                    self._redact_sensitive_data(str(arg)) if isinstance(arg, str) else arg
                    for arg in record.args
                )
            
            return True
            
        except Exception as e:
            # If filtering fails, log the error but don't suppress the original log
            print(f"Log filtering error: {e}")  # Use print to avoid recursion
            return True
    
    def _redact_sensitive_data(self, text: str) -> str:
        """
        Redact sensitive data from text using compiled patterns
        
        Args:
            text: Text to redact
            
        Returns:
            str: Text with sensitive data redacted
        """
        if not text:
            return text
            
        result = text
        for pattern, replacement in self.patterns:
            result = pattern.sub(replacement, result)
        
        return result


class BotocoreLogFilter(logging.Filter):
    """
    Specific filter for botocore logs to reduce noise and redact sensitive AWS data
    """
    
    def __init__(self, name: str = ""):
        super().__init__(name)
        self.settings = get_settings()
        
        # Patterns to suppress entirely in production (too noisy)
        self.suppress_patterns = [
            re.compile(r'Making request for OperationModel', re.IGNORECASE),
            re.compile(r'Calling endpoint provider with parameters', re.IGNORECASE),
            re.compile(r'Event [a-z-]+\.[a-zA-Z]+\.[a-zA-Z]+: calling handler', re.IGNORECASE),
        ] if not self.settings.is_development else []
        
        # Sensitive data filter
        self.sensitive_filter = SensitiveDataFilter()
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter botocore log records
        
        Args:
            record: Log record to filter
            
        Returns:
            bool: True to keep the log, False to suppress it
        """
        try:
            # In production, suppress noisy patterns
            if not self.settings.is_development:
                message = str(record.msg) if record.msg else ""
                for pattern in self.suppress_patterns:
                    if pattern.search(message):
                        return False
            
            # Apply sensitive data filtering
            return self.sensitive_filter.filter(record)
            
        except Exception as e:
            print(f"Botocore log filtering error: {e}")
            return True


def configure_log_filtering():
    """
    Configure log filtering for the application
    Should be called during application startup
    """
    settings = get_settings()
    
    # Add sensitive data filter to root logger
    root_logger = logging.getLogger()
    sensitive_filter = SensitiveDataFilter(redact_in_development=False)
    root_logger.addFilter(sensitive_filter)
    
    # Add specific filter for botocore (AWS SDK) logs
    botocore_logger = logging.getLogger('botocore')
    botocore_filter = BotocoreLogFilter()
    botocore_logger.addFilter(botocore_filter)
    
    # Reduce log level for noisy AWS libraries in production
    if not settings.is_development:
        logging.getLogger('botocore').setLevel(logging.WARNING)
        logging.getLogger('boto3').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('s3transfer').setLevel(logging.WARNING)
    
    # Log the configuration
    logger = logging.getLogger(__name__)
    logger.info("🛡️ Log filtering configured")
    if not settings.is_development:
        logger.info("🔒 Production mode: Enhanced log redaction enabled")
    else:
        logger.info("🔧 Development mode: Minimal log redaction")


def test_log_filtering():
    """
    Test function to verify log filtering is working correctly
    """
    logger = logging.getLogger(__name__)
    
    # Test various sensitive patterns
    test_messages = [
        "Authorization: AWS4-HMAC-SHA256 Credential=dummy/20250907/us-east-1/dynamodb/aws4_request, SignedHeaders=content-type;host;x-amz-date;x-amz-target, Signature=72dc7389535762000209c40e2f5c1f47d8914b151f68a59dd5d1fa15e33edf6c",
        "aws_access_key_id=AKIAIOSFODNN7EXAMPLE",
        "aws_secret_access_key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        "api_key: sk-1234567890abcdef1234567890abcdef",
        "password='super_secret_password_123'",
        "Normal log message without sensitive data"
    ]
    
    logger.info("🧪 Testing log filtering...")
    for i, message in enumerate(test_messages, 1):
        logger.info(f"Test {i}: {message}")
    
    logger.info("✅ Log filtering test complete")


# Convenience function for manual redaction
def redact_sensitive_data(text: str) -> str:
    """
    Manually redact sensitive data from text
    
    Args:
        text: Text to redact
        
    Returns:
        str: Text with sensitive data redacted
    """
    filter_instance = SensitiveDataFilter()
    return filter_instance._redact_sensitive_data(text)
