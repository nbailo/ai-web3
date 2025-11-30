from web3 import Web3
from flask import Flask, jsonify, request
import time

app = Flask(__name__)

# Connect to Base RPC
w3 = Web3(Web3.HTTPProvider('https://mainnet.base.org'))

QUOTER_ADDRESS = "0x3d4e44Eb1374240CE5F1B871ab261CD16335B76a"

QUOTER_ABI = [{
    "inputs": [
        {"components": [
            {"internalType": "address", "name": "tokenIn", "type": "address"},
            {"internalType": "address", "name": "tokenOut", "type": "address"},
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "uint24", "name": "fee", "type": "uint24"},
            {"internalType": "uint160", "name": "sqrtPriceLimitX96", "type": "uint160"}
        ], "internalType": "struct IQuoterV2.QuoteExactInputSingleParams", "name": "params", "type": "tuple"}
    ],
    "name": "quoteExactInputSingle",
    "outputs": [
        {"internalType": "uint256", "name": "amountOut", "type": "uint256"},
        {"internalType": "uint160", "name": "sqrtPriceX96After", "type": "uint160"},
        {"internalType": "uint32", "name": "initializedTicksCrossed", "type": "uint32"},
        {"internalType": "uint256", "name": "gasEstimate", "type": "uint256"}
    ],
    "stateMutability": "nonpayable",
    "type": "function"
}]


def get_price(token_in, token_out, amount):
    """Get a single price quote"""
    try:
        quoter = w3.eth.contract(address=QUOTER_ADDRESS, abi=QUOTER_ABI)

        result = quoter.functions.quoteExactInputSingle({
            'tokenIn': token_in,
            'tokenOut': token_out,
            'amountIn': amount,
            'fee': 3000,
            'sqrtPriceLimitX96': 0
        }).call()

        return result[0]
    except Exception as e:
        print(f"Error getting price: {e}")
        return None


def build_depth_curve(token_in, token_out, token_in_decimals, token_out_decimals):
    """Build depth curve by sampling different trade sizes"""

    test_amounts = [100, 500, 1000, 5000, 10000]

    depth_curve = []
    mid_price = None

    for amount_human in test_amounts:
        amount_raw = int(amount_human * (10 ** token_in_decimals))

        amount_out = get_price(token_in, token_out, amount_raw)

        if amount_out:
            price = amount_out / amount_raw

            if mid_price is None:
                mid_price = price

            impact_bps = ((price - mid_price) / mid_price) * 10000 if mid_price else 0

            depth_curve.append({
                'amount_in': amount_human,
                'amount_out': amount_out / (10 ** token_out_decimals),
                'price': price,
                'impact_bps': impact_bps
            })

    return {
        'mid_price': mid_price,
        'depth_curve': depth_curve,
        'timestamp': time.time(),
        'confidence': 0.95,
        'source': 'uniswap_v3_base'
    }


@app.route('/price', methods=['GET'])
def get_price_data():
    """
    API endpoint for price data
    Query params: token_in, token_out, decimals_in, decimals_out
    """
    token_in = request.args.get('token_in')
    token_out = request.args.get('token_out')
    decimals_in = int(request.args.get('decimals_in', 18))
    decimals_out = int(request.args.get('decimals_out', 18))

    if not token_in or not token_out:
        return jsonify({'error': 'Missing token addresses'}), 400

    try:
        result = build_depth_curve(token_in, token_out, decimals_in, decimals_out)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'timestamp': time.time()})


if __name__ == '__main__':
    # Test on startup
    USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
    WETH = "0x4200000000000000000000000000000000000006"

    print("Testing price engine...")
    result = build_depth_curve(USDC, WETH, 6, 18)
    print(f"Mid Price: {result['mid_price']}")
    print(f"Depth points: {len(result['depth_curve'])}")
    print("\nStarting API server on http://localhost:5000")

    app.run(debug=True, port=5000)