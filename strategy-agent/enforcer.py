from typing import Optional, Tuple, List
import time
from datatypes import (
    QuoteRequest,
    ChainSnapshot,
    QuoteIntent,
    PricingSnapshot,
    RejectionReason,
    DailyCapExceededError,
    state
)
from makeragent.SmartChatBot import MakerConfig
from gen_intent import synthesize_quote_intent

# ============================================================================
# Core Logic Functions
# ============================================================================

def check_policy_enforcement(
    quote_request: QuoteRequest,
    maker_config: MakerConfig
) -> List[RejectionReason]:
    """
    Policy enforcement: honor maker settings.
    Returns rejection reason if policy violated, None otherwise.
    """
    rejections = []
    # Check if maker is paused
    if maker_config.paused:
        rejections.append(RejectionReason.MAKER_PAUSED)
    
    # Check if pair is allowed
    # clarify logic of allowed pairs 
    pair_allowed = any(
        pair.get('tokenIn', '').lower() == quote_request.tokenIn.lower() and
        pair.get('tokenOut', '').lower() == quote_request.tokenOut.lower()
        for pair in maker_config.allowed_pairs
    )
    if not pair_allowed and len(maker_config.allowed_pairs) > 0:
        rejections.append(RejectionReason.PAIR_NOT_ALLOWED)
    
    # Check max trade size
    amount_float = float(quote_request.amount)
    max_trade_float = float(maker_config.max_trade_size) if maker_config.max_trade_size else 0.0
    if max_trade_float > 0 and amount_float > max_trade_float:
        rejections.append(RejectionReason.MAX_TRADE_SIZE_EXCEEDED)
    
    # Check daily caps if configured
    if maker_config.daily_caps:
        for cap in maker_config.daily_caps:
            if (
                cap.get('tokenIn', '') == quote_request.tokenIn
                and cap.get('tokenOut', '') == quote_request.tokenOut
            ):
                cap_amount_str = cap.get('cap', '0')
                cap_amount_float = float(cap_amount_str)
                if cap_amount_float <= 0:
                    # Non-positive caps are treated as disabled
                    break

                try:
                    # This will raise DailyCapExceededError if the new volume would exceed the cap.
                    state.add_daily_volume(
                        maker=maker_config.maker,
                        token_in=quote_request.tokenIn,
                        token_out=quote_request.tokenOut,
                        amount=amount_float,
                        cap=cap_amount_float,
                    )
                except DailyCapExceededError:
                    rejections.append(RejectionReason.DAILY_CAP_EXCEEDED)

                # If we found and processed a matching cap, we can stop checking further caps
                break
    if quote_request.idempotencyKey in state.quote_cache:
        rejections.append(RejectionReason.REPEATED_IDEMPOTENCY_KEY)
    return rejections


# For state actions
# state initialisation below

    # def __init__(self):
    #     # maker => current nonce
    #     self.maker_nonces: Dict[str, int] = {}
        
    #     # idempotencyKey => QuoteIntent (for replay protection)
    #     self.quote_cache: Dict[str, QuoteIntent] = {}
        
    #     # maker => strategyHash => token => budget snapshot
    #     self.budget_snapshots: Dict[str, Dict[str, Dict[str, str]]] = {}
        
    #     # maker => daily volume tracking (for daily caps)
    #     # Format: maker => strategy => 
    #     # {"date": "YYYY-MM-DD", "volume": "amount", "pair": "tokenIn-tokenOut" }
    #     self.daily_volumes: Dict[str, Dict[str, Any]] = {}

def check_on_chain_feasibility(
    quote_request: QuoteRequest,
    maker_config: MakerConfig,
    chain_snapshot: ChainSnapshot,
    amount_out: float,
) -> List[RejectionReason]:
    """
    On-chain feasibility gate: ensure strategy is active, has budget, and allowances.
    Returns rejection reason if not feasible, None otherwise.
    """
    rejections = []
    # Check strategy status
    if chain_snapshot.strategyStatus != "ACTIVE":
        rejections.append(RejectionReason.STRATEGY_INACTIVE)
    
    # Check tokenOut budget
    required_budget = amount_out
    available_budget = float(state.budget_snapshots[maker_config.strategyHash][quote_request.tokenOut])
    for record in state.daily_volumes[maker_config.strategyHash]:
        available_budget = available_budget - record["amount"]
    if available_budget < required_budget:
        rejections.append(RejectionReason.INSUFFICIENT_BUDGET)
    
    # Check allowances (maker → Aqua for tokenOut)
    token_out_allowance = None
    for allowance in chain_snapshot.allowances:
        if allowance.get('token', '') == quote_request.tokenOut:
            token_out_allowance = float(allowance.get('allowance', '0'))
            break
    
    if token_out_allowance is None or token_out_allowance < required_budget:
        rejections.append(RejectionReason.INSUFFICIENT_ALLOWANCE)

    return rejections


def process_quote_request(
    quote_request: QuoteRequest,
    maker_config: MakerConfig,
    pricing_snapshot: PricingSnapshot,
    chain_snapshot: ChainSnapshot
) -> Tuple[Optional[QuoteIntent], List[RejectionReason]]:
    """
    Main processing function: validates inputs and produces quote intent or rejection.
    Returns: (intent, rejection_reason(s))
    """
    intent = synthesize_quote_intent(quote_request, maker_config, pricing_snapshot, chain_snapshot) 
    rejections = []


    # Check pricing staleness
    if pricing_snapshot.stale:
        rejections.append(RejectionReason.STALE_PRICING)
    
    # Policy enforcement
    policy_reason = check_policy_enforcement(quote_request, maker_config)
    rejections.extend(policy_reason)
    
    # Synthesize quote intent
    intent = synthesize_quote_intent(
        quote_request, maker_config, pricing_snapshot, chain_snapshot
    )
    
    # On-chain feasibility check
    feasibility_reason = check_on_chain_feasibility(
        quote_request, chain_snapshot, intent.amountOut
    )
    rejections.extend(feasibility_reason)

    if rejections == []:
        #state update
        #1. nonce
        state.get_next_nonce(maker_config.strategyHash)
        #2. idempotency key
        state.cache_quote(quote_request.idempotencyKey, intent)
        #3. volumes
        state.add_daily_volume(quote_request.tokenIn, quote_request.tokenOut, intent.amountOut, maker_config.strategyHash)

    return (intent, rejections)