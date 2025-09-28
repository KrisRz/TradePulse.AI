# TradePulse.AI Trading Configuration

## Overview

This folder contains **simplified trading configuration** for TradePulse.AI. The configuration has been streamlined to focus only on core trading parameters that affect AI behavior and risk management.

> **Note**: Infrastructure settings (database, networking) are managed separately from trading configuration.

## Configuration Files Structure

```
config/
├── README.md                 # This documentation
└── trading-config.yaml      # Core trading parameters and risk management
```

## Configuration Philosophy

**What's included**: Core trading logic, AI thresholds, risk management
**What's removed**: Infrastructure settings (managed separately), duplicated environment configs

The configuration focuses on parameters that directly affect:
- ✅ **Trading signals generation**
- ✅ **AI confidence thresholds** 
- ✅ **Position sizing and risk management**
- ✅ **Performance targets and optimization**

## Configuration Sections

### 1. Signal Processing Configuration (`signal_processing`)

Controls AI signal generation timing and error handling.

```yaml
signal_processing:
  signal_interval_seconds: 180          # 3 minutes for aggressive day trading
  ai_processing_timeout_seconds: 60.0   # AI model processing timeout
  target_move_usd: 500.0               # Target Bitcoin move size ($500+)
  signals_per_hour_expected: 20         # Expected signals per hour (60/3)
```

**Key Parameters:**
- **signal_interval_seconds**: Currently hardcoded to 180s (3 minutes) in the application
- **target_move_usd**: The minimum Bitcoin price movement to trigger signals
- **signals_per_hour_expected**: Performance benchmark for monitoring

### 2. Trading Engine Configuration (`trading_engine`)

The core AI trading decision parameters.

```yaml
trading_engine:
  min_confidence_threshold: 0.45      # Minimum AI confidence (0.0-1.0)
  consensus_threshold: 0.35           # Minimum consensus between models (0.0-1.0)
  max_position_size_percentage: 20.0  # 20% maximum position size
  min_position_size_percentage: 3.0   # 3% minimum position size
  stop_loss_percentage: 2.0           # 2% stop loss
  take_profit_percentage: 3.0         # 3% take profit
  max_daily_positions: 20             # Maximum positions per day
```

**Key Parameters:**
- **min_confidence_threshold**: Higher = fewer but more confident trades (0.45 = 45% confidence)
- **consensus_threshold**: Agreement level between AI models (0.35 = 35% consensus)
- **position sizing**: Controls risk per trade (3%-20% of portfolio)
- **stop_loss/take_profit**: Automatic risk management (2% loss, 3% profit targets)

### 3. Performance Configuration (`performance`)

Controls system performance and resource usage.

```yaml
performance:
  # Memory management
  cache_size: 2000                    # Max cache entries (100-10000)
  memory_limit_mb: 4096               # Memory limit in MB (1024-32768)
  gc_interval_seconds: 300            # Garbage collection interval (30-3600s)
  
  # Monitoring
  performance_log_interval: 60        # Performance logging interval (15-600s)
  enable_profiling: false             # Enable performance profiling
```

**Key Parameters:**
- **cache_size**: Number of items to cache. Higher = better performance but more memory.
- **memory_limit_mb**: System memory limit. Should be set based on available RAM.
- **gc_interval_seconds**: How often to run garbage collection. Lower = more frequent cleanup.

### 4. Monitoring Configuration (`monitoring`)

Controls system health monitoring and alerting.

```yaml
monitoring:
  # Health checks
  health_check_interval: 30           # Health check frequency (10-300s)
  metrics_collection_interval: 15     # Metrics collection frequency (5-300s)
  
  # Alert thresholds
  alert_thresholds:
    memory_usage_percent: 85.0        # Memory usage alert threshold (50-95%)
    cpu_usage_percent: 80.0           # CPU usage alert threshold (50-95%)
    error_rate_percent: 10.0          # Error rate alert threshold (1-50%)
  
  # Logging
  enable_detailed_logging: true       # Enable detailed system logging
```

**Key Parameters:**
- **health_check_interval**: How often to check system health
- **alert_thresholds**: When to trigger alerts (lower = more sensitive)
- **enable_detailed_logging**: Toggle verbose logging (impacts performance)

### 5. Error Handling Configuration (`error_handling`)

Controls error recovery and resilience behavior.

```yaml
error_handling:
  # Retry behavior
  max_retry_attempts: 3               # Max retry attempts (1-10)
  retry_delay_seconds: 5.0            # Delay between retries (1-300s)
  
  # Circuit breaker
  circuit_breaker_failure_threshold: 5    # Failures before circuit opens (3-20)
  circuit_breaker_recovery_timeout: 60    # Recovery timeout seconds (30-600)
  
  # Recovery
  enable_automatic_recovery: true     # Enable automatic error recovery
```

**Key Parameters:**
- **max_retry_attempts**: How many times to retry failed operations
- **circuit_breaker_failure_threshold**: Failures before stopping attempts
- **enable_automatic_recovery**: Toggle automatic system recovery

## Environment-Specific Configurations

### Development Environment (`development.yaml`)

Optimized for development with:
- **Faster signal intervals** (60s vs 180s) for quick testing
- **Lower thresholds** for more frequent trading
- **Enhanced logging** for debugging
- **Smaller position sizes** for safety

### Production Environment (`production.yaml`)

Optimized for live trading with:
- **Conservative thresholds** for safety
- **Larger position sizes** for profitability
- **Performance optimizations** for speed
- **Comprehensive monitoring** for reliability

### Testing Environment (`testing.yaml`)

Optimized for automated testing with:
- **Very fast intervals** (10s) for quick test execution
- **Minimal logging** for speed
- **Isolated settings** to avoid interference

## Runtime Configuration Management

### API Endpoints

All configuration can be managed via REST API endpoints:

```bash
# Get current configuration
GET /admin/configuration/current

# Update configuration section
PUT /admin/configuration/update
{
  "section": "trading_engine",
  "updates": {
    "min_confidence_threshold": 0.50
  },
  "reason": "Increase confidence for better trades"
}

# View configuration change history
GET /admin/configuration/history?limit=50

# Reload configuration from files
POST /admin/configuration/reload

# Export configuration
GET /admin/configuration/export?format=yaml

# Get configuration schema
GET /admin/configuration/schema
```

### Configuration Updates

Updates are applied immediately without restart and include:
- **Validation** against schema before applying
- **Change tracking** with user and timestamp
- **Rollback capability** if needed
- **Callback notifications** to affected components

## Configuration Validation

The system automatically validates all configuration changes against a comprehensive schema:

### Validation Rules
- **Type checking**: Ensures correct data types (integer, number, boolean, string)
- **Range validation**: Enforces minimum/maximum values where applicable
- **Required fields**: Ensures all mandatory configuration is present
- **Cross-validation**: Checks relationships between related settings

### Common Validation Errors
```
signal_processing.signal_interval_seconds: Value 30 below minimum 60
trading_engine.min_confidence_threshold: Expected number, got string
performance.cache_size: Value 50 below minimum 100
```

## Best Practices

### 1. Configuration Changes
- **Always test** configuration changes in development first
- **Use meaningful reasons** when updating via API
- **Monitor system behavior** after changes
- **Keep backups** of working configurations

### 2. Environment Management
- **Development**: Use for testing new configurations safely
- **Production**: Make conservative changes, monitor closely
- **Testing**: Optimize for speed and isolation

### 3. Performance Tuning
- **Start conservative** with thresholds and gradually optimize
- **Monitor resource usage** when increasing cache sizes
- **Balance speed vs accuracy** with timeout settings
- **Use profiling** to identify bottlenecks

### 4. Troubleshooting
- **Check validation errors** if updates fail
- **Review change history** to identify problematic changes
- **Use schema endpoint** to understand valid ranges
- **Monitor logs** for configuration-related errors

## Configuration Examples

### High-Frequency Trading Setup
```yaml
signal_processing:
  signal_interval_seconds: 60          # 1-minute signals
  enable_pattern_analysis: false       # Disable for speed

trading_engine:
  min_confidence_threshold: 0.35       # Lower threshold for more trades
  max_daily_positions: 50              # Allow more positions
  max_hold_hours: 4                    # Shorter holds
```

### Conservative Trading Setup
```yaml 
signal_processing:
  signal_interval_seconds: 300         # 5-minute signals
  enable_pattern_analysis: true        # Full analysis

trading_engine:
  min_confidence_threshold: 0.65       # High confidence required
  max_daily_positions: 5               # Limit positions
  max_hold_hours: 48                   # Longer holds allowed
```

### Development Testing Setup
```yaml
signal_processing:
  signal_interval_seconds: 60          # Fast testing
  signal_timeout_seconds: 30.0         # Quick timeouts

trading_engine:
  max_position_size_percent: 5.0       # Small positions for safety
  max_daily_positions: 3               # Limit for testing
```

## Monitoring Configuration Health

### Key Metrics to Watch
- **Configuration validation success rate**: Should be 100%
- **Runtime update success rate**: Should be > 95%
- **Configuration reload frequency**: Monitor for excessive reloads
- **Validation error types**: Identify common configuration mistakes

### Alerts to Configure
- Configuration validation failures
- Failed configuration updates
- Excessive configuration changes
- Schema validation errors

## Migration and Deployment

### Deploying Configuration Changes
1. **Test in development environment**
2. **Validate configuration with schema**
3. **Apply changes via API with reason**
4. **Monitor system behavior**
5. **Rollback if issues detected**

### Deployment Considerations
- **Environment variables** override YAML settings
- **Configuration persistence** across application restarts
- **File-based configuration management**
- **Configuration backup and restore** procedures

## Support and Troubleshooting

### Common Issues
1. **Validation failures**: Check schema and value ranges
2. **Update failures**: Verify section names and property names
3. **Performance degradation**: Review resource limits and intervals
4. **Trading behavior changes**: Check threshold and position sizing changes

### Getting Help
- Check configuration schema via API: `GET /admin/configuration/schema`
- Review change history: `GET /admin/configuration/history`
- Validate current config: Check logs for validation messages
- Export current config: `GET /admin/configuration/export` for backup

### Configuration Backup
Always maintain backups of working configurations:
```bash
# Export current configuration
curl -X GET "http://localhost:9001/admin/configuration/export?format=yaml" \
  -H "Authorization: Bearer <token>" \
  > backup-$(date +%Y%m%d-%H%M%S).yaml
```

---

**Last Updated**: January 2025 - Phase 3.2 Configuration Management  
**Version**: 3.2.0  
**Author**: TradePulse.AI Development Team