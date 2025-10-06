# Missing DynamoDB Tables - Causing Deployment Rollbacks
# These tables are required by the application but missing from AWS

# =============================================================================
# PRIORITY 1: position_results (CRITICAL - Blocking Deployment!)
# =============================================================================
# Used by: continuous_learning_engine, intelligent_exit_engine, 
#          model_retraining_service, position_result_tracker
# Purpose: Stores closed position results for ML learning and optimization

resource "aws_dynamodb_table" "position_results" {
  name         = "position_results" # Match code usage (not tradepulse_ prefix)
  billing_mode = "PAY_PER_REQUEST"  # On-demand pricing (no capacity planning needed)
  hash_key     = "position_id"
  range_key    = "closed_at"

  attribute {
    name = "position_id"
    type = "S"
  }

  attribute {
    name = "closed_at"
    type = "N"
  }

  attribute {
    name = "symbol"
    type = "S"
  }

  # GSI for querying by symbol and time
  global_secondary_index {
    name            = "symbol-closed_at-index"
    hash_key        = "symbol"
    range_key       = "closed_at"
    projection_type = "ALL"
  }

  # TTL to auto-delete old results after 90 days
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = {
    Name        = "${var.project_name}-position-results"
    Environment = "production"
    Priority    = "critical"
    Purpose     = "ML learning and continuous optimization"
  }
}

# =============================================================================
# PRIORITY 2: trading_signals_v2 (MEDIUM - Degrades Model Retraining)
# =============================================================================
# Used by: model_retraining_service
# Purpose: Stores AI trading signals for model retraining and analysis

resource "aws_dynamodb_table" "trading_signals_v2" {
  name         = "trading_signals_v2" # Match code usage (not tradepulse_ prefix)
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "signal_id"
  range_key    = "timestamp"

  attribute {
    name = "signal_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "N"
  }

  attribute {
    name = "symbol"
    type = "S"
  }

  # GSI for querying signals by symbol and time
  global_secondary_index {
    name            = "symbol-timestamp-index"
    hash_key        = "symbol"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  # TTL to auto-delete old signals after 30 days
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = {
    Name        = "${var.project_name}-trading-signals-v2"
    Environment = "production"
    Priority    = "medium"
    Purpose     = "Model retraining and signal analysis"
  }
}

# =============================================================================
# PRIORITY 3: position_tracker_stats (LOW - Minor Impact)
# =============================================================================
# Used by: position_result_tracker
# Purpose: Tracks position tracker statistics (win rate, avg PnL, etc.)

resource "aws_dynamodb_table" "position_tracker_stats" {
  name         = "position_tracker_stats" # Match code usage (not tradepulse_ prefix)
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "tracker_id"

  attribute {
    name = "tracker_id"
    type = "S"
  }

  tags = {
    Name        = "${var.project_name}-position-tracker-stats"
    Environment = "production"
    Priority    = "low"
    Purpose     = "Position tracker statistics persistence"
  }
}

# =============================================================================
# OUTPUTS
# =============================================================================

output "position_results_table_name" {
  description = "Name of the position_results table"
  value       = aws_dynamodb_table.position_results.name
}

output "position_results_table_arn" {
  description = "ARN of the position_results table"
  value       = aws_dynamodb_table.position_results.arn
}

output "trading_signals_v2_table_name" {
  description = "Name of the trading_signals_v2 table"
  value       = aws_dynamodb_table.trading_signals_v2.name
}

output "position_tracker_stats_table_name" {
  description = "Name of the position_tracker_stats table"
  value       = aws_dynamodb_table.position_tracker_stats.name
}

# Note: Table names match code usage exactly (no tradepulse_ prefix) 
# to avoid ResourceNotFoundException errors
