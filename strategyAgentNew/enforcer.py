from typing import Tuple, List
import time
import json
from decimal import Decimal, InvalidOperation
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

def calculate_impact_and_buy_amount(
    sell_amount: int,
    depth_points: List[DepthPointDto],
    mid_price: str
) -> Tuple[float, int]:
    """
    Linear interpolation over cumulative depth curve to estimate executable buy amount
    and resulting price impact vs mid price.
    """
    if sell_amount <= 0 or not depth_points:
        return 0.0, 0

    # Ensure depth points are sorted by cumulative input
    sorted_points = sorted(depth_points, key=lambda dp: dp.amountInRaw)

    prev_point = DepthPointDto(
        amountInRaw=0,
        amountOutRaw=0,
        price=mid_price,
        impactBps=0,
        provenance=[],
    )

    for point in sorted_points:
        if sell_amount <= point.amountInRaw:
            denominator = point.amountInRaw - prev_point.amountInRaw
            if denominator == 0:
                buy_amount = point.amountOutRaw
            else:
                ratio = (sell_amount - prev_point.amountInRaw) / denominator
                buy_amount = int(
                    prev_point.amountOutRaw
                    + (point.amountOutRaw - prev_point.amountOutRaw) * ratio
                )
            break
        prev_point = point
    else:
        # Requested size exceeds curve, use the last cumulative point
        buy_amount = sorted_points[-1].amountOutRaw

    try:
        mid = Decimal(mid_price)
        exec_price = Decimal(buy_amount) / Decimal(sell_amount)
        if mid == 0:
            impact_bps = 0
        else:
            impact_bps = float(((exec_price - mid) / mid) * Decimal('10000'))
    except (InvalidOperation, ZeroDivisionError):
        impact_bps = 0.0

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


    impact_bps, buy_amount = calculate_impact_and_buy_amount(
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
    strategy_hash = sir.strategy.hash if hasattr(sir.strategy, "hash") and sir.strategy.hash else compute_strategy_hash(sir.strategy)

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

    ttl_ms = int(sir.strategy.params["ttlSec"]) * 1000

    strategy_intent_response = StrategyIntentResponse(
        decision=decision,
        strategy=strategy_info_response,
        buyAmount=buy_amount*(1-sir.strategy.params["spreadBps"]/10000),
        feeBps=sir.strategy.params["feeBps"],
        feeAmount=int(sir.strategy.params["feeBps"] * sir.sellAmount/ 10000),
        expiry=sir.pricingSnapshot.asOfMs + ttl_ms,
        pricing=sir.pricingSnapshot
    )
    return strategy_intent_response