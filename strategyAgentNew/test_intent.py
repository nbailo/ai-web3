"""
Test script for the /intent endpoint.
Run this after starting the Flask server.
"""
import requests
import json
import time

BASE_URL = "http://localhost:5001"

def test_health():
    """Test the health endpoint"""
    print("Testing /health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

def test_intent_success():
    """Test the /intent endpoint with a valid request"""
    print("Testing /intent endpoint with valid request...")
    
    # Sample request data
    request_data = {
        "chainId": 8453,
        "maker": "0xMAKER000000000000000000000000000000000001",
        "executor": "0x0B9Ec798B4Ea766d8c5C2b995aD37FedB858200a",
        "taker": "0xTAKER000000000000000000000000000000000001",
        "recipient": "0xRECIP000000000000000000000000000000000001",
        "sellToken": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "buyToken": "0x4200000000000000000000000000000000000006",
        "sellAmount": "2000000000",
        "pricingSnapshot": {
            "asOfMs": 1765071909000,
            "stale": False,
            "confidenceScore": 0.93,
            "sourcesUsed": ["uniswap_v3_base","1inch_quote"],
            "midPrice": "0.00052",
            "depthPoints": [
            {
            "amountInRaw": "2000000000",
            "amountOutRaw": "1045000000000000000",
            "impactBps": 18,
            "feeTier": 3000,
            "gasEstimate": "160000"
            },
            {
            "amountInRaw": "5000000000",
            "amountOutRaw": "2600000000000000000",
            "impactBps": 42,
            "feeTier": 3000,
            "gasEstimate": "170000"
            }
            ],
            "reasonCodes": []
        },

        "strategy": {
            "id": "3c2f4c0e-1b7d-4c5d-9b3d-2e3a2a6f6c10",
            "version": 1,
            "params": {
                "ttlSec": 15,
                "feeBps": 10,
                "spreadBps": 20,
                "maxTradeRaw": "2000000000",
                "maxImpactBps": 80,
                "minConfidenceScore": 0.85,
                "rejectIfStale": True
            }
        }
    }

    response = requests.post(
        f"{BASE_URL}/intent",
        json=request_data,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

if __name__ == "__main__":
    print("=" * 60)
    print("Strategy Agent API Test Suite")
    print("=" * 60)
    print()
    
    try:
        test_health()
        test_intent_success()
        
        
        print("=" * 60)
        print("All tests completed!")
        print("=" * 60)
        print()
        print("To test with Swagger UI:")
        print("1. Start the Flask server: python flaskapp.py")
        print("2. Open your browser to: http://localhost:5001/swagger")
        print("3. Use the Swagger UI to test the /intent endpoint interactively")
        
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to the server.")
        print("Please make sure the Flask server is running on http://localhost:5001")
        print("Start it with: python flaskapp.py")

