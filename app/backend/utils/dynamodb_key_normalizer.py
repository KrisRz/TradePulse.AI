"""
DynamoDB Key Type Normalizer - TradePulse.AI
===========================================

Utility to ensure proper key types for DynamoDB operations
and prevent "Type mismatch for key" errors.

Author: TradePulse.AI Development Team
Created: January 2025
Version: 1.0.0
"""

import logging
from typing import Dict, Any, Union
from datetime import datetime, timezone
from decimal import Decimal

logger = logging.getLogger(__name__)

# Table key schemas - defines expected types for each table's keys
TABLE_KEY_SCHEMAS = {
    "trading_decisions": {
        "decision_id": "S",  # String (HASH key: decision_YYYYMMDD_HHMMSS_uuid)
        "timestamp": "N"  # Number (RANGE key: epoch timestamp)
    },
    "tradepulse_market_data": {
        "symbol": "S",  # String (HASH key)
        "timestamp": "N"  # Number (RANGE key: epoch timestamp)
    },
    "live_candles": {
        "symbol": "S",  # String
        "timestamp": "N"  # Number (consistent with Terraform)
    },
    "tradepulse-live_candles-production": {
        "symbol": "S",  # String
        "timestamp": "N"  # Number (to match Terraform table definition)
    },
    "emergency_state": {
        "id": "S"  # String
    },
    "virtual_positions": {
        "user_id": "S",  # String
        "position_id": "S"  # String
    },
    "virtual_trades": {
        "user_id": "S",  # String
        "trade_id": "S"  # String
    },
    "learning_engine_state": {
        "engine_id": "S"  # String
    }
}

def normalize_dynamodb_item(table_name: str, item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize DynamoDB item to ensure proper key types
    
    Args:
        table_name: Name of the DynamoDB table
        item: Item data to normalize
        
    Returns:
        Dict with properly typed keys
    """
    if table_name not in TABLE_KEY_SCHEMAS:
        logger.warning(f"🔄 PIPELINE DEBUG: Unknown table schema for {table_name}, skipping normalization")
        return item
    
    normalized_item = item.copy()
    key_schema = TABLE_KEY_SCHEMAS[table_name]
    
    for key_name, expected_type in key_schema.items():
        if key_name in normalized_item:
            original_value = normalized_item[key_name]
            
            try:
                if expected_type == "S":
                    # Ensure string type
                    normalized_item[key_name] = str(original_value)
                elif expected_type == "N":
                    # Ensure number type (use Decimal for DynamoDB)
                    if isinstance(original_value, (int, float)):
                        normalized_item[key_name] = Decimal(str(original_value))
                    elif isinstance(original_value, str):
                        normalized_item[key_name] = Decimal(original_value)
                    else:
                        normalized_item[key_name] = Decimal(str(original_value))
                        
                logger.debug(f"🔄 PIPELINE DEBUG: Normalized {key_name}: {type(original_value).__name__} -> {expected_type}")
                
            except Exception as e:
                logger.error(f"💥 PIPELINE DEBUG: Failed to normalize {key_name} for table {table_name}: {e}")
                # Keep original value if normalization fails
                normalized_item[key_name] = original_value
    
    return normalized_item

def validate_item_before_write(table_name: str, item: Dict[str, Any]) -> bool:
    """
    Validate item has correct key types before DynamoDB write
    
    Args:
        table_name: Name of the DynamoDB table
        item: Item data to validate
        
    Returns:
        bool: True if valid, False if validation failed
    """
    if table_name not in TABLE_KEY_SCHEMAS:
        logger.debug(f"🔄 PIPELINE DEBUG: No schema validation for {table_name}")
        return True
    
    key_schema = TABLE_KEY_SCHEMAS[table_name]
    
    for key_name, expected_type in key_schema.items():
        if key_name not in item:
            logger.error(f"💥 PIPELINE DEBUG: Missing required key {key_name} for table {table_name}")
            return False
        
        value = item[key_name]
        
        if expected_type == "S" and not isinstance(value, str):
            logger.error(f"💥 PIPELINE DEBUG: Key {key_name} should be string, got {type(value).__name__}")
            return False
        elif expected_type == "N" and not isinstance(value, (int, float, Decimal)):
            logger.error(f"💥 PIPELINE DEBUG: Key {key_name} should be number, got {type(value).__name__}")
            return False
    
    logger.debug(f"✅ PIPELINE DEBUG: Item validation passed for {table_name}")
    return True

def safe_put_item(table, item: Dict[str, Any], table_name: str = None, **kwargs) -> bool:
    """
    Safe wrapper for DynamoDB put_item with automatic key normalization
    
    Args:
        table: DynamoDB table resource
        item: Item to write
        table_name: Table name for normalization (optional)
        **kwargs: Additional arguments for put_item
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get table name if not provided
        if table_name is None:
            table_name = table.name
        
        # Normalize item keys
        normalized_item = normalize_dynamodb_item(table_name, item)
        
        # Validate before write
        if not validate_item_before_write(table_name, normalized_item):
            logger.error(f"💥 PIPELINE DEBUG: Item validation failed for {table_name}")
            return False
        
        # Perform the write
        table.put_item(Item=normalized_item, **kwargs)
        logger.debug(f"✅ PIPELINE DEBUG: Successfully wrote item to {table_name}")
        return True
        
    except Exception as e:
        logger.error(f"💥 PIPELINE DEBUG: Failed to write to {table_name}: {e}")
        return False
