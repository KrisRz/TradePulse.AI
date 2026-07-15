"""
TradePulse.AI - ML Model Updater Lambda Handler
Continuous Learning and Model Updates
"""

import os
import sys
import json
import logging
import boto3
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handler(event, context):
    """
    Lambda handler for ML model updates
    Triggered daily for model retraining and updates
    """
    try:
        logger.info("🤖 ML Model Updater Lambda triggered")
        
        # Import services after path setup
        from app.services.database import DatabaseService
        from app.services.continuous_learning_engine import ContinuousLearningEngine
        from app.services.model_loader import ModelLoader
        
        # Initialize services
        db_service = DatabaseService()
        learning_engine = ContinuousLearningEngine()
        model_loader = ModelLoader()
        
        # Check if model update is needed
        last_update = get_last_model_update(db_service)
        hours_since_update = (datetime.now(timezone.utc) - last_update).total_seconds() / 3600
        
        if hours_since_update < 24:
            logger.info(f"⏭️ Model updated {hours_since_update:.1f}h ago, skipping update")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'status': 'skipped',
                    'reason': 'Recent update exists',
                    'hours_since_update': hours_since_update,
                    'function': 'ml_model_updater'
                })
            }
        
        # Collect training data from recent trades
        training_data = collect_recent_training_data(db_service)
        
        if len(training_data) < 100:  # Minimum data threshold
            logger.warning(f"Insufficient training data: {len(training_data)} samples")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'status': 'skipped',
                    'reason': 'Insufficient training data',
                    'samples_available': len(training_data),
                    'function': 'ml_model_updater'
                })
            }
        
        # Perform incremental model update
        update_results = learning_engine.incremental_update(training_data)
        
        # Upload updated models to S3
        model_s3_bucket = os.environ.get('MODEL_S3_BUCKET')
        if model_s3_bucket and update_results.get('success'):
            upload_models_to_s3(model_s3_bucket, update_results.get('models', {}))
        
        # Log model performance metrics
        performance_metrics = {
            'metric_id': f"model_update_{int(datetime.now(timezone.utc).timestamp())}",
            'model_type': 'enterprise_6layer',
            'date': datetime.now(timezone.utc).date().isoformat(),
            'timestamp': int(datetime.now(timezone.utc).timestamp()),
            'training_samples': len(training_data),
            'accuracy_improvement': update_results.get('accuracy_improvement', 0),
            'precision_improvement': update_results.get('precision_improvement', 0),
            'training_duration_seconds': update_results.get('training_duration', 0),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        
        db_service.put_item('model_performance_metrics', performance_metrics)
        
        # Record model update
        model_update_record = {
            'update_id': f"update_{int(datetime.now(timezone.utc).timestamp())}",
            'timestamp': int(datetime.now(timezone.utc).timestamp()),
            'model_version': update_results.get('model_version', '1.0'),
            'training_samples': len(training_data),
            'performance_metrics': performance_metrics,
            'update_type': 'incremental',
            'success': update_results.get('success', False),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        
        db_service.put_item('model_updates', model_update_record)
        
        # Return response
        response = {
            'statusCode': 200,
            'body': json.dumps({
                'status': 'success',
                'training_samples': len(training_data),
                'accuracy_improvement': update_results.get('accuracy_improvement', 0),
                'model_version': update_results.get('model_version', '1.0'),
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'function': 'ml_model_updater'
            })
        }
        
        logger.info(f"✅ ML model update completed: {len(training_data)} samples")
        return response
        
    except Exception as e:
        logger.error(f"❌ ML Model Updater Lambda error: {e}")
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'status': 'error',
                'message': str(e),
                'function': 'ml_model_updater',
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        }

def get_last_model_update(db_service):
    """Get timestamp of last model update"""
    try:
        recent_updates = db_service.scan_table('model_updates', {}, limit=1)
        if recent_updates:
            last_timestamp = recent_updates[0].get('timestamp', 0)
            return datetime.fromtimestamp(float(last_timestamp), tz=timezone.utc)
        else:
            # Default to 7 days ago if no updates found
            return datetime.now(timezone.utc) - timedelta(days=7)
    except Exception as e:
        logger.error(f"Error getting last model update: {e}")
        return datetime.now(timezone.utc) - timedelta(days=1)

def collect_recent_training_data(db_service):
    """Collect recent trading data for model training"""
    try:
        # Get closed positions from last 7 days
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        
        recent_positions = db_service.scan_table('positions', {
            'status': 'closed'
        })
        
        training_samples = []
        
        for position in recent_positions:
            try:
                close_time = position.get('closed_at')
                if close_time and datetime.fromisoformat(close_time.replace('Z', '+00:00')) > seven_days_ago:
                    
                    # Create training sample
                    sample = {
                        'symbol': position.get('symbol', 'BTCUSDT'),
                        'entry_price': float(position.get('entry_price', 0)),
                        'exit_price': float(position.get('exit_price', 0)),
                        'pnl_percent': float(position.get('pnl_percent', 0)),
                        'holding_duration': position.get('holding_duration_hours', 0),
                        'signal_confidence': position.get('signal_confidence', 0.5),
                        'market_conditions': position.get('market_conditions', {}),
                        'outcome': 'profit' if float(position.get('pnl_percent', 0)) > 0 else 'loss'
                    }
                    
                    training_samples.append(sample)
                    
            except Exception as e:
                logger.error(f"Error processing position for training: {e}")
                continue
        
        logger.info(f"Collected {len(training_samples)} training samples")
        return training_samples
        
    except Exception as e:
        logger.error(f"Error collecting training data: {e}")
        return []

def upload_models_to_s3(bucket_name, models):
    """Upload updated models to S3"""
    try:
        s3 = boto3.client('s3')
        
        for model_name, model_data in models.items():
            s3_key = f"models/{model_name}/{datetime.now(timezone.utc).strftime('%Y/%m/%d')}/{model_name}.pkl"
            
            # Upload model to S3
            s3.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=model_data,
                ServerSideEncryption='aws:kms'
            )
            
            logger.info(f"✅ Uploaded {model_name} to S3: s3://{bucket_name}/{s3_key}")
        
    except Exception as e:
        logger.error(f"❌ Failed to upload models to S3: {e}")

# For local testing
if __name__ == "__main__":
    test_event = {"source": "test"}
    test_context = {"function_name": "test"}
    result = handler(test_event, test_context)
    print(json.dumps(result, indent=2))
