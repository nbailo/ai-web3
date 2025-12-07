from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from flask import Flask, jsonify, request
from web3 import Web3
import time
from decimal import Decimal
from datatypes import QuoteRequest, AllowedPair, PricingSnapshot, ChainSnapshot
from confighelper import fetch_maker_config_from_db, fetch_chain_snapshot
from enforcer import process_quote_request
from fetchdata import fetch_pricing_snapshot
from makeragent.SmartChatBot import MakerConfig

app = Flask(__name__)

@app.route('/quote', methods=['POST'])
def get_quote():
    """
    Main quote endpoint.
    Expects JSON with: quoteRequest, makerConfig (optional - will fetch if not provided),
    pricingSnapshot (optional - will fetch if not provided), chainSnapshot (optional - will fetch if not provided)
    """

    # 1. data intake
    # 1.1 ingest the QuoteRequest 
    # status: waiting for quoteRequest API to implement
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'Missing request body'}), 400
        if 'quoteRequest' not in data:
            return jsonify({'error': 'Missing quoteRequest'}), 400
        
        quote_req = QuoteRequest(**data['quoteRequest'])
        
        # 1.2 ingest the makerConfig
        # status: waiting for database implementation
        if 'makerConfig' in data:
            maker_cfg = MakerConfig.from_dict(data['makerConfig'])
        else:
            # Fetch from DB (would need maker address - using taker as fallback)
            maker_cfg = fetch_maker_config_from_db(quote_req.taker)
            if not maker_cfg:
                return jsonify({'error': 'Could not fetch maker config'}), 500
        
        #1.3 ingest the PricingSnapshot
        if 'pricingSnapshot' in data:
            pricing = PricingSnapshot.from_dict(data['pricingSnapshot'])
        else:
            pricing = fetch_pricing_snapshot(
                quote_req.chainId,
                quote_req.tokenIn,
                quote_req.tokenOut,
                quote_req.side
            )
            if not pricing:
                return jsonify({'error': 'Could not fetch pricing snapshot'}), 500
        
        # 1.4 ingest the ChainSnapshot
        # status: Chain API TBD 
        if 'chainSnapshot' in data:
            chain = ChainSnapshot.from_dict(data['chainSnapshot'])
        else:
            # Need strategy hash - use first from maker config or fetch
            strategy_hash = "0x0"
            if maker_cfg.strategyHashes:
                strategy_hash = maker_cfg.strategyHashes[0]
            
            chain = fetch_chain_snapshot(
                quote_req.chainId,
                maker_cfg.maker,
                strategy_hash,
                quote_req.tokenOut
            )
            if not chain:
                return jsonify({'error': 'Could not fetch chain snapshot'}), 500
        
        # 2. processing the quote once all data is in
        intent, rejections  = process_quote_request(
            quote_req, maker_cfg, pricing, chain
        )
        
        if rejections != []:
            response = {
                'quoteIntent': intent.to_dict(),
                'rejected': False
            }
            return jsonify(response), 200
        else:
            response = {
                'quoteIntent': None,
                'rejected': True,
                'rejectionReason': rejections
            }
            return jsonify(response), 200
    
    except KeyError as e:
        return jsonify({'error': f'Missing required field: {str(e)}'}), 400
    except Exception as e:
        print(f"Error processing quote request: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'timestamp': time.time(),
        'service': 'strategy-agent'
    })


if __name__ == '__main__':
    print("Starting Strategy Agent service on http://localhost:5001")
    print("Endpoints:")
    print("  POST /quote - Get a quote")
    print("  GET /health - Health check")
    app.run(debug=True, port=5001)
