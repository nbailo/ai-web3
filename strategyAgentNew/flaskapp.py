from typing import Dict, Any
from flask import Flask, jsonify, request
from flasgger import Swagger
import time
from datatypes import (
    StrategyIntentRequest,
    StrategyInfo,
    PricingSnapshotDto,
    DepthPointDto,
    Provenance
)
from enforcer import process_quote_request

app = Flask(__name__)

# Swagger configuration
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/apispec.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/swagger"
}

swagger_template = {
    "swagger": "2.0",
    "info": {
        "title": "Strategy Agent API",
        "description": "API for strategy intent requests and quote processing",
        "version": "1.0.0"
    },
    "host": "localhost:5001",
    "basePath": "/",
    "schemes": ["http"]
}

swagger = Swagger(app, config=swagger_config, template=swagger_template)


def ingest_strategy_intent_request(data: Dict[str, Any]) -> StrategyIntentRequest:
    """
    Ingest and validate a StrategyIntentRequest from JSON data.
    
    Args:
        data: Dictionary containing the request data from JSON body
        
    Returns:
        StrategyIntentRequest: Validated and constructed request object
        
    Raises:
        KeyError: If required fields are missing
        ValueError: If field types are invalid
        Exception: For other validation/construction errors
    """
    try:
        # Validate top-level required fields
        if not data:
            raise ValueError("Request body is empty")
        
        # Extract and validate pricingSnapshot (nested PricingSnapshotDto)
        if 'pricingSnapshot' not in data:
            raise KeyError("Missing required field: pricingSnapshot")
        
        pricing_data = data['pricingSnapshot']
        
        # Build DepthPointDto list
        depth_points = []
        if 'depthPoints' in pricing_data:
            for dp_data in pricing_data['depthPoints']:
                # Build Provenance list for each depth point
                provenance_list = []
                if 'provenance' in dp_data:
                    for prov_data in dp_data['provenance']:
                        provenance = Provenance(
                            venue=prov_data['venue'],
                            feeTier=prov_data.get('feeTier')
                        )
                        provenance_list.append(provenance)
                
                depth_point = DepthPointDto(
                    amountInRaw=int(dp_data['amountInRaw']),
                    amountOutRaw=int(dp_data['amountOutRaw']),
                    price=int(dp_data['amountInRaw'])/int(dp_data['amountOutRaw']),
                    impactBps=dp_data['impactBps'],
                    provenance=provenance_list
                )
                depth_points.append(depth_point)
        
        # Build PricingSnapshotDto
        pricing_snapshot = PricingSnapshotDto(
            asOfMs=pricing_data['asOfMs'],
            midPrice=pricing_data['midPrice'],
            depthPoints=depth_points,
            sourcesUsed=pricing_data['sourcesUsed'],
            confidenceScore=pricing_data['confidenceScore'],
            stale=pricing_data['stale'],
            reasonCodes=pricing_data['reasonCodes']
        )
        
        # Extract and validate strategy (nested StrategyInfo)
        if 'strategy' not in data:
            raise KeyError("Missing required field: strategy")
        
        strategy_data = data['strategy']
        strategy = StrategyInfo(
            id=strategy_data['id'],
            version=int(strategy_data['version']),
            params=strategy_data.get('params', {})
        )
        
        # Build StrategyIntentRequest
        intent_request = StrategyIntentRequest(
            chainId=int(data['chainId']),
            maker=str(data['maker']),
            executor=str(data['executor']),
            taker=str(data['taker']),
            sellToken=str(data['sellToken']),
            buyToken=str(data['buyToken']),
            sellAmount=int(data['sellAmount']),
            recipient=str(data['recipient']),
            pricingSnapshot=pricing_snapshot,
            strategy=strategy
        )
        
        return intent_request
        
    except KeyError as e:
        raise KeyError(f"Missing required field: {str(e)}")
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid field value or type: {str(e)}")
    except Exception as e:
        raise Exception(f"Error ingesting StrategyIntentRequest: {str(e)}")

@app.route('/intent', methods=['POST'])
def get_response():
    """
    Strategy Intent Request Endpoint
    Process a strategy intent request and return a quote response.
    ---
    tags:
      - Strategy Intent
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: body
        name: body
        description: Strategy Intent Request
        required: true
        schema:
          type: object
          required:
            - chainId
            - maker
            - executor
            - taker
            - sellToken
            - buyToken
            - sellAmount
            - recipient
            - pricingSnapshot
            - strategy
          properties:
            chainId:
              type: integer
              example: 8453
            maker:
              type: string
              example: "0x1234567890123456789012345678901234567890"
            executor:
              type: string
              example: "0x1234567890123456789012345678901234567890"
            taker:
              type: string
              example: "0x1234567890123456789012345678901234567890"
            sellToken:
              type: string
              example: "0x1234567890123456789012345678901234567890"
            buyToken:
              type: string
              example: "0x1234567890123456789012345678901234567890"
            sellAmount:
              type: integer
              example: 1000000000000000000
            recipient:
              type: string
              example: "0x1234567890123456789012345678901234567890"
            pricingSnapshot:
              type: object
              required:
                - asOfMs
                - midPrice
                - depthPoints
                - sourcesUsed
                - latencyMs
                - confidenceScore
                - stale
                - reasonCodes
              properties:
                asOfMs:
                  type: integer
                  example: 1704067200000
                blockNumber:
                  type: integer
                  example: 12345678
                midPrice:
                  type: string
                  example: "3000.5"
                depthPoints:
                  type: array
                  items:
                    type: object
                    required:
                      - amountInRaw
                      - amountOutRaw
                      - price
                      - impactBps
                      - provenance
                    properties:
                      amountInRaw:
                        type: integer
                        example: 1000000000000000000
                      amountOutRaw:
                        type: integer
                        example: 3000000000000000000
                      price:
                        type: string
                        example: "3000.0"
                      impactBps:
                        type: integer
                        example: 0
                      provenance:
                        type: array
                        items:
                          type: object
                          properties:
                            venue:
                              type: string
                              example: "uniswap_v3"
                            feeTier:
                              type: integer
                              example: 3000
                sourcesUsed:
                  type: string
                  example: "uniswap_v3_base"
                latencyMs:
                  type: integer
                  example: 50
                confidenceScore:
                  type: integer
                  example: 95
                stale:
                  type: boolean
                  example: false
                reasonCodes:
                  type: string
                  example: ""
            strategy:
              type: object
              required:
                - id
                - version
                - params
              properties:
                id:
                  type: string
                  example: "strategy-001"
                version:
                  type: integer
                  example: 1
                params:
                  type: object
                  example:
                    feeBps: 10
                    maxImpactBps: 50
                    maxTradeRaw: 10000000000000000000
                    ttlSec: 300
                    rejectIfStale: true
    responses:
      200:
        description: Successful response
        schema:
          type: object
          properties:
            strategy:
              type: object
              properties:
                id:
                  type: string
                  example: "strategy-001"
                version:
                  type: integer
                  example: 1
                hash:
                  type: string
                  example: "0xabc123..."
            buyAmount:
              type: string
              example: "3000000000000000000"
            feeBps:
              type: integer
              example: 10
            feeAmount:
              type: string
              example: "3000000000000000"
            expiry:
              type: integer
              example: 1704067500000
            tx:
              type: object
              properties:
                to:
                  type: string
                  example: "0x1234..."
                data:
                  type: string
                  example: "0x..."
                value:
                  type: string
                  example: "0"
            pricing:
              type: object
              properties:
                asOfMs:
                  type: integer
                  example: 1704067200000
                confidenceScore:
                  type: number
                  example: 95.0
                stale:
                  type: boolean
                  example: false
                sourcesUsed:
                  type: array
                  items:
                    type: string
                  example: ["uniswap_v3_base"]
      400:
        description: Bad request - missing or invalid fields
        schema:
          type: object
          properties:
            error:
              type: string
      500:
        description: Internal server error
        schema:
          type: object
          properties:
            error:
              type: string
    """
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'Missing request body'}), 400
        
        # Ingest StrategyIntentRequest
        intent_request = ingest_strategy_intent_request(data)
        intent_response = process_quote_request(intent_request)
        # TODO: Process the intent_request and return response
        # This will need to be implemented based on your processing logic
        return jsonify(intent_response.to_dict()), 200
    except KeyError as e:
        return jsonify({'error': f'Missing required field: {str(e)}'}), 400
    except ValueError as e:
        return jsonify({'error': f'Invalid field value: {str(e)}'}), 400
    except Exception as e:
        print(f"Error processing quote request: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """
    Health Check Endpoint
    Returns the health status of the service.
    ---
    tags:
      - Health
    responses:
      200:
        description: Service is healthy
        schema:
          type: object
          properties:
            status:
              type: string
              example: "ok"
            timestamp:
              type: number
              example: 1704067200.123
            service:
              type: string
              example: "strategy-agent"
    """
    return jsonify({
        'status': 'ok',
        'timestamp': time.time(),
        'service': 'strategy-agent'
    })


if __name__ == '__main__':
    print("Starting Strategy Agent service on http://localhost:5001")
    print("Endpoints:")
    print("  POST /intent - Get a quote")
    print("  GET /health - Health check")
    print("  GET /swagger - Swagger UI documentation")
    print("  GET /apispec.json - OpenAPI specification")
    app.run(debug=True, port=5001)
