#!/usr/bin/env python3
"""
Enterprise DynamoDB Schema Builder
=================================

Builds the complete enterprise-grade DynamoDB Local schema as planned in database.py
Creates all 22+ tables with proper schemas, GSIs, TTL, and enterprise features.

Usage: python3 scripts/build_enterprise_schema.py
"""

import sys
import os
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent / "app" / "backend"))

from core.database import DatabaseManager, DynamoDBClient
import structlog
from datetime import datetime

logger = structlog.get_logger(__name__)

def main():
    """Build complete enterprise schema"""
    print("🏗️ BUILDING COMPLETE ENTERPRISE DYNAMODB SCHEMA")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    try:
        # Initialize database manager for local development
        print("🔧 Initializing DatabaseManager...")
        db_manager = DatabaseManager(local_development=True)
        
        # Get current state
        current_tables = set(db_manager.client.dynamodb.meta.client.list_tables()['TableNames'])
        print(f"📊 Current tables: {len(current_tables)}")
        
        print("\n🚀 Starting enterprise table creation...")
        print("This will create all tables defined in database.py TableSchemas")
        print()
        
        # Track creation progress
        created_count = 0
        skipped_count = 0
        failed_count = 0
        
        # Get all schema methods from TableSchemas
        schema_methods = [
            ('live_candles', db_manager.schemas.get_live_candles_schema),
            ('trading_signals', db_manager.schemas.get_signals_schema),
            ('training_data', db_manager.schemas.get_training_data_schema),
            ('exit_analysis_log', db_manager.schemas.get_exit_analysis_log_schema),
            ('position_monitoring_log', db_manager.schemas.get_position_monitoring_log_schema),
            ('trade_execution_metrics', db_manager.schemas.get_trade_execution_metrics_schema),
            ('alert_notifications', db_manager.schemas.get_alert_notifications_schema),
            ('tradepulse-users', db_manager.schemas.get_users_schema),
            ('tradepulse-virtual-portfolios', db_manager.schemas.get_virtual_portfolios_schema),
            ('ai_vs_random_experiments', db_manager.schemas.get_ai_vs_random_experiments_schema),
            ('signal_accuracy_tracking', db_manager.schemas.get_signal_accuracy_tracking_schema),
            ('trading_patterns', db_manager.schemas.get_trading_patterns_schema),
            ('user_performance_showcases', db_manager.schemas.get_user_performance_showcases_schema),
            ('model_performance_metrics', db_manager.schemas.get_model_performance_metrics_schema),
            ('users_enhanced', db_manager.schemas.get_users_enhanced_schema),
            ('invitations', db_manager.schemas.get_invitations_schema),
            ('user_activity_logs', db_manager.schemas.get_user_activity_logs_schema),
            ('messages', db_manager.schemas.get_messages_schema),
            ('message_deliveries', db_manager.schemas.get_message_deliveries_schema),
            ('announcements', db_manager.schemas.get_announcements_schema),
            ('user_notification_preferences', db_manager.schemas.get_user_notification_preferences_schema),
            ('notification_templates', db_manager.schemas.get_notification_templates_schema)
        ]
        
        # Create each table
        for table_name, schema_method in schema_methods:
            try:
                print(f"📋 Processing: {table_name}")
                
                # Check if table already exists
                try:
                    table = db_manager.client.get_table(table_name)
                    print(f"   ✅ Already exists: {table_name}")
                    skipped_count += 1
                    continue
                except:
                    pass
                
                # Get schema and create table
                schema = schema_method()
                print(f"   🔨 Creating: {table_name}")
                
                success = db_manager.client.create_table(schema)
                if success:
                    print(f"   ✅ Created: {table_name}")
                    created_count += 1
                else:
                    print(f"   ❌ Failed: {table_name}")
                    failed_count += 1
                    
            except Exception as e:
                print(f"   ❌ Error creating {table_name}: {e}")
                failed_count += 1
        
        print("\n" + "=" * 60)
        print("📈 ENTERPRISE SCHEMA BUILD SUMMARY:")
        print(f"✅ Created: {created_count} tables")
        print(f"⏭️  Skipped: {skipped_count} tables (already exist)")
        print(f"❌ Failed: {failed_count} tables")
        
        # Get final state
        final_tables = set(db_manager.client.dynamodb.meta.client.list_tables()['TableNames'])
        print(f"📊 Total tables: {len(final_tables)} (was {len(current_tables)})")
        
        # Show new tables
        new_tables = final_tables - current_tables
        if new_tables:
            print(f"\n🆕 New tables created ({len(new_tables)}):")
            for table in sorted(new_tables):
                print(f"   + {table}")
        
        # Enterprise features summary
        print("\n🏢 ENTERPRISE FEATURES NOW AVAILABLE:")
        print("✅ AI/ML Pipeline: signal_accuracy_tracking, trading_patterns, model_performance_metrics")
        print("✅ User Management: users_enhanced, invitations, user_activity_logs")
        print("✅ Communication: messages, message_deliveries, announcements, notification_templates")
        print("✅ Marketing: user_performance_showcases, ai_vs_random_experiments")
        print("✅ Advanced Monitoring: exit_analysis_log, position_monitoring_log, trade_execution_metrics")
        print("✅ Alert System: alert_notifications with multi-channel support")
        
        if failed_count == 0:
            print("\n🎉 ENTERPRISE SCHEMA BUILD COMPLETED SUCCESSFULLY!")
            print("Your DynamoDB Local now matches the full database.py specification")
        else:
            print(f"\n⚠️ Build completed with {failed_count} failures")
            print("Some enterprise features may not be available")
        
        return failed_count == 0
        
    except Exception as e:
        print(f"\n❌ Enterprise schema build failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
