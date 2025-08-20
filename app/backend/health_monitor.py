"""
TradePulse.AI - Health Monitor Lambda Handler (Fixed)
System Health Monitoring and Alerting
"""

import os
import sys
import json
import logging
import boto3
from datetime import datetime, timezone
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handler(event, context):
    """
    Lambda handler for system health monitoring
    Triggered by EventBridge every 5 minutes
    """
    try:
        logger.info("🏥 Health Monitor Lambda triggered")
        
        # Import services after path setup (FIXED: removed app. prefix)
        from app.backend.services import DatabaseService
        
        # Initialize services
        db_service = DatabaseService()
        
        # Health check results
        health_results = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'checks': {}
        }
        
        # 1. Database connectivity check
        try:
            test_result = db_service.health_check()
            health_results['checks']['database'] = {
                'status': 'healthy' if test_result else 'unhealthy',
                'message': 'Database connection OK' if test_result else 'Database connection failed'
            }
        except Exception as e:
            health_results['checks']['database'] = {
                'status': 'unhealthy',
                'message': f'Database error: {str(e)}'
            }
        
        # 2. Recent signal generation check
        try:
            # Check for recent signals (last 30 minutes)
            recent_signals = db_service.scan_table('signals', {
                'timestamp': {
                    'gte': int((datetime.now(timezone.utc).timestamp() - 1800))
                }
            }, limit=1)
            
            health_results['checks']['signal_generation'] = {
                'status': 'healthy' if recent_signals else 'warning',
                'message': f'Recent signals found: {len(recent_signals)}' if recent_signals else 'No recent signals'
            }
        except Exception as e:
            health_results['checks']['signal_generation'] = {
                'status': 'unhealthy',
                'message': f'Signal check error: {str(e)}'
            }
        
        # 3. Lambda function status check
        try:
            lambda_client = boto3.client('lambda', region_name='eu-west-2')
            
            # Check main backend Lambda
            backend_function = lambda_client.get_function(FunctionName='tradepulse-backend-api-production')
            health_results['checks']['backend_lambda'] = {
                'status': 'healthy' if backend_function['Configuration']['State'] == 'Active' else 'unhealthy',
                'message': f"Backend Lambda state: {backend_function['Configuration']['State']}"
            }
        except Exception as e:
            health_results['checks']['backend_lambda'] = {
                'status': 'unhealthy',
                'message': f'Backend Lambda check error: {str(e)}'
            }
        
        # 4. API Gateway health check
        try:
            import requests
            api_response = requests.get(
                'https://hi3b3e4y7a.execute-api.eu-west-2.amazonaws.com/production/api/health',
                timeout=10
            )
            health_results['checks']['api_gateway'] = {
                'status': 'healthy' if api_response.status_code == 200 else 'unhealthy',
                'message': f'API Gateway response: {api_response.status_code}'
            }
        except Exception as e:
            health_results['checks']['api_gateway'] = {
                'status': 'unhealthy',
                'message': f'API Gateway check error: {str(e)}'
            }
        
        # 5. CloudFront distribution check
        try:
            cloudfront_client = boto3.client('cloudfront')
            distribution = cloudfront_client.get_distribution(Id='E2T06EN7O486LG')
            health_results['checks']['cloudfront'] = {
                'status': 'healthy' if distribution['Distribution']['Status'] == 'Deployed' else 'warning',
                'message': f"CloudFront status: {distribution['Distribution']['Status']}"
            }
        except Exception as e:
            health_results['checks']['cloudfront'] = {
                'status': 'unhealthy',
                'message': f'CloudFront check error: {str(e)}'
            }
        
        # Calculate overall status
        statuses = [check['status'] for check in health_results['checks'].values()]
        if all(status == 'healthy' for status in statuses):
            overall_status = 'healthy'
        elif any(status == 'unhealthy' for status in statuses):
            overall_status = 'unhealthy'
        else:
            overall_status = 'warning'
        
        # Send alerts if unhealthy
        if overall_status == 'unhealthy':
            try:
                send_health_alert(health_results)
            except Exception as e:
                logger.error(f"Failed to send health alert: {e}")
        
        # Store health check results
        health_record = {
            'check_id': f"health_{int(datetime.now(timezone.utc).timestamp())}",
            'timestamp': int(datetime.now(timezone.utc).timestamp()),
            'overall_status': overall_status,
            'checks': health_results['checks'],
            'checked_at': health_results['timestamp']
        }
        
        try:
            db_service.put_item('health_checks', health_record)
        except Exception as e:
            logger.error(f"Failed to store health check: {e}")
        
        # Return response
        response = {
            'statusCode': 200,
            'body': json.dumps({
                'status': 'success',
                'health_status': overall_status,
                'checks_performed': len(health_results['checks']),
                'timestamp': health_results['timestamp'],
                'function': 'health_monitor'
            })
        }
        
        logger.info(f"✅ Health monitoring completed: {overall_status}")
        return response
        
    except Exception as e:
        logger.error(f"❌ Health Monitor Lambda error: {e}")
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'status': 'error',
                'message': str(e),
                'function': 'health_monitor',
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        }

def send_health_alert(health_results):
    """Send health alert via SNS"""
    try:
        sns_client = boto3.client('sns', region_name='eu-west-2')
        
        # Create alert message
        unhealthy_checks = [
            f"- {name}: {check['message']}"
            for name, check in health_results['checks'].items()
            if check['status'] == 'unhealthy'
        ]
        
        message = f"""
🚨 TradePulse.AI Health Alert

System Status: UNHEALTHY
Timestamp: {health_results['timestamp']}

Failed Checks:
{chr(10).join(unhealthy_checks)}

Please investigate immediately.
"""
        
        # Send to SNS topic (if configured)
        topic_arn = os.environ.get('HEALTH_ALERT_SNS_TOPIC')
        if topic_arn:
            sns_client.publish(
                TopicArn=topic_arn,
                Message=message,
                Subject='TradePulse.AI Health Alert'
            )
            logger.info("Health alert sent via SNS")
        else:
            logger.warning("No SNS topic configured for health alerts")
            
    except Exception as e:
        logger.error(f"Failed to send health alert: {e}")
