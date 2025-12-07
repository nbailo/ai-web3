from datatypes import QuoteRequest, PricingSnapshot, ChainSnapshot, QuoteIntent, state
from makeragent.SmartChatBot import MakerConfig
import time

def synthesize_quote_intent(
    quote_request: QuoteRequest,
    maker_config: MakerConfig,
    pricing_snapshot: PricingSnapshot,
    chain_snapshot: ChainSnapshot
) -> QuoteIntent:
    """
    Quote Intent synthesis: choose side-aware amountIn/amountOut, spread, ttlSec,
    minOutNet, select strategyHash, and allocate a fresh nonce.
    """
    # Check for cached quote (idempotency)
    if quote_request.idempotencyKey:
        cached = state.get_cached_quote(quote_request.idempotencyKey)
        if cached:
            return cached
    
    # Select strategy hash
    strategy_hash = maker_config.strategyHash
    if not strategy_hash or strategy_hash == "0x0" or strategy_hash == "":
        if chain_snapshot.strategyHash:
            strategy_hash = chain_snapshot.strategyHash
        else:
            strategy_hash = "0x0"  # Fallback
    
# @dataclass
# class QuoteRequest:
#     """Request for a quote from a taker."""
#     chainId: int
#     side: str  # "sell" | "buy"
#     tokenIn: str
#     tokenOut: str
#     amount: str  # uint256 in base units (as string)
#     taker: str
#     recipient: Optional[str] = None
#     idempotencyKey: Optional[str] = None

    # Calculate amounts based on side
    # calculate based on depth curve 
    if (quote_request.side == "sell"): 
        amountOut = 0
        amountIn = quote_request.tokenIn * pricing_snapshot.midPrice
        for snap in pricing_snapshot.depthPoints:
            spread_bps = snap.impactBps
            if (snap.amount > amountIn):
                break
    if (quote_request.side == "buy"): 
        amountIn = 0
        amountOut = quote_request.tokenIn * pricing_snapshot.midPrice
        for snap in pricing_snapshot.depthPoints:
            spread_bps = snap.impactBps
            if (snap.amount > amountOut):
                break
    # else: throw exception 
    
    # Select TTL (use middle of range or default)
    ttl_sec = 300  # Default 5 minutes
    # tbd: waiting on ttl-sec from makeragent
    
    expiry = int(time.time()) + ttl_sec
    
    # Calculate minOutNet (amountOut minus some buffer for slippage)
    # Use 99% of amountOut as minOutNet (slippage tolerance in %)
    slippage_tolerance = 1
    min_out_net = int(amountOut * (100 - slippage_tolerance) / 100)
    
    # Get next nonce
    nonce = state.get_next_nonce(maker_config.maker)
    
    # Create quote intent
    intent = QuoteIntent(
        maker=maker_config.maker,
        tokenIn=quote_request.tokenIn,
        tokenOut=quote_request.tokenOut,
        amountIn=amountIn,
        amountOut=amountOut,
        strategyHash=strategy_hash,
        nonce=nonce,
        expiry=expiry,
        minOutNet=str(min_out_net),
        idempotencyKey=quote_request.idempotencyKey
    )
    
    # Cache the quote if idempotency key provided
    if quote_request.idempotencyKey:
        state.cache_quote(quote_request.idempotencyKey, intent)
    
    return intent
