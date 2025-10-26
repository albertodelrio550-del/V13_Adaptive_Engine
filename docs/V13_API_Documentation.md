# V13 API Documentation

## Overview

The V13 Adaptive Manual Trading Engine provides a comprehensive REST API for system monitoring, status checks, and external integrations. The API is built using Flask and provides real-time access to system state, performance metrics, and control functions.

## Base URL

```
http://localhost:5000
```

## Authentication

Currently, the API does not require authentication for development and testing purposes. In production environments, consider implementing API key authentication or OAuth.

## Response Format

All API responses are returned in JSON format with the following structure:

```json
{
  "status": "success|error",
  "data": {},
  "message": "Optional message",
  "timestamp": "ISO 8601 timestamp"
}
```

## Endpoints

### System Status

#### GET /status

Returns the current system status and operational state.

**Response:**
```json
{
  "status": "success",
  "data": {
    "system_state": "running|stopped|error",
    "active_doctrine": "fabio|marco|tanja|tg|kane|mayne|umar",
    "uptime_seconds": 3600,
    "last_update": "2025-01-15T10:30:00Z",
    "mode": "paper|live",
    "risk_level": "low|medium|high"
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Status Codes:**
- `200` - Success
- `500` - Internal server error

### Performance Metrics

#### GET /metrics

Returns current performance metrics and trading statistics.

**Query Parameters:**
- `period` (optional): Time period for metrics (`1h`, `1d`, `1w`, `1m`) - defaults to `1d`

**Response:**
```json
{
  "status": "success",
  "data": {
    "total_pnl": 1250.75,
    "daily_pnl": 45.30,
    "win_rate": 0.68,
    "total_trades": 150,
    "sharpe_ratio": 1.45,
    "max_drawdown": -125.50,
    "avg_trade_pnl": 8.34,
    "largest_win": 125.00,
    "largest_loss": -75.25,
    "current_drawdown": -15.20,
    "volatility": 0.023
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Status Codes:**
- `200` - Success
- `400` - Invalid period parameter
- `500` - Internal server error

### Doctrine Information

#### GET /doctrines

Returns information about active doctrines and their performance.

**Response:**
```json
{
  "status": "success",
  "data": {
    "active_doctrine": "fabio",
    "doctrine_performance": {
      "fabio": {
        "accuracy": 0.72,
        "total_trades": 45,
        "win_rate": 0.69,
        "avg_return": 12.50,
        "last_used": "2025-01-15T09:45:00Z"
      },
      "marco": {
        "accuracy": 0.65,
        "total_trades": 32,
        "win_rate": 0.63,
        "avg_return": 9.80,
        "last_used": "2025-01-14T14:20:00Z"
      }
    },
    "doctrine_history": [
      {
        "doctrine": "fabio",
        "activated_at": "2025-01-15T09:45:00Z",
        "reason": "volatility > 1.5"
      }
    ]
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Status Codes:**
- `200` - Success
- `500` - Internal server error

### Risk Management

#### GET /risk

Returns current risk management status and parameters.

**Response:**
```json
{
  "status": "success",
  "data": {
    "current_exposure": 2500.00,
    "max_exposure": 5000.00,
    "exposure_percentage": 0.50,
    "daily_drawdown": -45.25,
    "max_daily_drawdown": -100.00,
    "drawdown_percentage": 0.45,
    "risk_mode": "balanced",
    "position_limits": {
      "max_position_size": 1000.00,
      "max_positions": 5,
      "max_correlated_positions": 2
    },
    "circuit_breakers": {
      "volatility_threshold": 0.05,
      "drawdown_threshold": -200.00,
      "correlation_threshold": 0.85
    }
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Status Codes:**
- `200` - Success
- `500` - Internal server error

#### POST /risk

Updates risk management parameters.

**Request Body:**
```json
{
  "max_exposure": 7500.00,
  "max_daily_drawdown": -150.00,
  "risk_mode": "conservative",
  "position_limits": {
    "max_position_size": 1500.00,
    "max_positions": 3
  }
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "updated_parameters": ["max_exposure", "max_daily_drawdown", "risk_mode"],
    "validation_status": "passed",
    "effective_from": "2025-01-15T10:30:00Z"
  },
  "message": "Risk parameters updated successfully",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Status Codes:**
- `200` - Success
- `400` - Invalid parameters
- `500` - Internal server error

### Health Check

#### GET /health

Returns system health status for monitoring and load balancer checks.

**Response:**
```json
{
  "status": "success",
  "data": {
    "overall_health": "healthy",
    "components": {
      "api": "healthy",
      "database": "healthy",
      "market_data": "healthy",
      "trading_engine": "healthy"
    },
    "response_time_ms": 45,
    "uptime_seconds": 86400
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Status Codes:**
- `200` - System healthy
- `503` - System unhealthy

### Trading Operations

#### GET /positions

Returns current open positions.

**Response:**
```json
{
  "status": "success",
  "data": {
    "positions": [
      {
        "symbol": "AAPL",
        "side": "long",
        "quantity": 100,
        "entry_price": 185.50,
        "current_price": 187.25,
        "unrealized_pnl": 175.00,
        "stop_loss": 182.00,
        "take_profit": 195.00,
        "opened_at": "2025-01-15T09:30:00Z",
        "soldier": "assassin_01",
        "doctrine": "fabio"
      }
    ],
    "summary": {
      "total_positions": 1,
      "total_exposure": 18725.00,
      "total_unrealized_pnl": 175.00
    }
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

#### GET /orders

Returns recent order history.

**Query Parameters:**
- `limit` (optional): Maximum number of orders to return (default: 50)
- `status` (optional): Filter by order status (`filled`, `pending`, `cancelled`)

**Response:**
```json
{
  "status": "success",
  "data": {
    "orders": [
      {
        "order_id": "ord_12345",
        "symbol": "AAPL",
        "side": "buy",
        "quantity": 100,
        "order_type": "market",
        "status": "filled",
        "filled_price": 185.50,
        "filled_quantity": 100,
        "filled_at": "2025-01-15T09:30:00Z",
        "soldier": "assassin_01",
        "doctrine": "fabio"
      }
    ],
    "pagination": {
      "total_orders": 150,
      "returned_orders": 50,
      "has_more": true
    }
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

## Error Handling

### Error Response Format

```json
{
  "status": "error",
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {}
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### Common Error Codes

- `INVALID_REQUEST` - Malformed request or invalid parameters
- `SYSTEM_UNAVAILABLE` - System is temporarily unavailable
- `DATA_NOT_FOUND` - Requested data not found
- `PERMISSION_DENIED` - Insufficient permissions
- `RATE_LIMIT_EXCEEDED` - Too many requests
- `INTERNAL_ERROR` - Unexpected internal error

## Rate Limiting

- **General endpoints**: 100 requests per minute per IP
- **Health check**: 1000 requests per minute per IP
- **Rate limit headers** are included in all responses:
  - `X-RateLimit-Limit`: Maximum requests per minute
  - `X-RateLimit-Remaining`: Remaining requests in current window
  - `X-RateLimit-Reset`: Time when limit resets (Unix timestamp)

## WebSocket Support

For real-time updates, the API supports WebSocket connections:

**WebSocket URL:** `ws://localhost:5000/ws`

**Supported Topics:**
- `system_status` - Real-time system status updates
- `performance_metrics` - Live performance metric updates
- `doctrine_changes` - Doctrine activation notifications
- `trade_updates` - Real-time trade execution updates

**Example Subscription:**
```json
{
  "action": "subscribe",
  "topics": ["system_status", "performance_metrics"]
}
```

## SDK and Libraries

### Python Client

```python
from v13_api_client import V13Client

client = V13Client(base_url="http://localhost:5000")

# Get system status
status = client.get_status()
print(f"System state: {status['data']['system_state']}")

# Get performance metrics
metrics = client.get_metrics(period="1d")
print(f"Daily P&L: {metrics['data']['daily_pnl']}")

# Update risk parameters
client.update_risk({
    "max_exposure": 7500.00,
    "risk_mode": "conservative"
})
```

### JavaScript Client

```javascript
import { V13API } from 'v13-api-client';

const client = new V13API('http://localhost:5000');

// Get system status
const status = await client.getStatus();
console.log(`System state: ${status.data.system_state}`);

// Subscribe to real-time updates
client.subscribe(['system_status', 'performance_metrics'], (update) => {
  console.log('Real-time update:', update);
});
```

## Monitoring and Logging

All API requests are logged with the following information:
- Timestamp
- Client IP address
- Request method and endpoint
- Response status code
- Response time
- User agent (if provided)

Logs are available in `logs/api_access.log` and can be queried via the monitoring endpoints.

## Security Considerations

### Production Deployment

1. **Enable HTTPS** - Use SSL/TLS certificates
2. **Implement Authentication** - API keys or OAuth 2.0
3. **Rate Limiting** - Configure appropriate limits
4. **Input Validation** - Validate all request parameters
5. **CORS Configuration** - Configure Cross-Origin Resource Sharing
6. **Request Logging** - Enable comprehensive request logging

### Best Practices

- Use API versioning in URLs for future compatibility
- Implement proper error handling without exposing sensitive information
- Cache responses where appropriate to reduce load
- Monitor API usage and performance metrics
- Implement graceful degradation during system issues

## Support

For API support and questions:
- Check the logs in `logs/api_access.log` for request details
- Review the system logs in `logs/V13_unified.log` for errors
- Contact the development team with specific error messages and timestamps

---

*This API documentation is maintained alongside the system. Check for updates with each release.*
