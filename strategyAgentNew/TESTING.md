# Testing the Strategy Agent API with Swagger

This guide explains how to test the `/intent` endpoint using Swagger UI.

## Prerequisites

1. Install dependencies:
```bash
pip install -r requirements.txt
```

This will install:
- Flask (web framework)
- web3 (for blockchain interactions)
- flasgger (for Swagger UI)

## Starting the Server

1. Start the Flask server:
```bash
python flaskapp.py
```

You should see output like:
```
Starting Strategy Agent service on http://localhost:5001
Endpoints:
  POST /intent - Get a quote
  GET /health - Health check
  GET /swagger - Swagger UI documentation
  GET /apispec.json - OpenAPI specification
```

## Testing with Swagger UI

### Option 1: Using Swagger UI (Recommended)

1. Open your browser and navigate to:
   ```
   http://localhost:5001/swagger
   ```

2. You'll see the Swagger UI interface with all available endpoints:
   - `/intent` (POST) - Strategy Intent Request
   - `/health` (GET) - Health Check

3. To test the `/intent` endpoint:
   - Click on the `/intent` endpoint to expand it
   - Click the "Try it out" button
   - Fill in the request body with JSON data (see example below)
   - Click "Execute"
   - View the response below

### Option 2: Using the Test Script

1. Make sure the server is running (see above)

2. Run the test script:
```bash
python test_intent.py
```

This will run several test cases:
- Health check test
- Valid intent request test
- Missing field test
- Stale pricing rejection test

## Example Request Body

Here's a complete example request body for the `/intent` endpoint:

```json
{
  "chainId": 8453,
  "maker": "0x1234567890123456789012345678901234567890",
  "executor": "0x1234567890123456789012345678901234567890",
  "taker": "0x9876543210987654321098765432109876543210",
  "sellToken": "0x1111111111111111111111111111111111111111",
  "buyToken": "0x2222222222222222222222222222222222222222",
  "sellAmount": 1000000000000000000,
  "recipient": "0x9876543210987654321098765432109876543210",
  "pricingSnapshot": {
    "asOfMs": 1704067200000,
    "blockNumber": 12345678,
    "midPrice": "3000.5",
    "depthPoints": [
      {
        "amountInRaw": 1000000000000000000,
        "amountOutRaw": 3000000000000000000,
        "price": "3000.0",
        "impactBps": 0,
        "provenance": [
          {
            "venue": "uniswap_v3",
            "feeTier": 3000
          }
        ]
      }
    ],
    "sourcesUsed": "uniswap_v3_base",
    "latencyMs": 50,
    "confidenceScore": 95,
    "stale": false,
    "reasonCodes": ""
  },
  "strategy": {
    "id": "strategy-001",
    "version": 1,
    "params": {
      "feeBps": 10,
      "maxImpactBps": 50,
      "maxTradeRaw": 10000000000000000000,
      "ttlSec": 300,
      "rejectIfStale": false
    }
  }
}
```

## Testing Different Scenarios

### 1. Successful Request
Use the example above with valid data. Should return a 200 response with strategy intent details.

### 2. Missing Required Field
Remove a required field (e.g., `chainId`). Should return a 400 error.

### 3. Stale Pricing Rejection
Set `rejectIfStale: true` in strategy params and use an old `asOfMs` timestamp (older than `ttlSec`). Should return a rejection.

### 4. Max Impact BPS Exceeded
Use depth points with high `impactBps` values that exceed `maxImpactBps` in strategy params. Should return a rejection.

### 5. Max Trade Size Exceeded
Use a `sellAmount` larger than `maxTradeRaw` in strategy params. Should return a rejection.

## API Endpoints

- **POST /intent** - Process a strategy intent request
- **GET /health** - Health check endpoint
- **GET /swagger** - Swagger UI documentation
- **GET /apispec.json** - OpenAPI specification (JSON)

## Troubleshooting

1. **Connection refused**: Make sure the Flask server is running on port 5001
2. **Import errors**: Run `pip install -r requirements.txt` to install dependencies
3. **Port already in use**: Change the port in `flaskapp.py` or stop the process using port 5001

