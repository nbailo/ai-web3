from datatypes import PricingSnapshot
import requests
import time
from typing import Optional

PRICE_ENGINE_URL = "http://localhost:5000"

def fetch_pricing_snapshot(
    chain_id: int,
    token_in: str,
    token_out: str,
    side: str,
) -> Optional[PricingSnapshot]:
    """
    Fetch pricing snapshot from price-engine service.
    """
    #status: need to verify whether this makes sense 
    try:
        # Call price-engine service
        params = {
            'token_in': token_in,
            'token_out': token_out,
            'decimals_in': 18,  # Would need to fetch from token contract
            'decimals_out': 18
        }
        
        response = requests.get(f"{PRICE_ENGINE_URL}/price", params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        # Convert price-engine response to PricingSnapshot
        # The price-engine returns: mid_price, depth_curve, timestamp, confidence, source
        mid_price = data.get('mid_price', '0')
        depth_curve = data.get('depth_curve', [])

        return PricingSnapshot(
            midPrice=mid_price,
            depthPoints=depth_curve,
            confidenceScore=float(data.get('confidence', 0.95)),
            stale=False,  # Would check timestamp in production
            sourcesUsed=[data.get('source', 'unknown')],
            asOf=data.get('timestamp', time.time()),
            # sourceBreakdown=None,
            # latencyMs=None
        )

    except Exception as e:
        print(f"Error fetching pricing snapshot: {e}")
        return None