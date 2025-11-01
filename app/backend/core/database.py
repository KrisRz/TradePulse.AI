"""
Database module for TradePulse.AI
Provides DynamoDB client, schema definitions, and table management
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List, Optional, Union
import json
import os
import boto3
from botocore.exceptions import ClientError, EndpointConnectionError
from botocore.config import Config
import structlog
from dataclasses import dataclass
import logging
from functools import lru_cache

from .config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

@lru_cache(maxsize=1)
def get_dynamodb_singleton():
    """Singleton DynamoDB resource to prevent multiple client creation and ListTables storms"""
    # Get region from environment (defaults to eu-west-2 for production)
    region = os.getenv("DYNAMODB_REGION") or os.getenv("AWS_REGION", "eu-west-2")
    
    cfg = Config(
        retries={"max_attempts": 5, "mode": "standard"},
        connect_timeout=10, 
        read_timeout=30, 
        max_pool_connections=50,
        user_agent_extra="TradePulseAI"
    )
    
    endpoint_url = os.getenv("DYNAMODB_ENDPOINT")
    if endpoint_url:
        logger.info(f"Using DynamoDB Local on {endpoint_url} (region={region}) with optimized connection pooling")
        # FORCE dummy credentials for DynamoDB Local (ignore system AWS credentials)
        return boto3.resource(
            "dynamodb",
            endpoint_url=endpoint_url,
            region_name=region,
            aws_access_key_id="dummy", 
            aws_secret_access_key="dummy",
            aws_session_token=None,  # Explicitly clear session token
            config=cfg
        )
    else:
        # Use system credentials for production AWS with correct region
        logger.info(f"Using AWS DynamoDB in region={region}")
        return boto3.resource("dynamodb", region_name=region, config=cfg)

# Reduce noisy botocore logs for both development and production
for name in ("botocore", "boto3", "urllib3", "s3transfer"):
    logging.getLogger(name).setLevel(logging.WARNING)


class DynamoDBClient:
    """DynamoDB client wrapper for local development and AWS deployment"""
    
    def __init__(self, local_development: Optional[bool] = None):
        if local_development is None:
            # CRITICAL FIX: Use is_development property instead of string comparison
            local_development = settings.is_development
        # Professional connection configuration with optimized pooling
        config = Config(
            max_pool_connections=50,  # Reduce connection resets
            retries={
                'max_attempts': 3,
                'mode': 'standard'
            },
            read_timeout=60,
            connect_timeout=60
        )
        
        # Use singleton DynamoDB resource to prevent multiple client creation
        self.dynamodb = get_dynamodb_singleton()
        
        # Test connection only once during initialization with throttled logging
        if not hasattr(DynamoDBClient, '_connection_verified'):
            try:
                self.dynamodb.meta.client.list_tables()
                logger.info("✅ DynamoDB connection verified")
                DynamoDBClient._connection_verified = True
                DynamoDBClient._logged_verification = True
            except Exception as e:
                logger.error(f"DynamoDB connection failed: {e}")
                
                # In development, NEVER fallback to AWS - force DynamoDB Local usage
                if settings.is_development:
                    logger.error("🚨 DynamoDB Local connection required for development - check if DynamoDB Local is running on port 8000")
                    logger.error("💡 Run: ./start_dynamodb.sh")
                    raise ConnectionError(f"DynamoDB Local required for development but connection failed: {e}")
                else:
                    # Only fallback to AWS in production
                    logger.warning("DynamoDB Local not available, falling back to AWS DynamoDB")
                # Let boto3 use instance role credentials in production
                self.dynamodb = boto3.resource(
                    'dynamodb',
                    region_name=settings.AWS_REGION,
                    config=config
                )
        else:
            # Only log once more instead of spamming
            if not hasattr(DynamoDBClient, '_logged_verification'):
                logger.debug("🔄 DynamoDB connection already verified")
                DynamoDBClient._logged_verification = True
    
    def get_table(self, table_name: str) -> Any:
        """Get a DynamoDB table"""
        try:
            return self.dynamodb.Table(table_name)
        except Exception as e:
            logger.error(f"Error getting table {table_name}: {e}")
            raise
    
    def create_table(self, table_config: Dict[str, Any]) -> bool:
        """Create a DynamoDB table"""
        try:
            table = self.dynamodb.create_table(**table_config)
            table.wait_until_exists()
            logger.info(f"✅ Created table: {table_config['TableName']}")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceInUseException':
                logger.debug(f"✅ Table {table_config['TableName']} already exists")
                return True
            else:
                logger.error(f"❌ Error creating table {table_config['TableName']}: {e}")
                return False
    
    def put_item(self, table_name: str, item: Dict[str, Any]) -> bool:
        """Put an item in DynamoDB table with proper type conversion"""
        try:
            logger.debug(f"🔄 Attempting to save item to table '{table_name}'")
            # Extract ID from various possible fields (or use symbol+timestamp for market data)
            item_id = item.get('id') or item.get('position_id') or item.get('trade_id') or item.get('pk')
            if not item_id and 'symbol' in item and 'timestamp' in item:
                item_id = f"{item['symbol']}@{item['timestamp']}"
            # Emergency events safety: ensure event_id exists and use it as PK surrogate
            if table_name == 'emergency_events':
                import uuid, time as _t
                if not item.get('event_id'):
                    item['event_id'] = str(uuid.uuid4())
                # Provide sortable timestamp if missing
                if not item.get('ts'):
                    item['ts'] = int(_t.time() * 1000)
                item_id = item['event_id']
            item_id = item_id or 'NO_ID'
            logger.debug(f"📝 Item data: {list(item.keys())} - ID: {item_id}")
            
            # Convert numeric values to proper DynamoDB format
            processed_item = self._convert_item_types(item)
            
            table = self.get_table(table_name)
            logger.debug(f"✅ Got table reference for '{table_name}'")
            
            table.put_item(Item=processed_item)
            logger.debug(f"✅ Successfully saved item to '{table_name}' - ID: {item_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Error putting item in {table_name}: {e}")
            logger.error(f"📝 Item keys that failed: {list(item.keys()) if item else 'None'}")
            return False
    
    def put_item_conditional(self, table_name: str, item: Dict[str, Any], 
                           condition_expression: str, 
                           expression_attribute_names: Optional[Dict[str, str]] = None,
                           expression_attribute_values: Optional[Dict[str, Any]] = None) -> bool:
        """Put an item with conditional expression for idempotency"""
        try:
            # Convert numeric values to proper DynamoDB format
            processed_item = self._convert_item_types(item)
            
            table = self.get_table(table_name)
            
            # Build put_item parameters
            put_params = {
                'Item': processed_item,
                'ConditionExpression': condition_expression
            }
            
            if expression_attribute_names:
                put_params['ExpressionAttributeNames'] = expression_attribute_names
                
            if expression_attribute_values:
                put_params['ExpressionAttributeValues'] = expression_attribute_values
            
            table.put_item(**put_params)
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                # Item already exists - this is expected for idempotency
                raise e
            else:
                logger.error(f"❌ Error putting conditional item in {table_name}: {e}")
                return False
        except Exception as e:
            logger.error(f"❌ Unexpected error putting conditional item in {table_name}: {e}")
            return False
    
    def _convert_item_types(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Convert item types for proper DynamoDB storage"""
        converted = {}
        
        # Define numeric fields that should be stored as DynamoDB Number type
        numeric_fields = {
            'entry_price', 'exit_price', 'current_price', 'stop_loss', 'take_profit',
            'size', 'quantity', 'ai_confidence', 'realized_pnl', 'unrealized_pnl',
            'pnl_percentage', 'duration_minutes', 'price', 'volume', 'amount',
            'balance', 'cash_balance', 'total_pnl', 'risk_score', 'confidence',
            'threshold', 'multiplier', 'ratio', 'percentage'
        }
        
        for key, value in item.items():
            if key in numeric_fields and value is not None:
                # Convert to Decimal for DynamoDB Number type
                if isinstance(value, (int, float, str)):
                    try:
                        converted[key] = Decimal(str(value))
                    except (ValueError, TypeError):
                        converted[key] = value
                elif isinstance(value, Decimal):
                    converted[key] = value
                else:
                    converted[key] = value
            else:
                converted[key] = value
                
        return converted
    
    def get_item(self, table_name: str, key: Dict[str, Any], consistent_read: bool = True) -> Optional[Dict[str, Any]]:
        """Get an item from DynamoDB table with consistent read by default"""
        try:
            table = self.get_table(table_name)
            # Use ConsistentRead=True by default to avoid eventual consistency races
            # This is especially important for DynamoDB Local during development
            response = table.get_item(Key=key, ConsistentRead=consistent_read)
            return response.get('Item')
        except Exception as e:
            logger.error(f"Error getting item from {table_name}: {e}")
            return None
    
    def delete_item(self, table_name: str, key: Dict[str, Any]) -> bool:
        """Delete an item from DynamoDB table"""
        try:
            table = self.get_table(table_name)
            table.delete_item(Key=key)
            return True
        except Exception as e:
            logger.error(f"Error deleting item from {table_name}: {e}")
            return False
    
    def scan_table(self, table_name: str) -> List[Dict[str, Any]]:
        """Scan all items from DynamoDB table"""
        try:
            table = self.get_table(table_name)
            response = table.scan()
            return response.get('Items', [])
        except Exception as e:
            logger.error(f"Error scanning table {table_name}: {e}")
            return []
    
    def query_items(
        self, 
        table_name: str, 
        key_condition_expression: Any = None,
        filter_expression: Any = None,
        projection_expression: str = None,
        index_name: str = None,
        limit: int = None,
        exclusive_start_key: Dict[str, Any] = None,
        consistent_read: bool = True
    ) -> Dict[str, Any]:
        """Query items from DynamoDB table with proper Query operation"""
        try:
            table = self.get_table(table_name)
            
            query_params = {}
            
            if key_condition_expression:
                query_params['KeyConditionExpression'] = key_condition_expression
            
            if filter_expression:
                query_params['FilterExpression'] = filter_expression
                
            if projection_expression:
                query_params['ProjectionExpression'] = projection_expression
                
            if index_name:
                query_params['IndexName'] = index_name
                
            if limit:
                query_params['Limit'] = limit
                
            if exclusive_start_key:
                query_params['ExclusiveStartKey'] = exclusive_start_key
            
            # Add ConsistentRead for DynamoDB Local to avoid eventual consistency races
            # Note: ConsistentRead only works for queries on the main table, not GSI
            if not index_name and consistent_read:
                query_params['ConsistentRead'] = consistent_read
            
            response = table.query(**query_params)
            
            return {
                'Items': response.get('Items', []),
                'Count': response.get('Count', 0),
                'ScannedCount': response.get('ScannedCount', 0),
                'LastEvaluatedKey': response.get('LastEvaluatedKey')
            }
            
        except Exception as e:
            logger.error(f"Error querying table {table_name}: {e}")
            return {'Items': [], 'Count': 0, 'ScannedCount': 0, 'LastEvaluatedKey': None}


@dataclass
class MarketCandle:
    """Market candle data model"""
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    trades: int
    symbol: str = "BTCUSDT"
    interval: str = "1m"
    
    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert to DynamoDB item format"""
        return {
            'PK': f'CANDLE#{self.symbol}#{self.interval}',
            'SK': f'TIMESTAMP#{self.timestamp}',
            'timestamp': self.timestamp,
            'open': Decimal(str(self.open)),
            'high': Decimal(str(self.high)),
            'low': Decimal(str(self.low)),
            'close': Decimal(str(self.close)),
            'volume': Decimal(str(self.volume)),
            'trades': self.trades,
            'symbol': self.symbol,
            'interval': self.interval,
            'date': datetime.fromtimestamp(self.timestamp / 1000).strftime('%Y-%m-%d'),
            'hour': datetime.fromtimestamp(self.timestamp / 1000).strftime('%Y-%m-%d-%H'),
            'TTL': int(self.timestamp / 1000) + (90 * 24 * 60 * 60)  # 90 days retention
        }


@dataclass
class TradingSignal:
    """Trading signal data model"""
    signal_id: str
    timestamp: int
    symbol: str
    action: str  # BUY, SELL, HOLD
    confidence: float
    price: float
    reasoning: Dict[str, Any]
    model_versions: Dict[str, str]
    user_id: Optional[str] = None
    
    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert to DynamoDB item format"""
        return {
            'PK': f'SIGNAL#{self.signal_id}',
            'SK': f'TIMESTAMP#{self.timestamp}',
            'GSI1PK': f'SYMBOL#{self.symbol}',
            'GSI1SK': f'ACTION#{self.action}',
            'GSI2PK': f'DATE#{datetime.fromtimestamp(self.timestamp / 1000).strftime("%Y-%m-%d")}',
            'GSI2SK': f'CONFIDENCE#{int(self.confidence * 100)}',
            'signal_id': self.signal_id,
            'timestamp': self.timestamp,
            'symbol': self.symbol,
            'action': self.action,
            'confidence': Decimal(str(self.confidence)),
            'price': Decimal(str(self.price)),
            'reasoning': json.dumps(self.reasoning),
            'model_versions': json.dumps(self.model_versions),
            'user_id': self.user_id,
            'TTL': int(self.timestamp / 1000) + (365 * 24 * 60 * 60)  # 1 year retention
        }


@dataclass
class ExitAnalysisLog:
    """Exit analysis log data model"""
    log_id: str
    position_id: str
    timestamp: int
    symbol: str
    market_data: Dict[str, Any]
    layer_results: Dict[str, Any]
    final_decision: Dict[str, Any]
    execution_time_ms: int
    user_id: Optional[str] = None
    
    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert to DynamoDB item format"""
        return {
            'PK': f'EXIT_ANALYSIS#{self.log_id}',
            'SK': f'TIMESTAMP#{self.timestamp}',
            'GSI1PK': f'POSITION#{self.position_id}',
            'GSI1SK': f'TIMESTAMP#{self.timestamp}',
            'GSI2PK': f'SYMBOL#{self.symbol}',
            'GSI2SK': f'DATE#{datetime.fromtimestamp(self.timestamp / 1000).strftime("%Y-%m-%d")}',
            'log_id': self.log_id,
            'position_id': self.position_id,
            'timestamp': self.timestamp,
            'symbol': self.symbol,
            'market_data': json.dumps(self.market_data),
            'layer_results': json.dumps(self.layer_results),
            'final_decision': json.dumps(self.final_decision),
            'execution_time_ms': self.execution_time_ms,
            'user_id': self.user_id,
            'TTL': int(self.timestamp / 1000) + (180 * 24 * 60 * 60)  # 180 days retention
        }


@dataclass
class PositionMonitoringLog:
    """Position monitoring log data model"""
    log_id: str
    position_id: str
    timestamp: int
    monitoring_status: str  # STARTED, MONITORING, STOPPED, ERROR
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_percentage: float
    monitoring_duration_minutes: int
    next_analysis_time: int
    user_id: Optional[str] = None
    
    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert to DynamoDB item format"""
        return {
            'PK': f'POSITION_MONITOR#{self.log_id}',
            'SK': f'TIMESTAMP#{self.timestamp}',
            'GSI1PK': f'POSITION#{self.position_id}',
            'GSI1SK': f'TIMESTAMP#{self.timestamp}',
            'GSI2PK': f'STATUS#{self.monitoring_status}',
            'GSI2SK': f'TIMESTAMP#{self.timestamp}',
            'log_id': self.log_id,
            'position_id': self.position_id,
            'timestamp': self.timestamp,
            'monitoring_status': self.monitoring_status,
            'current_price': Decimal(str(self.current_price)),
            'unrealized_pnl': Decimal(str(self.unrealized_pnl)),
            'unrealized_pnl_percentage': Decimal(str(self.unrealized_pnl_percentage)),
            'monitoring_duration_minutes': self.monitoring_duration_minutes,
            'next_analysis_time': self.next_analysis_time,
            'user_id': self.user_id,
            'TTL': int(self.timestamp / 1000) + (90 * 24 * 60 * 60)  # 90 days retention
        }


@dataclass
class TradeExecutionMetrics:
    """Trade execution metrics data model"""
    metrics_id: str
    timestamp: int
    date: str
    total_positions_monitored: int
    total_exit_decisions: int
    successful_exits: int
    failed_exits: int
    average_holding_time_minutes: float
    total_pnl_improvement: float
    exit_reasons: Dict[str, int]
    layer_trigger_stats: Dict[str, int]
    performance_metrics: Dict[str, float]
    
    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert to DynamoDB item format"""
        return {
            'PK': f'EXECUTION_METRICS#{self.metrics_id}',
            'SK': f'TIMESTAMP#{self.timestamp}',
            'GSI1PK': f'DATE#{self.date}',
            'GSI1SK': f'TIMESTAMP#{self.timestamp}',
            'metrics_id': self.metrics_id,
            'timestamp': self.timestamp,
            'date': self.date,
            'total_positions_monitored': self.total_positions_monitored,
            'total_exit_decisions': self.total_exit_decisions,
            'successful_exits': self.successful_exits,
            'failed_exits': self.failed_exits,
            'average_holding_time_minutes': Decimal(str(self.average_holding_time_minutes)),
            'total_pnl_improvement': Decimal(str(self.total_pnl_improvement)),
            'exit_reasons': json.dumps(self.exit_reasons),
            'layer_trigger_stats': json.dumps(self.layer_trigger_stats),
            'performance_metrics': json.dumps(self.performance_metrics),
            'TTL': int(self.timestamp / 1000) + (365 * 24 * 60 * 60)  # 1 year retention
        }


@dataclass
class AlertNotification:
    """Alert notification data model"""
    alert_id: str
    timestamp: int
    alert_type: str  # POSITION_CLOSED, MONITORING_STARTED, MONITORING_STOPPED, ERROR
    title: str
    message: str
    severity: str  # INFO, WARNING, ERROR, CRITICAL
    position_id: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    sent_discord: bool = False
    sent_telegram: bool = False
    
    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert to DynamoDB item format"""
        return {
            'PK': f'ALERT#{self.alert_id}',
            'SK': f'TIMESTAMP#{self.timestamp}',
            'GSI1PK': f'TYPE#{self.alert_type}',
            'GSI1SK': f'TIMESTAMP#{self.timestamp}',
            'GSI2PK': f'SEVERITY#{self.severity}',
            'GSI2SK': f'TIMESTAMP#{self.timestamp}',
            'alert_id': self.alert_id,
            'timestamp': self.timestamp,
            'alert_type': self.alert_type,
            'title': self.title,
            'message': self.message,
            'severity': self.severity,
            'position_id': self.position_id,
            'user_id': self.user_id,
            'metadata': json.dumps(self.metadata) if self.metadata else None,
            'sent_discord': self.sent_discord,
            'sent_telegram': self.sent_telegram,
            'TTL': int(self.timestamp / 1000) + (90 * 24 * 60 * 60)  # 90 days retention
        }


class TableSchemas:
    """DynamoDB table schema definitions"""
    
    @staticmethod
    def get_live_candles_schema() -> Dict[str, Any]:
        """Live market candles table schema - optimized for time-series queries"""
        return {
            'TableName': 'live_candles',
            'KeySchema': [
                {'AttributeName': 'PK', 'KeyType': 'HASH'},
                {'AttributeName': 'SK', 'KeyType': 'RANGE'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'PK', 'AttributeType': 'S'},
                {'AttributeName': 'SK', 'AttributeType': 'N'},  # 🔧 FIX: SK is timestamp (NUMBER, not STRING)
                {'AttributeName': 'date', 'AttributeType': 'S'},
                {'AttributeName': 'hour', 'AttributeType': 'S'},
                {'AttributeName': 'timestamp', 'AttributeType': 'N'}
            ],
            'GlobalSecondaryIndexes': [
                {
                    'IndexName': 'DateIndex',
                    'KeySchema': [
                        {'AttributeName': 'date', 'KeyType': 'HASH'},
                        {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                },
                {
                    'IndexName': 'HourIndex',
                    'KeySchema': [
                        {'AttributeName': 'hour', 'KeyType': 'HASH'},
                        {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ],
            'BillingMode': 'PAY_PER_REQUEST',
            'StreamSpecification': {
                'StreamEnabled': True,
                'StreamViewType': 'NEW_AND_OLD_IMAGES'
            },
            'Tags': [
                {'Key': 'Project', 'Value': 'TradePulse'},
                {'Key': 'Environment', 'Value': os.getenv('ENVIRONMENT', 'development')},
                {'Key': 'DataType', 'Value': 'LiveCandles'}
            ]
        }
    
    @staticmethod
    def get_signals_schema() -> Dict[str, Any]:
        """Trading signals table schema"""
        return {
            'TableName': 'trading_signals',
            'KeySchema': [
                {'AttributeName': 'PK', 'KeyType': 'HASH'},
                {'AttributeName': 'SK', 'KeyType': 'RANGE'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'PK', 'AttributeType': 'S'},
                {'AttributeName': 'SK', 'AttributeType': 'S'},
                {'AttributeName': 'GSI1PK', 'AttributeType': 'S'},
                {'AttributeName': 'GSI1SK', 'AttributeType': 'S'},
                {'AttributeName': 'GSI2PK', 'AttributeType': 'S'},
                {'AttributeName': 'GSI2SK', 'AttributeType': 'S'}
            ],
            'GlobalSecondaryIndexes': [
                {
                    'IndexName': 'SymbolActionIndex',
                    'KeySchema': [
                        {'AttributeName': 'GSI1PK', 'KeyType': 'HASH'},
                        {'AttributeName': 'GSI1SK', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                },
                {
                    'IndexName': 'DateConfidenceIndex',
                    'KeySchema': [
                        {'AttributeName': 'GSI2PK', 'KeyType': 'HASH'},
                        {'AttributeName': 'GSI2SK', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ],
            'BillingMode': 'PAY_PER_REQUEST',
            'StreamSpecification': {
                'StreamEnabled': True,
                'StreamViewType': 'NEW_AND_OLD_IMAGES'
            },
            'Tags': [
                {'Key': 'Project', 'Value': 'TradePulse'},
                {'Key': 'Environment', 'Value': os.getenv('ENVIRONMENT', 'development')},
                {'Key': 'DataType', 'Value': 'TradingSignals'}
            ]
        }
    
    @staticmethod
    def get_training_data_schema() -> Dict[str, Any]:
        """Training data metadata table schema"""
        return {
            'TableName': 'training_data',
            'KeySchema': [
                {'AttributeName': 'PK', 'KeyType': 'HASH'},
                {'AttributeName': 'SK', 'KeyType': 'RANGE'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'PK', 'AttributeType': 'S'},
                {'AttributeName': 'SK', 'AttributeType': 'S'},
                {'AttributeName': 'data_source', 'AttributeType': 'S'},
                {'AttributeName': 'created_at', 'AttributeType': 'S'}
            ],
            'GlobalSecondaryIndexes': [
                {
                    'IndexName': 'DataSourceIndex',
                    'KeySchema': [
                        {'AttributeName': 'data_source', 'KeyType': 'HASH'},
                        {'AttributeName': 'created_at', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ],
            'BillingMode': 'PAY_PER_REQUEST',
            'Tags': [
                {'Key': 'Project', 'Value': 'TradePulse'},
                {'Key': 'Environment', 'Value': os.getenv('ENVIRONMENT', 'development')},
                {'Key': 'DataType', 'Value': 'TrainingData'}
            ]
        }

    @staticmethod
    def get_exit_analysis_log_schema() -> Dict[str, Any]:
        """Exit analysis log table schema for position monitoring"""
        return {
            'TableName': 'exit_analysis_log',
            'KeySchema': [
                {'AttributeName': 'PK', 'KeyType': 'HASH'},
                {'AttributeName': 'SK', 'KeyType': 'RANGE'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'PK', 'AttributeType': 'S'},
                {'AttributeName': 'SK', 'AttributeType': 'S'},
                {'AttributeName': 'GSI1PK', 'AttributeType': 'S'},
                {'AttributeName': 'GSI1SK', 'AttributeType': 'S'},
                {'AttributeName': 'GSI2PK', 'AttributeType': 'S'},
                {'AttributeName': 'GSI2SK', 'AttributeType': 'S'}
            ],
            'GlobalSecondaryIndexes': [
                {
                    'IndexName': 'PositionIndex',
                    'KeySchema': [
                        {'AttributeName': 'GSI1PK', 'KeyType': 'HASH'},
                        {'AttributeName': 'GSI1SK', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                },
                {
                    'IndexName': 'SymbolDateIndex',
                    'KeySchema': [
                        {'AttributeName': 'GSI2PK', 'KeyType': 'HASH'},
                        {'AttributeName': 'GSI2SK', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ],
            'BillingMode': 'PAY_PER_REQUEST',
            'StreamSpecification': {
                'StreamEnabled': True,
                'StreamViewType': 'NEW_AND_OLD_IMAGES'
            },
            'Tags': [
                {'Key': 'Project', 'Value': 'TradePulse'},
                {'Key': 'Environment', 'Value': os.getenv('ENVIRONMENT', 'development')},
                {'Key': 'DataType', 'Value': 'ExitAnalysisLog'}
            ]
        }

    @staticmethod
    def get_position_monitoring_log_schema() -> Dict[str, Any]:
        """Position monitoring log table schema"""
        return {
            'TableName': 'position_monitoring_log',
            'KeySchema': [
                {'AttributeName': 'PK', 'KeyType': 'HASH'},
                {'AttributeName': 'SK', 'KeyType': 'RANGE'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'PK', 'AttributeType': 'S'},
                {'AttributeName': 'SK', 'AttributeType': 'S'},
                {'AttributeName': 'GSI1PK', 'AttributeType': 'S'},
                {'AttributeName': 'GSI1SK', 'AttributeType': 'S'},
                {'AttributeName': 'GSI2PK', 'AttributeType': 'S'},
                {'AttributeName': 'GSI2SK', 'AttributeType': 'S'}
            ],
            'GlobalSecondaryIndexes': [
                {
                    'IndexName': 'PositionIndex',
                    'KeySchema': [
                        {'AttributeName': 'GSI1PK', 'KeyType': 'HASH'},
                        {'AttributeName': 'GSI1SK', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                },
                {
                    'IndexName': 'StatusIndex',
                    'KeySchema': [
                        {'AttributeName': 'GSI2PK', 'KeyType': 'HASH'},
                        {'AttributeName': 'GSI2SK', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ],
            'BillingMode': 'PAY_PER_REQUEST',
            'StreamSpecification': {
                'StreamEnabled': True,
                'StreamViewType': 'NEW_AND_OLD_IMAGES'
            },
            'Tags': [
                {'Key': 'Project', 'Value': 'TradePulse'},
                {'Key': 'Environment', 'Value': os.getenv('ENVIRONMENT', 'development')},
                {'Key': 'DataType', 'Value': 'PositionMonitoringLog'}
            ]
        }

    @staticmethod
    def get_trade_execution_metrics_schema() -> Dict[str, Any]:
        """Trade execution metrics table schema"""
        return {
            'TableName': 'trade_execution_metrics',
            'KeySchema': [
                {'AttributeName': 'PK', 'KeyType': 'HASH'},
                {'AttributeName': 'SK', 'KeyType': 'RANGE'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'PK', 'AttributeType': 'S'},
                {'AttributeName': 'SK', 'AttributeType': 'S'},
                {'AttributeName': 'GSI1PK', 'AttributeType': 'S'},
                {'AttributeName': 'GSI1SK', 'AttributeType': 'S'}
            ],
            'GlobalSecondaryIndexes': [
                {
                    'IndexName': 'DateIndex',
                    'KeySchema': [
                        {'AttributeName': 'GSI1PK', 'KeyType': 'HASH'},
                        {'AttributeName': 'GSI1SK', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ],
            'BillingMode': 'PAY_PER_REQUEST',
            'StreamSpecification': {
                'StreamEnabled': True,
                'StreamViewType': 'NEW_AND_OLD_IMAGES'
            },
            'Tags': [
                {'Key': 'Project', 'Value': 'TradePulse'},
                {'Key': 'Environment', 'Value': os.getenv('ENVIRONMENT', 'development')},
                {'Key': 'DataType', 'Value': 'TradeExecutionMetrics'}
            ]
        }

    @staticmethod
    def get_alert_notifications_schema() -> Dict[str, Any]:
        """Alert notifications table schema"""
        return {
            'TableName': 'alert_notifications',
            'KeySchema': [
                {'AttributeName': 'PK', 'KeyType': 'HASH'},
                {'AttributeName': 'SK', 'KeyType': 'RANGE'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'PK', 'AttributeType': 'S'},
                {'AttributeName': 'SK', 'AttributeType': 'S'},
                {'AttributeName': 'status', 'AttributeType': 'S'},
                {'AttributeName': 'created_at', 'AttributeType': 'S'}
            ],
            'GlobalSecondaryIndexes': [
                {
                    'IndexName': 'StatusIndex',
                    'KeySchema': [
                        {'AttributeName': 'status', 'KeyType': 'HASH'},
                        {'AttributeName': 'created_at', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ],
            'BillingMode': 'PAY_PER_REQUEST',
            'Tags': [
                {'Key': 'Project', 'Value': 'TradePulse'},
                {'Key': 'Environment', 'Value': os.getenv('ENVIRONMENT', 'development')},
                {'Key': 'DataType', 'Value': 'AlertNotifications'}
            ]
        }

    @staticmethod
    def get_users_schema() -> Dict[str, Any]:
        """Users table schema"""
        return {
            'TableName': 'tradepulse-users',
            'KeySchema': [
                {'AttributeName': 'id', 'KeyType': 'HASH'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'id', 'AttributeType': 'S'},
                {'AttributeName': 'email', 'AttributeType': 'S'}
            ],
            'GlobalSecondaryIndexes': [
                {
                    'IndexName': 'EmailIndex',
                    'KeySchema': [
                        {'AttributeName': 'email', 'KeyType': 'HASH'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ],
            'BillingMode': 'PAY_PER_REQUEST',
            'Tags': [
                {'Key': 'Project', 'Value': 'TradePulse'},
                {'Key': 'Environment', 'Value': os.getenv('ENVIRONMENT', 'development')},
                {'Key': 'DataType', 'Value': 'Users'}
            ]
        }

    @staticmethod
    def get_virtual_portfolios_schema() -> Dict[str, Any]:
        """Virtual portfolios table schema"""
        return {
            'TableName': 'tradepulse-virtual-portfolios',
            'KeySchema': [
                {'AttributeName': 'user_id', 'KeyType': 'HASH'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'user_id', 'AttributeType': 'S'}
            ],
            'BillingMode': 'PAY_PER_REQUEST',
            'Tags': [
                {'Key': 'Project', 'Value': 'TradePulse'},
                {'Key': 'Environment', 'Value': os.getenv('ENVIRONMENT', 'development')},
                {'Key': 'DataType', 'Value': 'VirtualPortfolios'}
            ]
        }
    
    def get_ai_vs_random_experiments_schema(self) -> Dict[str, Any]:
        """AI vs Random experiments table schema - REAL DATA FOR MARKETING"""
        return {
            'TableName': 'ai_vs_random_experiments',
            'KeySchema': [
                {'AttributeName': 'experiment_id', 'KeyType': 'HASH'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'experiment_id', 'AttributeType': 'S'},
                {'AttributeName': 'start_date', 'AttributeType': 'S'},
                {'AttributeName': 'experiment_status', 'AttributeType': 'S'}
            ],
            'GlobalSecondaryIndexes': [
                {
                    'IndexName': 'status-date-index',
                    'KeySchema': [
                        {'AttributeName': 'experiment_status', 'KeyType': 'HASH'},
                        {'AttributeName': 'start_date', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ],
            'BillingMode': 'PAY_PER_REQUEST'
        }
    
    def get_signal_accuracy_tracking_schema(self) -> Dict[str, Any]:
        """Signal accuracy tracking table schema - CONTINUOUS LEARNING DATA"""
        return {
            'TableName': 'signal_accuracy_tracking',
            'KeySchema': [
                {'AttributeName': 'signal_id', 'KeyType': 'HASH'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'signal_id', 'AttributeType': 'S'},
                {'AttributeName': 'generated_at', 'AttributeType': 'S'},
                {'AttributeName': 'outcome_measured', 'AttributeType': 'S'}
            ],
            'GlobalSecondaryIndexes': [
                {
                    'IndexName': 'date-measured-index',
                    'KeySchema': [
                        {'AttributeName': 'outcome_measured', 'KeyType': 'HASH'},
                        {'AttributeName': 'generated_at', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ],
            'BillingMode': 'PAY_PER_REQUEST'
        }

    def get_trading_patterns_schema(self) -> Dict[str, Any]:
        """Trading patterns database schema - PATTERN LEARNING ENGINE"""
        return {
            'TableName': 'trading_patterns',
            'KeySchema': [
                {'AttributeName': 'pattern_id', 'KeyType': 'HASH'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'pattern_id', 'AttributeType': 'S'},
                {'AttributeName': 'pattern_type', 'AttributeType': 'S'},
                {'AttributeName': 'success_rate', 'AttributeType': 'N'},
                {'AttributeName': 'market_condition', 'AttributeType': 'S'},
                {'AttributeName': 'last_updated', 'AttributeType': 'S'}
            ],
            'GlobalSecondaryIndexes': [
                {
                    'IndexName': 'type-success-index',
                    'KeySchema': [
                        {'AttributeName': 'pattern_type', 'KeyType': 'HASH'},
                        {'AttributeName': 'success_rate', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                },
                {
                    'IndexName': 'market-updated-index',
                    'KeySchema': [
                        {'AttributeName': 'market_condition', 'KeyType': 'HASH'},
                        {'AttributeName': 'last_updated', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ],
            'BillingMode': 'PAY_PER_REQUEST'
        }

    def get_user_performance_showcases_schema(self) -> Dict[str, Any]:
        """User performance showcases schema - MARKETING TESTIMONIALS"""
        return {
            'TableName': 'user_performance_showcases',
            'KeySchema': [
                {'AttributeName': 'showcase_id', 'KeyType': 'HASH'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'showcase_id', 'AttributeType': 'S'},
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'performance_score', 'AttributeType': 'N'},
                {'AttributeName': 'created_date', 'AttributeType': 'S'},
                {'AttributeName': 'marketing_approved', 'AttributeType': 'S'}
            ],
            'GlobalSecondaryIndexes': [
                {
                    'IndexName': 'user-performance-index',
                    'KeySchema': [
                        {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                        {'AttributeName': 'performance_score', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                },
                {
                    'IndexName': 'marketing-date-index',
                    'KeySchema': [
                        {'AttributeName': 'marketing_approved', 'KeyType': 'HASH'},
                        {'AttributeName': 'created_date', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ],
            'BillingMode': 'PAY_PER_REQUEST'
        }

    def get_model_performance_metrics_schema(self) -> Dict[str, Any]:
        """Model performance metrics schema - DETAILED AI ANALYSIS"""
        return {
            'TableName': 'model_performance_metrics',
            'KeySchema': [
                {'AttributeName': 'metric_id', 'KeyType': 'HASH'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'metric_id', 'AttributeType': 'S'},
                {'AttributeName': 'date', 'AttributeType': 'S'},
                {'AttributeName': 'model_type', 'AttributeType': 'S'},
                {'AttributeName': 'accuracy_score', 'AttributeType': 'N'}
            ],
            'GlobalSecondaryIndexes': [
                {
                    'IndexName': 'date-accuracy-index',
                    'KeySchema': [
                        {'AttributeName': 'date', 'KeyType': 'HASH'},
                        {'AttributeName': 'accuracy_score', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                },
                {
                    'IndexName': 'model-date-index',
                    'KeySchema': [
                        {'AttributeName': 'model_type', 'KeyType': 'HASH'},
                        {'AttributeName': 'date', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ],
            'BillingMode': 'PAY_PER_REQUEST'
        }

    def get_users_enhanced_schema(self) -> Dict[str, Any]:
        """Get the enhanced users table schema for enterprise user management"""
        return {
            'TableName': 'users_enhanced',
            'BillingMode': 'PAY_PER_REQUEST',
            'KeySchema': [
                {'AttributeName': 'id', 'KeyType': 'HASH'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'id', 'AttributeType': 'S'},
                {'AttributeName': 'email', 'AttributeType': 'S'},
                {'AttributeName': 'status', 'AttributeType': 'S'},
                {'AttributeName': 'role', 'AttributeType': 'S'},
                {'AttributeName': 'created_at', 'AttributeType': 'S'}
            ],
            'GlobalSecondaryIndexes': [
                {
                    'IndexName': 'email-index',
                    'KeySchema': [{'AttributeName': 'email', 'KeyType': 'HASH'}],
                    'Projection': {'ProjectionType': 'ALL'}
                },
                {
                    'IndexName': 'status-index',
                    'KeySchema': [{'AttributeName': 'status', 'KeyType': 'HASH'}],
                    'Projection': {'ProjectionType': 'ALL'}
                },
                {
                    'IndexName': 'role-index',
                    'KeySchema': [{'AttributeName': 'role', 'KeyType': 'HASH'}],
                    'Projection': {'ProjectionType': 'ALL'}
                },
                {
                    'IndexName': 'created_at-index',
                    'KeySchema': [{'AttributeName': 'created_at', 'KeyType': 'HASH'}],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ]
        }

    def get_invitations_schema(self) -> Dict[str, Any]:
        """Get the invitations table schema for invitation management"""
        return {
            'TableName': 'invitations',
            'BillingMode': 'PAY_PER_REQUEST',
            'KeySchema': [
                {'AttributeName': 'id', 'KeyType': 'HASH'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'id', 'AttributeType': 'S'},
                {'AttributeName': 'email', 'AttributeType': 'S'},
                {'AttributeName': 'status', 'AttributeType': 'S'},
                {'AttributeName': 'invited_by', 'AttributeType': 'S'},
                {'AttributeName': 'created_at', 'AttributeType': 'S'}
            ],
            'GlobalSecondaryIndexes': [
                {
                    'IndexName': 'email-index',
                    'KeySchema': [{'AttributeName': 'email', 'KeyType': 'HASH'}],
                    'Projection': {'ProjectionType': 'ALL'}
                },
                {
                    'IndexName': 'status-index',
                    'KeySchema': [{'AttributeName': 'status', 'KeyType': 'HASH'}],
                    'Projection': {'ProjectionType': 'ALL'}
                },
                {
                    'IndexName': 'invited_by-index',
                    'KeySchema': [{'AttributeName': 'invited_by', 'KeyType': 'HASH'}],
                    'Projection': {'ProjectionType': 'ALL'}
                },
                {
                    'IndexName': 'created_at-index',
                    'KeySchema': [{'AttributeName': 'created_at', 'KeyType': 'HASH'}],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ]
        }

    def get_user_activity_logs_schema(self) -> Dict[str, Any]:
        """Get the user_activity_logs table schema for audit trails"""
        return {
            'TableName': 'user_activity_logs',
            'BillingMode': 'PAY_PER_REQUEST',
            'KeySchema': [
                {'AttributeName': 'id', 'KeyType': 'HASH'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'id', 'AttributeType': 'S'},
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'timestamp', 'AttributeType': 'S'},
                {'AttributeName': 'action', 'AttributeType': 'S'}
            ],
            'GlobalSecondaryIndexes': [
                {
                    'IndexName': 'user_id-timestamp-index',
                    'KeySchema': [
                        {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                        {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                },
                {
                    'IndexName': 'action-index',
                    'KeySchema': [{'AttributeName': 'action', 'KeyType': 'HASH'}],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ]
        }

    def get_messages_schema(self) -> Dict[str, Any]:
        """Get the messages table schema for communication system"""
        return {
            'TableName': 'messages',
            'BillingMode': 'PAY_PER_REQUEST',
            'KeySchema': [
                {'AttributeName': 'id', 'KeyType': 'HASH'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'id', 'AttributeType': 'S'},
                {'AttributeName': 'sender_id', 'AttributeType': 'S'},
                {'AttributeName': 'type', 'AttributeType': 'S'},
                {'AttributeName': 'created_at', 'AttributeType': 'S'}
            ],
            'GlobalSecondaryIndexes': [
                {
                    'IndexName': 'sender_id-index',
                    'KeySchema': [{'AttributeName': 'sender_id', 'KeyType': 'HASH'}],
                    'Projection': {'ProjectionType': 'ALL'}
                },
                {
                    'IndexName': 'type-created_at-index',
                    'KeySchema': [
                        {'AttributeName': 'type', 'KeyType': 'HASH'},
                        {'AttributeName': 'created_at', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ]
        }

    def get_message_deliveries_schema(self) -> Dict[str, Any]:
        """Get the message_deliveries table schema"""
        return {
            'TableName': 'message_deliveries',
            'BillingMode': 'PAY_PER_REQUEST',
            'KeySchema': [
                {'AttributeName': 'id', 'KeyType': 'HASH'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'id', 'AttributeType': 'S'},
                {'AttributeName': 'recipient_id', 'AttributeType': 'S'},
                {'AttributeName': 'message_id', 'AttributeType': 'S'},
                {'AttributeName': 'created_at', 'AttributeType': 'S'},
                {'AttributeName': 'status', 'AttributeType': 'S'}
            ],
            'GlobalSecondaryIndexes': [
                {
                    'IndexName': 'recipient_id-created_at-index',
                    'KeySchema': [
                        {'AttributeName': 'recipient_id', 'KeyType': 'HASH'},
                        {'AttributeName': 'created_at', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                },
                {
                    'IndexName': 'message_id-index',
                    'KeySchema': [{'AttributeName': 'message_id', 'KeyType': 'HASH'}],
                    'Projection': {'ProjectionType': 'ALL'}
                },
                {
                    'IndexName': 'status-index',
                    'KeySchema': [{'AttributeName': 'status', 'KeyType': 'HASH'}],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ]
        }

    def get_announcements_schema(self) -> Dict[str, Any]:
        """Get the announcements table schema"""
        return {
            'TableName': 'announcements',
            'BillingMode': 'PAY_PER_REQUEST',
            'KeySchema': [
                {'AttributeName': 'id', 'KeyType': 'HASH'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'id', 'AttributeType': 'S'},
                {'AttributeName': 'created_by', 'AttributeType': 'S'},
                {'AttributeName': 'status', 'AttributeType': 'S'},
                {'AttributeName': 'created_at', 'AttributeType': 'S'}
            ],
            'GlobalSecondaryIndexes': [
                {
                    'IndexName': 'created_by-index',
                    'KeySchema': [{'AttributeName': 'created_by', 'KeyType': 'HASH'}],
                    'Projection': {'ProjectionType': 'ALL'}
                },
                {
                    'IndexName': 'status-created_at-index',
                    'KeySchema': [
                        {'AttributeName': 'status', 'KeyType': 'HASH'},
                        {'AttributeName': 'created_at', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ]
        }

    def get_user_notification_preferences_schema(self) -> Dict[str, Any]:
        """Get the user notification preferences table schema"""
        return {
            'TableName': 'user_notification_preferences',
            'BillingMode': 'PAY_PER_REQUEST',
            'KeySchema': [
                {'AttributeName': 'user_id', 'KeyType': 'HASH'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'user_id', 'AttributeType': 'S'}
            ]
        }

    def get_notification_templates_schema(self) -> Dict[str, Any]:
        """Get the notification templates table schema"""
        return {
            'TableName': 'notification_templates',
            'BillingMode': 'PAY_PER_REQUEST',
            'KeySchema': [
                {'AttributeName': 'id', 'KeyType': 'HASH'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'id', 'AttributeType': 'S'},
                {'AttributeName': 'type', 'AttributeType': 'S'},
                {'AttributeName': 'category', 'AttributeType': 'S'}
            ],
            'GlobalSecondaryIndexes': [
                {
                    'IndexName': 'type-index',
                    'KeySchema': [{'AttributeName': 'type', 'KeyType': 'HASH'}],
                    'Projection': {'ProjectionType': 'ALL'}
                },
                {
                    'IndexName': 'category-index',
                    'KeySchema': [{'AttributeName': 'category', 'KeyType': 'HASH'}],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ]
        }

    def get_learning_engine_state_schema(self) -> Dict[str, Any]:
        """Learning engine state table schema"""
        return {
            'TableName': 'learning_engine_state',
            'KeySchema': [
                {'AttributeName': 'engine_id', 'KeyType': 'HASH'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'engine_id', 'AttributeType': 'S'}
            ],
            'BillingMode': 'PAY_PER_REQUEST'
        }

    @staticmethod
    def get_health_checks_schema() -> Dict[str, Any]:
        """System health checks table schema used by health monitor."""
        return {
            'TableName': 'health_checks',
            'BillingMode': 'PAY_PER_REQUEST',
            'KeySchema': [
                {'AttributeName': 'check_id', 'KeyType': 'HASH'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'check_id', 'AttributeType': 'S'}
            ]
        }
    
    @staticmethod
    def get_trade_analyses_schema() -> Dict[str, Any]:
        """Trade analyses table schema for storing detailed trade analysis results."""
        return {
            'TableName': 'trade_analyses',
            'BillingMode': 'PAY_PER_REQUEST',
            'KeySchema': [
                {'AttributeName': 'trade_id', 'KeyType': 'HASH'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'trade_id', 'AttributeType': 'S'},
                {'AttributeName': 'symbol', 'AttributeType': 'S'},
                {'AttributeName': 'entry_time', 'AttributeType': 'S'}
            ],
            'GlobalSecondaryIndexes': [
                {
                    'IndexName': 'symbol-entry_time-index',
                    'KeySchema': [
                        {'AttributeName': 'symbol', 'KeyType': 'HASH'},
                        {'AttributeName': 'entry_time', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ]
        }
    
    @staticmethod
    def get_market_context_cache_schema() -> Dict[str, Any]:
        """Market context cache table for S/R levels and pattern stats."""
        return {
            'TableName': 'market_context_cache',
            'BillingMode': 'PAY_PER_REQUEST',
            'KeySchema': [
                {'AttributeName': 'symbol', 'KeyType': 'HASH'},
                {'AttributeName': 'period', 'KeyType': 'RANGE'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'symbol', 'AttributeType': 'S'},
                {'AttributeName': 'period', 'AttributeType': 'S'}
            ],
            'TimeToLiveSpecification': {
                'Enabled': True,
                'AttributeName': 'ttl'
            }
        }

class DatabaseManager:
    """Database manager for table operations and data management"""
    
    def __init__(self, local_development: Optional[bool] = None):
        self.client = DynamoDBClient(local_development)
        self.schemas = TableSchemas()
    
    def setup_all_tables(self) -> bool:
        """Set up all required tables for the application"""
        table_configs = [
            self.schemas.get_live_candles_schema(),
            self.schemas.get_signals_schema(),
            self.schemas.get_training_data_schema(),
            self.schemas.get_exit_analysis_log_schema(),
            self.schemas.get_position_monitoring_log_schema(),
            self.schemas.get_trade_execution_metrics_schema(),
            self.schemas.get_alert_notifications_schema(),
            self.schemas.get_users_schema(),
            self.schemas.get_virtual_portfolios_schema(),
            self.schemas.get_ai_vs_random_experiments_schema(),
            self.schemas.get_signal_accuracy_tracking_schema(),
            self.schemas.get_trading_patterns_schema(),
            self.schemas.get_user_performance_showcases_schema(),
            self.schemas.get_model_performance_metrics_schema(),
            self.schemas.get_users_enhanced_schema(),
            self.schemas.get_invitations_schema(),
            self.schemas.get_user_activity_logs_schema(),
            self.schemas.get_messages_schema(),
            self.schemas.get_message_deliveries_schema(),
            self.schemas.get_announcements_schema(),
            self.schemas.get_user_notification_preferences_schema(),
            self.schemas.get_notification_templates_schema(),
            self.schemas.get_learning_engine_state_schema(),
            self.schemas.get_health_checks_schema(),
            self.schemas.get_trade_analyses_schema()
        ]
        
        success = True
        for config in table_configs:
            try:
                # Check if table exists
                table = self.client.get_table(config['TableName'])
                logger.debug(f"✅ Table {config['TableName']} already exists")
            except:
                # Create table if it doesn't exist
                logger.info(f"📝 Creating table {config['TableName']}")
                if not self.client.create_table(config):
                    success = False
                    logger.error(f"❌ Failed to create table {config['TableName']}")
        
        return success
    
    def store_live_candle(self, candle: MarketCandle) -> bool:
        """Store live market candle data"""
        try:
            table = self.client.get_table('live_candles')
            table.put_item(Item=candle.to_dynamodb_item())
            return True
        except Exception as e:
            logger.error(f"Error storing live candle: {e}")
            return False
    
    def store_trading_signal(self, signal: TradingSignal) -> bool:
        """Store trading signal"""
        try:
            table = self.client.get_table('trading_signals')
            table.put_item(Item=signal.to_dynamodb_item())
            return True
        except Exception as e:
            logger.error(f"Error storing trading signal: {e}")
            return False
    
    def store_exit_analysis_log(self, log: ExitAnalysisLog) -> bool:
        """Store exit analysis log"""
        try:
            table = self.client.get_table('exit_analysis_log')
            table.put_item(Item=log.to_dynamodb_item())
            return True
        except Exception as e:
            logger.error(f"Error storing exit analysis log: {e}")
            return False
    
    def store_position_monitoring_log(self, log: PositionMonitoringLog) -> bool:
        """Store position monitoring log"""
        try:
            table = self.client.get_table('position_monitoring_log')
            table.put_item(Item=log.to_dynamodb_item())
            return True
        except Exception as e:
            logger.error(f"Error storing position monitoring log: {e}")
            return False
    
    def store_trade_execution_metrics(self, metrics: TradeExecutionMetrics) -> bool:
        """Store trade execution metrics"""
        try:
            table = self.client.get_table('trade_execution_metrics')
            table.put_item(Item=metrics.to_dynamodb_item())
            return True
        except Exception as e:
            logger.error(f"Error storing trade execution metrics: {e}")
            return False
    
    def store_alert_notification(self, alert: AlertNotification) -> bool:
        """Store alert notification"""
        try:
            table = self.client.get_table('alert_notifications')
            table.put_item(Item=alert.to_dynamodb_item())
            return True
        except Exception as e:
            logger.error(f"Error storing alert notification: {e}")
            return False
    
    def get_recent_candles(self, symbol: str = "BTCUSDT", limit: int = 100) -> List[MarketCandle]:
        """Get recent candles for ML processing"""
        try:
            table = self.client.get_table('live_candles')
            response = table.query(
                KeyConditionExpression='PK = :pk',
                ExpressionAttributeValues={':pk': f'CANDLE#{symbol}#1m'},
                ScanIndexForward=False,  # Get latest first
                Limit=limit
            )
            
            candles = []
            for item in response['Items']:
                candles.append(MarketCandle(
                    timestamp=int(item['timestamp']),
                    open=float(item['open']),
                    high=float(item['high']),
                    low=float(item['low']),
                    close=float(item['close']),
                    volume=float(item['volume']),
                    trades=int(item['trades']),
                    symbol=item['symbol'],
                    interval=item['interval']
                ))
            
            return candles
        except Exception as e:
            logger.error(f"Error getting recent candles: {e}")
            return []
    
    def get_exit_analysis_logs_by_position(self, position_id: str, limit: int = 50) -> List[ExitAnalysisLog]:
        """Get exit analysis logs for a specific position"""
        try:
            table = self.client.get_table('exit_analysis_log')
            response = table.query(
                IndexName='PositionIndex',
                KeyConditionExpression='GSI1PK = :pk',
                ExpressionAttributeValues={':pk': f'POSITION#{position_id}'},
                ScanIndexForward=False,  # Get latest first
                Limit=limit
            )
            
            logs = []
            for item in response['Items']:
                logs.append(ExitAnalysisLog(
                    log_id=item['log_id'],
                    position_id=item['position_id'],
                    timestamp=int(item['timestamp']),
                    symbol=item['symbol'],
                    market_data=json.loads(item['market_data']),
                    layer_results=json.loads(item['layer_results']),
                    final_decision=json.loads(item['final_decision']),
                    execution_time_ms=int(item['execution_time_ms']),
                    user_id=item.get('user_id')
                ))
            
            return logs
        except Exception as e:
            logger.error(f"Error getting exit analysis logs for position {position_id}: {e}")
            return []
    
    def get_position_monitoring_logs_by_position(self, position_id: str, limit: int = 100) -> List[PositionMonitoringLog]:
        """Get position monitoring logs for a specific position"""
        try:
            table = self.client.get_table('position_monitoring_log')
            response = table.query(
                IndexName='PositionIndex',
                KeyConditionExpression='GSI1PK = :pk',
                ExpressionAttributeValues={':pk': f'POSITION#{position_id}'},
                ScanIndexForward=False,  # Get latest first
                Limit=limit
            )
            
            logs = []
            for item in response['Items']:
                logs.append(PositionMonitoringLog(
                    log_id=item['log_id'],
                    position_id=item['position_id'],
                    timestamp=int(item['timestamp']),
                    monitoring_status=item['monitoring_status'],
                    current_price=float(item['current_price']),
                    unrealized_pnl=float(item['unrealized_pnl']),
                    unrealized_pnl_percentage=float(item['unrealized_pnl_percentage']),
                    monitoring_duration_minutes=int(item['monitoring_duration_minutes']),
                    next_analysis_time=int(item['next_analysis_time']),
                    user_id=item.get('user_id')
                ))
            
            return logs
        except Exception as e:
            logger.error(f"Error getting position monitoring logs for position {position_id}: {e}")
            return []
    
    def get_trade_execution_metrics_by_date(self, date: str, limit: int = 50) -> List[TradeExecutionMetrics]:
        """Get trade execution metrics for a specific date"""
        try:
            table = self.client.get_table('trade_execution_metrics')
            response = table.query(
                IndexName='DateIndex',
                KeyConditionExpression='GSI1PK = :pk',
                ExpressionAttributeValues={':pk': f'DATE#{date}'},
                ScanIndexForward=False,  # Get latest first
                Limit=limit
            )
            
            metrics = []
            for item in response['Items']:
                metrics.append(TradeExecutionMetrics(
                    metrics_id=item['metrics_id'],
                    timestamp=int(item['timestamp']),
                    date=item['date'],
                    total_positions_monitored=int(item['total_positions_monitored']),
                    total_exit_decisions=int(item['total_exit_decisions']),
                    successful_exits=int(item['successful_exits']),
                    failed_exits=int(item['failed_exits']),
                    average_holding_time_minutes=float(item['average_holding_time_minutes']),
                    total_pnl_improvement=float(item['total_pnl_improvement']),
                    exit_reasons=json.loads(item['exit_reasons']),
                    layer_trigger_stats=json.loads(item['layer_trigger_stats']),
                    performance_metrics=json.loads(item['performance_metrics'])
                ))
            
            return metrics
        except Exception as e:
            logger.error(f"Error getting trade execution metrics for date {date}: {e}")
            return []
    
    def get_alert_notifications_by_type(self, alert_type: str, limit: int = 50) -> List[AlertNotification]:
        """Get alert notifications by type"""
        try:
            table = self.client.get_table('alert_notifications')
            response = table.query(
                IndexName='TypeIndex',
                KeyConditionExpression='GSI1PK = :pk',
                ExpressionAttributeValues={':pk': f'TYPE#{alert_type}'},
                ScanIndexForward=False,  # Get latest first
                Limit=limit
            )
            
            alerts = []
            for item in response['Items']:
                alerts.append(AlertNotification(
                    alert_id=item['alert_id'],
                    timestamp=int(item['timestamp']),
                    alert_type=item['alert_type'],
                    title=item['title'],
                    message=item['message'],
                    severity=item['severity'],
                    position_id=item.get('position_id'),
                    user_id=item.get('user_id'),
                    metadata=json.loads(item['metadata']) if item.get('metadata') else None,
                    sent_discord=item.get('sent_discord', False),
                    sent_telegram=item.get('sent_telegram', False)
                ))
            
            return alerts
        except Exception as e:
            logger.error(f"Error getting alert notifications by type {alert_type}: {e}")
            return []

# Database manager - initialize only when needed
_db_manager = None

def get_database_manager():
    """Get database manager instance (lazy initialization)"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager 

async def init_database() -> None:
    """
    Initialize database connection and tables
    Enterprise startup function for database initialization
    """
    try:
        logger.info("🔍 Initializing database connection...")
        
        # Create DynamoDB client
        client = DynamoDBClient()
        
        # Test connection
        await test_connection(client)
        
        logger.info("✅ Database initialization successful")
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise


async def test_connection(client: DynamoDBClient) -> bool:
    """Test database connection"""
    try:
        # Try to list tables to test connection
        response = client.dynamodb.meta.client.list_tables()
        table_count = len(response.get('TableNames', []))
        logger.info(f"Database connection OK - {table_count} tables available")
        return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False


def get_database_session():
    """Get database session (placeholder for future session management)"""
    return DynamoDBClient()

def get_database_client():
    """Get database client for service usage"""
    return DynamoDBClient()


def ensure_table_exists(dynamodb_client, table_name: str, attributes: List[Dict], key_schema: List[Dict], 
                       global_secondary_indexes: Optional[List[Dict]] = None) -> bool:
    """
    Ensure a DynamoDB table exists, create if it doesn't
    
    Args:
        dynamodb_client: DynamoDB client instance
        table_name: Name of the table
        attributes: List of attribute definitions
        key_schema: Key schema definition
        global_secondary_indexes: Optional GSI definitions
        
    Returns:
        bool: True if table exists or was created successfully
    """
    try:
        # Check if table exists
        table = dynamodb_client.get_table(table_name)
        logger.debug(f"✅ Table '{table_name}' already exists")
        return True
    except Exception:
        # Table doesn't exist, create it
        try:
            logger.info(f"🔧 Creating table '{table_name}'...")
            
            table_config = {
                'TableName': table_name,
                'AttributeDefinitions': attributes,
                'KeySchema': key_schema,
                'BillingMode': 'PAY_PER_REQUEST'
            }
            
            if global_secondary_indexes:
                table_config['GlobalSecondaryIndexes'] = global_secondary_indexes
            
            dynamodb_client.dynamodb.create_table(**table_config)
            
            # Wait for table to become active
            waiter = dynamodb_client.dynamodb.meta.client.get_waiter('table_exists')
            waiter.wait(TableName=table_name)
            
            logger.info(f"✅ Table '{table_name}' created successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create table '{table_name}': {e}")
            return False


def ensure_required_tables() -> bool:
    """
    Ensure all required tables exist in DynamoDB Local
    This function should be called during application startup
    
    Returns:
        bool: True if all tables exist or were created successfully
    """
    try:
        client = DynamoDBClient()
        success = True
        
        # Get all table schemas from TableSchemas class
        schemas = TableSchemas()
        table_schemas = [
            TableSchemas.get_live_candles_schema(),
            TableSchemas.get_signals_schema(),
            TableSchemas.get_training_data_schema(),
            TableSchemas.get_exit_analysis_log_schema(),
            TableSchemas.get_position_monitoring_log_schema(),
            TableSchemas.get_trade_execution_metrics_schema(),
            TableSchemas.get_alert_notifications_schema(),
            TableSchemas.get_users_schema(),
            TableSchemas.get_virtual_portfolios_schema(),
            schemas.get_ai_vs_random_experiments_schema(),
            schemas.get_signal_accuracy_tracking_schema(),
            schemas.get_trading_patterns_schema(),
            schemas.get_user_performance_showcases_schema(),
            schemas.get_model_performance_metrics_schema(),
            schemas.get_users_enhanced_schema(),
            schemas.get_invitations_schema(),
            schemas.get_user_activity_logs_schema(),
            schemas.get_messages_schema(),
            schemas.get_message_deliveries_schema(),
            schemas.get_announcements_schema(),
            schemas.get_user_notification_preferences_schema(),
            schemas.get_notification_templates_schema(),
            TableSchemas.get_health_checks_schema(),
            schemas.get_learning_engine_state_schema(),
            TableSchemas.get_trade_analyses_schema(),
            TableSchemas.get_market_context_cache_schema()
        ]
        
        success_count = 0
        total_count = len(table_schemas)
        
        logger.info(f"🔧 Ensuring {total_count} required DynamoDB tables exist...")
        
        for schema in table_schemas:
            table_name = schema['TableName']
            try:
                # Check if table exists
                client.dynamodb.meta.client.describe_table(TableName=table_name)
                logger.debug(f"✅ Table {table_name} already exists")
                success_count += 1
                
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    # Table doesn't exist, create it
                    try:
                        logger.info(f"🔨 Creating table {table_name}...")
                        client.dynamodb.meta.client.create_table(**schema)
                        
                        # Wait for table to become active
                        waiter = client.dynamodb.meta.client.get_waiter('table_exists')
                        waiter.wait(TableName=table_name)
                        
                        logger.info(f"✅ Successfully created table {table_name}")
                        
                        # Enable TTL for tables that need it (after table is ACTIVE)
                        ttl_tables = ['trading_signals', 'exit_analysis_log', 'position_monitoring_log', 'trade_execution_metrics']
                        if table_name in ttl_tables:
                            try:
                                client.dynamodb.meta.client.update_time_to_live(
                                    TableName=table_name,
                                    TimeToLiveSpecification={
                                        'Enabled': True,
                                        'AttributeName': 'ttl'
                                    }
                                )
                                logger.debug(f"✅ TTL enabled for {table_name}")
                            except Exception as ttl_error:
                                logger.warning(f"⚠️ Failed to enable TTL for {table_name}: {ttl_error}")
                        
                        success_count += 1
                        
                    except Exception as create_error:
                        logger.error(f"❌ Failed to create table {table_name}: {create_error}")
                else:
                    logger.error(f"❌ Error checking table {table_name}: {e}")
        
        success = (success_count == total_count)
        
        logger.info(f"📊 Table creation complete: {success_count}/{total_count} tables ready")
        
        if success:
            logger.info("🎉 All required tables are available!")
        else:
            logger.error(f"⚠️ {total_count - success_count} tables failed to create")
            
        return success
        
    except Exception as e:
        logger.error(f"❌ Error ensuring required tables: {e}")
        return False 