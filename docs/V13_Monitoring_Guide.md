# V13 Monitoring Guide

## Overview

The V13 Adaptive Manual Trading Engine includes comprehensive monitoring capabilities to ensure system reliability, performance tracking, and operational visibility. This guide covers the monitoring components, logging systems, and dashboard features.

## Monitoring Components

### Session Logger

The Session Logger provides comprehensive activity tracking and timestamped logging for all system operations.

**Location:** `monitor/session_logger.py`

**Features:**
- System activity logging (startup, shutdown, sync operations)
- Trade execution logging with full details
- Doctrine switch tracking with reasoning
- Performance metrics logging
- Error and exception logging with stack traces
- Session summary generation
- Log export capabilities (JSON, CSV, TXT)
- Log search and filtering

**Log Files:**
- `logs/session_{session_id}.log` - Individual session logs
- `logs/V13_unified.log` - Consolidated system log
- `logs/api_access.log` - API request logs

### Visual Monitor

The Visual Monitor provides real-time dashboard and UI enhanced monitoring capabilities.

**Location:** `monitor/visual_monitor.py`

**Features:**
- Real-time system status dashboard
- Performance metrics visualization
- Doctrine activity monitoring
- Risk metrics tracking
- Alert and notification system
- Dashboard customization
- Export capabilities (PNG, PDF, HTML)

**Dashboard Components:**
- System status indicators
- Performance charts (P&L, win rate, drawdown)
- Doctrine performance displays
- Risk exposure gauges
- Trade execution tracking
- Alert notifications

## Logging System

### Log Levels

The system uses standard Python logging levels:

- **DEBUG**: Detailed diagnostic information
- **INFO**: General information about system operations
- **WARNING**: Warning messages for potential issues
- **ERROR**: Error messages for failures
- **CRITICAL**: Critical errors requiring immediate attention

### Log Format

All logs follow a consistent format:

```
timestamp - level - module - message
```

Example:
```
2025-01-15 10:30:00,123 - INFO - SessionLogger - Doctrine switched from fabio to marco (volatility > 1.5)
```

### Log Rotation

Logs are automatically rotated to prevent disk space issues:

- Daily rotation for session logs
- Size-based rotation (100MB) for unified logs
- 30-day retention period
- Compressed archives for old logs

## Dashboard Features

### Real-time Updates

The dashboard provides real-time updates with configurable refresh rates:

- **System Status**: Updates every 5 seconds
- **Performance Metrics**: Updates every 30 seconds
- **Risk Metrics**: Updates every 10 seconds
- **Doctrine Activity**: Updates on doctrine changes

### Visual Components

#### System Status Panel
- Current system state (running/stopped/error)
- Active doctrine display
- Uptime counter
- Last update timestamp
- Connection status indicators

#### Performance Dashboard
- Real-time P&L chart
- Win rate gauge
- Drawdown visualization
- Sharpe ratio indicator
- Trade count displays
- Average trade P&L

#### Doctrine Monitor
- Active doctrine indicator
- Doctrine performance history
- Switch history with timestamps
- Confidence level displays
- Performance comparison charts

#### Risk Management Panel
- Current exposure gauge
- Drawdown tracking
- Position limit indicators
- Risk threshold alerts
- Circuit breaker status

### Alert System

The monitoring system includes configurable alerts:

#### Alert Types
- **System Alerts**: System status changes, errors, warnings
- **Performance Alerts**: Drawdown thresholds, P&L targets
- **Risk Alerts**: Exposure limits, position size warnings
- **Doctrine Alerts**: Low confidence signals, performance drops

#### Alert Configuration

Alerts can be configured in `config/monitoring_config.json`:

```json
{
  "alerts": {
    "drawdown_threshold": -200.00,
    "exposure_limit": 0.80,
    "performance_target": 50.00,
    "error_rate_threshold": 0.05
  },
  "notifications": {
    "email": "alerts@trading-system.com",
    "webhook": "https://hooks.slack.com/...",
    "sms": "+1234567890"
  }
}
```

## Monitoring API Endpoints

### System Monitoring

#### GET /monitoring/status

Returns comprehensive system monitoring data.

**Response:**
```json
{
  "status": "success",
  "data": {
    "system_health": "healthy",
    "uptime_seconds": 86400,
    "memory_usage": 0.75,
    "cpu_usage": 0.45,
    "active_connections": 12,
    "last_backup": "2025-01-15T06:00:00Z",
    "error_count_24h": 3
  }
}
```

#### GET /monitoring/logs

Returns recent log entries with filtering options.

**Query Parameters:**
- `level` (optional): Filter by log level
- `module` (optional): Filter by module name
- `since` (optional): ISO 8601 timestamp for start time
- `limit` (optional): Maximum entries to return

**Response:**
```json
{
  "status": "success",
  "data": {
    "logs": [
      {
        "timestamp": "2025-01-15T10:30:00Z",
        "level": "INFO",
        "module": "SessionLogger",
        "message": "Doctrine switched to fabio"
      }
    ],
    "total_entries": 150,
    "filtered_entries": 25
  }
}
```

### Performance Monitoring

#### GET /monitoring/performance

Returns detailed performance monitoring data.

**Response:**
```json
{
  "status": "success",
  "data": {
    "response_times": {
      "avg_ms": 45,
      "95th_percentile_ms": 120,
      "99th_percentile_ms": 250
    },
    "throughput": {
      "requests_per_second": 15.5,
      "trades_per_minute": 2.3
    },
    "error_rates": {
      "total_errors": 5,
      "error_rate_percent": 0.02
    },
    "resource_usage": {
      "memory_mb": 512,
      "cpu_percent": 35,
      "disk_usage_gb": 25
    }
  }
}
```

### Alert Monitoring

#### GET /monitoring/alerts

Returns active alerts and alert history.

**Query Parameters:**
- `status` (optional): Filter by alert status (`active`, `resolved`)
- `type` (optional): Filter by alert type
- `since` (optional): ISO 8601 timestamp for start time

**Response:**
```json
{
  "status": "success",
  "data": {
    "active_alerts": [
      {
        "alert_id": "alert_123",
        "type": "risk",
        "severity": "warning",
        "message": "Drawdown approaching threshold",
        "triggered_at": "2025-01-15T10:25:00Z",
        "value": -180.50,
        "threshold": -200.00
      }
    ],
    "alert_history": [
      {
        "alert_id": "alert_122",
        "type": "performance",
        "severity": "info",
        "message": "Daily P&L target reached",
        "resolved_at": "2025-01-15T09:45:00Z"
      }
    ]
  }
}
```

## Log Analysis Tools

### Built-in Analysis

The system includes built-in log analysis tools:

#### Log Statistics
```bash
python -m monitor.log_analyzer --stats --period 24h
```

#### Error Pattern Detection
```bash
python -m monitor.log_analyzer --errors --pattern "connection" --since "2025-01-15"
```

#### Performance Trend Analysis
```bash
python -m monitor.log_analyzer --performance --metric response_time --period 7d
```

### External Tools

#### Logstash Integration

The system can integrate with Logstash for advanced log processing:

```logstash
input {
  file {
    path => "/path/to/v13/logs/*.log"
    start_position => "beginning"
  }
}

filter {
  grok {
    match => { "message" => "%{TIMESTAMP_ISO8601:timestamp} - %{LOGLEVEL:level} - %{WORD:module} - %{GREEDYDATA:message}" }
  }
}

output {
  elasticsearch {
    hosts => ["localhost:9200"]
    index => "v13-logs-%{+YYYY.MM.dd}"
  }
}
```

#### Kibana Dashboards

Pre-configured Kibana dashboards are available for:
- System performance monitoring
- Error tracking and analysis
- Trade execution visualization
- Risk metrics monitoring

## Troubleshooting

### Common Monitoring Issues

#### Dashboard Not Loading
1. Check if Visual Monitor service is running
2. Verify dashboard configuration in `config/dashboard_config.json`
3. Check browser console for JavaScript errors
4. Ensure WebSocket connection is established

#### Logs Not Appearing
1. Verify log file permissions
2. Check log rotation settings
3. Ensure logging level is appropriate
4. Confirm log directory exists and is writable

#### Alerts Not Triggering
1. Check alert configuration in `config/monitoring_config.json`
2. Verify threshold values are appropriate
3. Ensure notification channels are configured
4. Check system clock synchronization

#### Performance Degradation
1. Monitor resource usage (CPU, memory, disk)
2. Check log file sizes and rotation
3. Review database query performance
4. Analyze API response times

### Diagnostic Commands

#### System Health Check
```bash
python core/V13_SessionAudit.py --health-check
```

#### Log Integrity Check
```bash
python monitor/log_integrity_checker.py --verify
```

#### Performance Benchmark
```bash
python monitor/performance_benchmark.py --comprehensive
```

## Best Practices

### Monitoring Configuration

1. **Set Appropriate Thresholds**: Configure alerts based on your risk tolerance
2. **Regular Review**: Review monitoring configuration monthly
3. **Log Retention**: Balance log retention with storage constraints
4. **Alert Fatigue**: Avoid excessive alerting that leads to ignored warnings

### Operational Monitoring

1. **Daily Checks**: Review system status and key metrics daily
2. **Weekly Analysis**: Analyze performance trends and error patterns weekly
3. **Monthly Reports**: Generate comprehensive monthly monitoring reports
4. **Incident Response**: Document and improve incident response procedures

### Performance Optimization

1. **Log Level Management**: Use appropriate log levels in production
2. **Metric Sampling**: Sample high-frequency metrics to reduce storage
3. **Dashboard Optimization**: Limit dashboard refresh rates during high load
4. **Alert Prioritization**: Prioritize critical alerts over informational ones

## Support

For monitoring support and questions:
- Check the monitoring logs in `logs/monitoring.log`
- Review the system documentation in `docs/`
- Contact the development team with specific error messages and timestamps

---

*This monitoring guide is maintained alongside the system. Check for updates with each release.*
