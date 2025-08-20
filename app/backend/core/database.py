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
import structlog
from dataclasses import dataclass

from .config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class DynamoDBClient:
    """DynamoDB client wrapper for local development and AWS deployment"""
    
    def __init__(self, local_development: Optional[bool] = None):
        if local_development is None:
            local_development = settings.ENVIRONMENT == 'dev'  # Changed from 'development' to 'dev'
        self.dynamodb: Any
        if local_development:
            try:
                # Local DynamoDB on port 8000
                self.dynamodb = boto3.resource(
                    'dynamodb',
                    endpoint_url='http://localhost:8000',
                    region_name='us-east-1',
                    aws_access_key_id='dummy',
                    aws_secret_access_key='dummy'
                )
                # Test connection
                self.dynamodb.meta.client.list_tables()
                logger.info("Using DynamoDB Local on port 8000")
            except EndpointConnectionError:
                logger.warning("DynamoDB Local not available, falling back to AWS DynamoDB")
                self.dynamodb = boto3.resource(
                    'dynamodb',
                    region_name=settings.AWS_REGION,
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
                )
        else:
            # AWS DynamoDB
            self.dynamodb = boto3.resource(
                'dynamodb',
                region_name=settings.AWS_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
            )
    
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
            logger.info(f"Created table: {table_config['TableName']}")
            return True
        except ClientError as e:
            logger.error(f"Error creating table {table_config['TableName']}: {e}")
            return False
    
    def put_item(self, table_name: str, item: Dict[str, Any]) -> bool:
        """Put an item in DynamoDB table"""
        try:
            logger.info(f"🔄 Attempting to save item to table '{table_name}'")
            logger.info(f"📝 Item data: {list(item.keys())} - ID: {item.get('position_id', 'NO_ID')}")
            
            table = self.get_table(table_name)
            logger.info(f"✅ Got table reference for '{table_name}'")
            
            table.put_item(Item=item)
            logger.info(f"✅ Successfully saved item to '{table_name}' - ID: {item.get('position_id', 'NO_ID')}")
            return True
        except Exception as e:
            logger.error(f"❌ Error putting item in {table_name}: {e}")
            logger.error(f"📝 Item keys that failed: {list(item.keys()) if item else 'None'}")
            return False
    
    def get_item(self, table_name: str, key: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get an item from DynamoDB table"""
        try:
            table = self.get_table(table_name)
            response = table.get_item(Key=key)
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
    
    def query_items(self, table_name: str, key_condition: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Query items from DynamoDB table"""
        try:
            table = self.get_table(table_name)
            # Simple implementation - can be expanded
            response = table.scan()  # For now, just scan and filter
            items = response.get('Items', [])
            
            # Basic filtering
            filtered_items = []
            for item in items:
                match = True
                for key, value in key_condition.items():
                    if item.get(key) != value:
                        match = False
                        break
                if match:
                    filtered_items.append(item)
            
            return filtered_items
        except Exception as e:
            logger.error(f"Error querying table {table_name}: {e}")
            return []


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
                {'AttributeName': 'SK', 'AttributeType': 'S'},
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
                    'Projection': {'ProjectionType': 'ALL'},
                    'BillingMode': 'PAY_PER_REQUEST'
                },
                {
                    'IndexName': 'HourIndex',
                    'KeySchema': [
                        {'AttributeName': 'hour', 'KeyType': 'HASH'},
                        {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'BillingMode': 'PAY_PER_REQUEST'
                }
            ],
            'BillingMode': 'PAY_PER_REQUEST',
            'StreamSpecification': {
                'StreamEnabled': True,
                'StreamViewType': 'NEW_AND_OLD_IMAGES'
            },
            'TimeToLiveSpecification': {
                'AttributeName': 'TTL',
                'Enabled': True
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
                    'Projection': {'ProjectionType': 'ALL'},
                    'BillingMode': 'PAY_PER_REQUEST'
                },
                {
                    'IndexName': 'DateConfidenceIndex',
                    'KeySchema': [
                        {'AttributeName': 'GSI2PK', 'KeyType': 'HASH'},
                        {'AttributeName': 'GSI2SK', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'BillingMode': 'PAY_PER_REQUEST'
                }
            ],
            'BillingMode': 'PAY_PER_REQUEST',
            'StreamSpecification': {
                'StreamEnabled': True,
                'StreamViewType': 'NEW_AND_OLD_IMAGES'
            },
            'TimeToLiveSpecification': {
                'AttributeName': 'TTL',
                'Enabled': True
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
                    'Projection': {'ProjectionType': 'ALL'},
                    'BillingMode': 'PAY_PER_REQUEST'
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
                    'Projection': {'ProjectionType': 'ALL'},
                    'BillingMode': 'PAY_PER_REQUEST'
                },
                {
                    'IndexName': 'SymbolDateIndex',
                    'KeySchema': [
                        {'AttributeName': 'GSI2PK', 'KeyType': 'HASH'},
                        {'AttributeName': 'GSI2SK', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'BillingMode': 'PAY_PER_REQUEST'
                }
            ],
            'BillingMode': 'PAY_PER_REQUEST',
            'StreamSpecification': {
                'StreamEnabled': True,
                'StreamViewType': 'NEW_AND_OLD_IMAGES'
            },
            'TimeToLiveSpecification': {
                'AttributeName': 'TTL',
                'Enabled': True
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
                    'Projection': {'ProjectionType': 'ALL'},
                    'BillingMode': 'PAY_PER_REQUEST'
                },
                {
                    'IndexName': 'StatusIndex',
                    'KeySchema': [
                        {'AttributeName': 'GSI2PK', 'KeyType': 'HASH'},
                        {'AttributeName': 'GSI2SK', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'BillingMode': 'PAY_PER_REQUEST'
                }
            ],
            'BillingMode': 'PAY_PER_REQUEST',
            'StreamSpecification': {
                'StreamEnabled': True,
                'StreamViewType': 'NEW_AND_OLD_IMAGES'
            },
            'TimeToLiveSpecification': {
                'AttributeName': 'TTL',
                'Enabled': True
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
                    'Projection': {'ProjectionType': 'ALL'},
                    'BillingMode': 'PAY_PER_REQUEST'
                }
            ],
            'BillingMode': 'PAY_PER_REQUEST',
            'StreamSpecification': {
                'StreamEnabled': True,
                'StreamViewType': 'NEW_AND_OLD_IMAGES'
            },
            'TimeToLiveSpecification': {
                'AttributeName': 'TTL',
                'Enabled': True
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
                    'Projection': {'ProjectionType': 'ALL'},
                    'BillingMode': 'PAY_PER_REQUEST'
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
                    'Projection': {'ProjectionType': 'ALL'},
                    'BillingMode': 'PAY_PER_REQUEST'
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
                    'Projection': {'ProjectionType': 'ALL'},
                    'BillingMode': 'PAY_PER_REQUEST'
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

    def get_users_enhanced_schema() -> Dict[str, Any]:
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

    def get_invitations_schema() -> Dict[str, Any]:
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

    def get_user_activity_logs_schema() -> Dict[str, Any]:
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
            self.schemas.get_notification_templates_schema()
        ]
        
        success = True
        for config in table_configs:
            try:
                # Check if table exists
                table = self.client.get_table(config['TableName'])
                logger.info(f"Table {config['TableName']} already exists")
            except:
                # Create table if it doesn't exist
                logger.info(f"Creating table {config['TableName']}")
                if not self.client.create_table(config):
                    success = False
        
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

# Initialize database manager
db_manager = DatabaseManager() 

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