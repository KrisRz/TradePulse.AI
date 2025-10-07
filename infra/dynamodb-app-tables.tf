# Additional DynamoDB tables required by TradePulse.AI application
# These tables are created with local DynamoDB but missing from AWS
# Generated to match app/backend/core/database.py TableSchemas


# Trading decisions audit log - CRITICAL for decision tracking
resource "aws_dynamodb_table" "trading_decisions" {
  name         = "trading_decisions"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "decision_id"
  range_key    = "timestamp"

  attribute {
    name = "decision_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "N"
  }

  attribute {
    name = "day"
    type = "S"
  }

  # GSI for querying decisions by day
  global_secondary_index {
    name            = "DayIndex"
    hash_key        = "day"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = {
    Name        = "${var.project_name}-trading-decisions"
    Environment = "production"
  }
}

# Market data persistence - stores real-time candle data
resource "aws_dynamodb_table" "market_data" {
  name         = "tradepulse_market_data"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "symbol"
  range_key    = "timestamp"

  attribute {
    name = "symbol"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "N"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = {
    Name        = "${var.project_name}-market-data"
    Environment = "production"
  }
}

# Runtime table - for lease guard and singleton coordination
resource "aws_dynamodb_table" "runtime" {
  name         = "runtime"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  range_key    = "sk"

  attribute {
    name = "pk"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = {
    Name        = "${var.project_name}-runtime"
    Environment = "production"
  }
}

# Live candles table for real-time market data (local/development)
resource "aws_dynamodb_table" "live_candles" {
  name         = "live_candles"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "symbol"
  range_key    = "timestamp"

  attribute {
    name = "symbol"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "N"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = {
    Name = "${var.project_name}-live-candles"
  }
}

# Live candles table for production (separate table for env isolation)
resource "aws_dynamodb_table" "live_candles_production" {
  name         = "tradepulse-live_candles-production"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "symbol"
  range_key    = "timestamp"

  attribute {
    name = "symbol"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "N"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = {
    Name        = "${var.project_name}-live-candles-production"
    Environment = "production"
  }
}

# Trading signals table
resource "aws_dynamodb_table" "trading_signals" {
  name         = "trading_signals"
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

  global_secondary_index {
    name            = "symbol-timestamp-index"
    hash_key        = "symbol"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  tags = {
    Name = "${var.project_name}-trading-signals"
  }
}

# Training data table for ML models
resource "aws_dynamodb_table" "training_data" {
  name         = "training_data"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "data_id"

  attribute {
    name = "data_id"
    type = "S"
  }

  tags = {
    Name = "${var.project_name}-training-data"
  }
}

# Exit analysis log
resource "aws_dynamodb_table" "exit_analysis_log" {
  name         = "exit_analysis_log"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "position_id"
  range_key    = "timestamp"

  attribute {
    name = "position_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "N"
  }

  tags = {
    Name = "${var.project_name}-exit-analysis-log"
  }
}

# Position monitoring log
resource "aws_dynamodb_table" "position_monitoring_log" {
  name         = "position_monitoring_log"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "position_id"
  range_key    = "check_timestamp"

  attribute {
    name = "position_id"
    type = "S"
  }

  attribute {
    name = "check_timestamp"
    type = "N"
  }

  tags = {
    Name = "${var.project_name}-position-monitoring"
  }
}

# Trade execution metrics
resource "aws_dynamodb_table" "trade_execution_metrics" {
  name         = "trade_execution_metrics"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "trade_id"
  range_key    = "timestamp"

  attribute {
    name = "trade_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "N"
  }

  tags = {
    Name = "${var.project_name}-trade-execution-metrics"
  }
}

# Alert notifications
resource "aws_dynamodb_table" "alert_notifications" {
  name         = "alert_notifications"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "alert_id"
  range_key    = "timestamp"

  attribute {
    name = "alert_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "N"
  }

  tags = {
    Name = "${var.project_name}-alert-notifications"
  }
}

# Users table
resource "aws_dynamodb_table" "users" {
  name         = "tradepulse-users"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id"

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "email"
    type = "S"
  }

  global_secondary_index {
    name            = "email-index"
    hash_key        = "email"
    projection_type = "ALL"
  }

  tags = {
    Name = "${var.project_name}-users"
  }
}

# Virtual portfolios table
resource "aws_dynamodb_table" "virtual_portfolios" {
  name         = "virtual_portfolios"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id"

  attribute {
    name = "user_id"
    type = "S"
  }

  tags = {
    Name = "${var.project_name}-virtual-portfolios"
  }
}

# AI vs Random experiments
resource "aws_dynamodb_table" "ai_vs_random_experiments" {
  name         = "ai_vs_random_experiments"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "experiment_id"

  attribute {
    name = "experiment_id"
    type = "S"
  }

  tags = {
    Name = "${var.project_name}-ai-vs-random"
  }
}

# Signal accuracy tracking
resource "aws_dynamodb_table" "signal_accuracy_tracking" {
  name         = "signal_accuracy_tracking"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "signal_id"

  attribute {
    name = "signal_id"
    type = "S"
  }

  tags = {
    Name = "${var.project_name}-signal-accuracy"
  }
}

# Trading patterns
resource "aws_dynamodb_table" "trading_patterns" {
  name         = "trading_patterns"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pattern_id"

  attribute {
    name = "pattern_id"
    type = "S"
  }

  tags = {
    Name = "${var.project_name}-trading-patterns"
  }
}

# User performance showcases
resource "aws_dynamodb_table" "user_performance_showcases" {
  name         = "user_performance_showcases"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id"
  range_key    = "showcase_id"

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "showcase_id"
    type = "S"
  }

  tags = {
    Name = "${var.project_name}-user-showcases"
  }
}

# Model performance metrics
resource "aws_dynamodb_table" "model_performance_metrics" {
  name         = "model_performance_metrics"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "model_id"
  range_key    = "timestamp"

  attribute {
    name = "model_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "N"
  }

  tags = {
    Name = "${var.project_name}-model-performance"
  }
}

# Users enhanced table
resource "aws_dynamodb_table" "users_enhanced" {
  name         = "users_enhanced"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id"

  attribute {
    name = "user_id"
    type = "S"
  }

  tags = {
    Name = "${var.project_name}-users-enhanced"
  }
}

# Invitations table
resource "aws_dynamodb_table" "invitations" {
  name         = "invitations"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "invitation_id"

  attribute {
    name = "invitation_id"
    type = "S"
  }

  tags = {
    Name = "${var.project_name}-invitations"
  }
}

# User activity logs
resource "aws_dynamodb_table" "user_activity_logs" {
  name         = "user_activity_logs"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id"
  range_key    = "timestamp"

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "N"
  }

  tags = {
    Name = "${var.project_name}-user-activity"
  }
}

# Messages table
resource "aws_dynamodb_table" "messages" {
  name         = "messages"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "message_id"

  attribute {
    name = "message_id"
    type = "S"
  }

  tags = {
    Name = "${var.project_name}-messages"
  }
}

# Message deliveries
resource "aws_dynamodb_table" "message_deliveries" {
  name         = "message_deliveries"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "delivery_id"

  attribute {
    name = "delivery_id"
    type = "S"
  }

  tags = {
    Name = "${var.project_name}-message-deliveries"
  }
}

# Announcements
resource "aws_dynamodb_table" "announcements" {
  name         = "announcements"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "announcement_id"

  attribute {
    name = "announcement_id"
    type = "S"
  }

  tags = {
    Name = "${var.project_name}-announcements"
  }
}

# User notification preferences
resource "aws_dynamodb_table" "user_notification_preferences" {
  name         = "user_notification_preferences"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id"

  attribute {
    name = "user_id"
    type = "S"
  }

  tags = {
    Name = "${var.project_name}-notification-prefs"
  }
}

# Notification templates
resource "aws_dynamodb_table" "notification_templates" {
  name         = "notification_templates"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "template_id"

  attribute {
    name = "template_id"
    type = "S"
  }

  tags = {
    Name = "${var.project_name}-notification-templates"
  }
}

# Health checks table
resource "aws_dynamodb_table" "health_checks" {
  name         = "health_checks"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "check_id"
  range_key    = "timestamp"

  attribute {
    name = "check_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "N"
  }

  tags = {
    Name = "${var.project_name}-health-checks"
  }
}

# Trade analyses table
resource "aws_dynamodb_table" "trade_analyses" {
  name         = "trade_analyses"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "trade_id"
  range_key    = "analysis_timestamp"

  attribute {
    name = "trade_id"
    type = "S"
  }

  attribute {
    name = "analysis_timestamp"
    type = "N"
  }

  tags = {
    Name = "${var.project_name}-trade-analyses"
  }
}

# Emergency state - CRITICAL for emergency controls and circuit breakers
resource "aws_dynamodb_table" "emergency_state" {
  name         = "emergency_state"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = {
    Name        = "${var.project_name}-emergency-state"
    Environment = "production"
    Critical    = "true"
  }
}

# Portfolio active positions - CRITICAL for trading operations
resource "aws_dynamodb_table" "portfolio_positions" {
  name         = "portfolio_positions"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id"
  range_key    = "position_id"

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "position_id"
    type = "S"
  }

  attribute {
    name = "symbol"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  # GSI for querying positions by symbol
  global_secondary_index {
    name            = "SymbolIndex"
    hash_key        = "symbol"
    range_key       = "status"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = {
    Name        = "${var.project_name}-portfolio-positions"
    Environment = "production"
    Critical    = "true"
  }
}

# Portfolio closed positions - CRITICAL for performance tracking
resource "aws_dynamodb_table" "portfolio_closed_positions" {
  name         = "portfolio_closed_positions"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id"
  range_key    = "position_id"

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "position_id"
    type = "S"
  }

  attribute {
    name = "symbol"
    type = "S"
  }

  attribute {
    name = "closed_at"
    type = "S"
  }

  # GSI for querying closed positions by symbol
  global_secondary_index {
    name            = "SymbolClosedIndex"
    hash_key        = "symbol"
    range_key       = "closed_at"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = {
    Name        = "${var.project_name}-portfolio-closed-positions"
    Environment = "production"
    Critical    = "true"
  }
}

# Virtual portfolios - HIGH priority for virtual portfolio trading
resource "aws_dynamodb_table" "virtual_portfolios" {
  name         = "tradepulse-virtual-portfolios"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id"

  attribute {
    name = "user_id"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = {
    Name        = "${var.project_name}-virtual-portfolios"
    Environment = "production"
  }
}
