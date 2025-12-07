from typing import Tuple, List
import time
import json
from web3 import Web3
from datatypes import (
    DepthPointDto,
    RejectionReason,
    StrategyInfo,
    StrategyInfoResponse,
    StrategyIntentRequest,
    StrategyIntentResponse
)

# ============================================================================
# Core Logic Functions
# ============================================================================

def compute_strategy_hash(strategy: StrategyInfo) -> str:
    """
    Compute strategy hash exactly as it would be computed on-chain.
    Uses keccak256 of strategy bytes, matching AquaQuoteExecutor.computeStrategyHash.
    
    Args:
        strategy: StrategyInfo with id, version, and params
        
    Returns:
        Hex string of the strategy hash (0x-prefixed, 66 chars)
    """
    # Serialize strategy params deterministically (sorted keys, no whitespace)
    # This matches how strategy bytes would be encoded on-chain
    strategy_bytes = json.dumps(
        {
            "id": strategy.id,
            "version": strategy.version,
            "params": strategy.params
        },
        sort_keys=True,
        separators=(',', ':'),
        ensure_ascii=False
    ).encode('utf-8')
    
    # Compute keccak256 hash (same as Solidity keccak256)
    hash_bytes = Web3.keccak(strategy_bytes)
    return Web3.to_hex(hash_bytes)

def calculate_impact_and_fee_bps(
    sell_amount: int,
    depth_points: List[DepthPointDto],
    mid_price: str
) -> Tuple[float, float]:
    """
    Calculate impact_bps and fee_bps by buying as much as possible at cheap prices.
    
    Strategy: Walk through depth curve from best to worst prices, filling
    as much as possible at each price level before moving to the next.
    Depth points are cumulative - each point represents total available up to that amount.
    
    Args:
        sell_amount: Amount to sell (in base units)
        depth_points: List of depth points (ordered by amount, best prices first)
        mid_price: Mid price as string
        
    Returns:
        Tuple of (impact_bps, buy_amount) where:
        - impact_bps: Price impact in basis points (how much worse than mid price)
    """
    below_ideal_point = DepthPointDto(
    amountInRaw=0,
    amountOutRaw=0,
    price=mid_price,
    impactBps=0,
    provenance=[]
    )
    ideal_point = DepthPointDto(
    amountInRaw=0,
    amountOutRaw=0,
    price=mid_price,
    impactBps=0,
    provenance=[]
    )
    #point at start of curve with 0 trade volume
    for point in depth_points:
        below_ideal_point = ideal_point
        ideal_point = point
        if below_ideal_point.amountInRaw >= sell_amount:
            break
    
    impact_bps = below_ideal_point.impactBps + (ideal_point.impactBps - below_ideal_point.impactBps) * (sell_amount - below_ideal_point.amountInRaw) / (ideal_point.amountInRaw - below_ideal_point.amountInRaw)      
    buy_amount = below_ideal_point.amountOutRaw + (ideal_point.impactBps - below_ideal_point.impactBps) * (sell_amount - below_ideal_point.amountInRaw) / (ideal_point.amountInRaw - below_ideal_point.amountInRaw)     
    
    return impact_bps, buy_amount

# @dataclass
# class StrategyIntentRequest:
#     """Request for a strategy intent"""
#     chainId: int
#     maker: str
#     executor: str
#     taker: str
#     sellToken: str
#     buyToken: str
#     sellAmount: str
#     recipient: str
#     pricingSnapshot: PricingSnapshotDto
#     strategy: StrategyInfo

def check_policy_enforcement(
    sir: StrategyIntentRequest
) -> Tuple[List[RejectionReason], int]:
    """
    Policy enforcement: honor maker settings.
    Returns rejection reason if policy violated, None otherwise.
    """
    rejections = []
    
    
#     @dataclass
# class PricingSnapshotDto:
#   asOfMs: int
#   blockNumber: Optional[int] = None
#   midPrice: str
#   depthPoints: List[DepthPointDto]
#   sourcesUsed: str
#   latencyMs: int
#   confidenceScore: int
#   stale: bool
#   reasonCodes: str
    nowMs = int(time.time() * 1000)
    if nowMs - sir.pricingSnapshot.asOfMs > sir.strategy.params["ttlSec"]*1000:
        sir.pricingSnapshot.stale = True
    print(sir.pricingSnapshot.stale)
    print(sir.strategy.params["rejectIfStale"])
    if (sir.pricingSnapshot.stale and sir.strategy.params["rejectIfStale"] == True):
        rejections.append(RejectionReason.STALE_PRICING)
    # @dataclass
    # class DepthPointDto:
    #   amountInRaw: str
    #   amountOutRaw: str
    #   price: str
    #   impactBps: int
    #   provenance: List[Provenance]
    # finding ideal point on the depth curve          
    
    
    impact_bps, buy_amount = calculate_impact_and_fee_bps(
        sell_amount=sir.sellAmount,
        depth_points=sir.pricingSnapshot.depthPoints,
        mid_price=sir.pricingSnapshot.midPrice
    )

    if impact_bps > int(sir.strategy.params["maxImpactBps"]):
        rejections.append(RejectionReason.MAX_IMPACT_BPS_EXCEEDED)
    # Check max trade size
    amount_float = int(sir.sellAmount)
    max_trade_float = int(sir.strategy.params["maxTradeRaw"]) 
    if max_trade_float > 0 and amount_float > max_trade_float:
        rejections.append(RejectionReason.MAX_TRADE_SIZE_EXCEEDED)
    #enforcement of the transactions (ttlsec, spreadBps, maxImpactBps, feeBps)
    return rejections, buy_amount

def process_quote_request(
    sir: StrategyIntentRequest
) -> Tuple[StrategyIntentResponse, List[RejectionReason]]:
    """
    Main processing function: validates inputs and produces quote intent or rejection.
    Returns: (intent, rejection_reason(s))
    """
    # Compute strategy hash (matches on-chain computation)
    strategy_hash = compute_strategy_hash(sir.strategy)
    
    # Build strategy info response with hash
    strategy_info_response = StrategyInfoResponse(
        id=sir.strategy.id,
        version=sir.strategy.version,
        hash=strategy_hash
    )
    rejections, buy_amount = check_policy_enforcement(sir)
    print(rejections)
    if rejections == []:
        decision = "ACCEPT"
        reasoncodes = ["OK"]
    else:
        decision = "REJECT"
        reasoncodes = rejections
    sir.pricingSnapshot.reasonCodes = reasoncodes
    print(sir.pricingSnapshot.reasonCodes)

    strategy_intent_response = StrategyIntentResponse(
        decision=decision,
        strategy=strategy_info_response,
        buyAmount=buy_amount*(1-sir.strategy.params["spreadBps"]/10000),
        feeBps=sir.strategy.params["feeBps"],
        feeAmount=int(sir.strategy.params["feeBps"] * sir.sellAmount/ 10000),
        expiry=sir.pricingSnapshot.asOfMs + sir.strategy.params["ttlSec"],
        pricing=sir.pricingSnapshot
    )
    return strategy_intent_response