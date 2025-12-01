from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from flask import Flask, jsonify, request
from web3 import Web3
import time
import hashlib
import json
import requests
from decimal import Decimal
from datatypes import QuoteRequest, AllowedPair, PricingSnapshot, ChainSnapshot


# ============================================================================
# Configuration
# ============================================================================

# Price engine service URL
PRICE_ENGINE_URL = "http://localhost:5000"

# Web3 connection (will be initialized per chain)
web3_connections: Dict[int, Web3] = {}

# Aqua contract addresses (per chain)
AQUA_ADDRESSES: Dict[int, str] = {
    8453: "0x0000000000000000000000000000000000000000",  # Base mainnet (placeholder)
}

# Aqua ABI (simplified - would need full ABI in production)
AQUA_ABI = [
    {
        "inputs": [
            {"name": "maker", "type": "address"},
            {"name": "app", "type": "address"},
            {"name": "strategyHash", "type": "bytes32"},
            {"name": "token", "type": "address"}
        ],
        "name": "rawBalances",
        "outputs": [
            {"name": "balance", "type": "uint248"},
            {"name": "tokensCount", "type": "uint8"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

# ERC20 ABI (for allowance checks)
ERC20_ABI = [
    {
        "inputs": [
            {"name": "owner", "type": "address"},
            {"name": "spender", "type": "address"}
        ],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# ============================================================================
# Data Structures
# ============================================================================


@dataclass
class TTLRange:
    """TTL range configuration"""
    minSec: int
    maxSec: int


@dataclass
class SpreadPreset:
    """Spread preset configuration"""
    name: str
    spreadBps: int  # 0-10000


@dataclass
class MakerConfig:
    """Maker configuration stored in the database."""
    maker: str
    allowedPairs: List[Dict[str, str]]
    maxTradeSize: str  # uint256 in base units
    dailyCaps: Optional[List[Dict[str, str]]] = None
    ttlRanges: Dict[str, int] = field(default_factory=lambda: {"minSec": 0, "maxSec": 0})
    spreadPresets: List[Dict[str, Any]] = field(default_factory=list)
    paused: bool = False
    strategyHashes: List[str] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MakerConfig':
        """Create MakerConfig from dictionary"""
        return cls(
            maker=data['maker'],
            allowedPairs=data.get('allowedPairs', []),
            maxTradeSize=data.get('maxTradeSize', '0'),
            dailyCaps=data.get('dailyCaps'),
            ttlRanges=data.get('ttlRanges', {'minSec': 0, 'maxSec': 0}),
            spreadPresets=data.get('spreadPresets', []),
            paused=data.get('paused', False),
            strategyHashes=data.get('strategyHashes', [])
        )


@dataclass
class DepthPoint:
    """Depth point on the liquidity curve"""
    amount: str
    expectedOutOrIn: str
    impliedPrice: str
    impactBps: int


@dataclass
class RawBalances:
    """Raw balance information from Aqua strategy"""
    balance: str  # uint248 in base units
    tokensCount: int  # uint8: 0 = inactive, 0xff (255) = DOCKED, else = ACTIVE


@dataclass
class AllowanceInfo:
    """Token allowance information"""
    token: str
    allowance: str  # uint256 in base units
    spender: str


@dataclass
class ChainSnapshot:
    """On-chain state snapshot for feasibility checks."""
    chainId: int
    maker: str
    strategyHash: str
    rawBalances: Dict[str, Any]
    allowances: List[Dict[str, str]]
    strategyStatus: str  # "ACTIVE" | "DOCKED" | "INACTIVE"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChainSnapshot':
        """Create ChainSnapshot from dictionary"""
        return cls(
            chainId=data['chainId'],
            maker=data['maker'],
            strategyHash=data['strategyHash'],
            rawBalances=data['rawBalances'],
            allowances=data.get('allowances', []),
            strategyStatus=data.get('strategyStatus', 'INACTIVE')
        )


@dataclass
class QuoteIntent:
    """Deterministic quote intent output."""
    maker: str
    tokenIn: str
    tokenOut: str
    amountIn: str
    amountOut: str
    strategyHash: str
    nonce: int
    expiry: int  # Unix timestamp
    minOutNet: str
    reason: Optional[str] = None  # Rejection reason if declined
    idempotencyKey: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response"""
        return {
            'maker': self.maker,
            'tokenIn': self.tokenIn,
            'tokenOut': self.tokenOut,
            'amountIn': self.amountIn,
            'amountOut': self.amountOut,
            'strategyHash': self.strategyHash,
            'nonce': self.nonce,
            'expiry': self.expiry,
            'minOutNet': self.minOutNet,
            'idempotencyKey': self.idempotencyKey
        }


@dataclass
class ExplainabilityPayload:
    """Optional explainability data for Maker Agent consumers."""
    description: str
    rationale: Optional[str] = None
    spreadApplied: Optional[str] = None
    ttlSec: Optional[int] = None
    strategySelectionReason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response"""
        return {
            'description': self.description,
            'rationale': self.rationale,
            'spreadApplied': self.spreadApplied,
            'ttlSec': self.ttlSec,
            'strategySelectionReason': self.strategySelectionReason,
            'metadata': self.metadata
        }


# ============================================================================
# Rejection Reasons (canonical)
# ============================================================================

class RejectionReason:
    MAKER_PAUSED = "MAKER_PAUSED"
    INSUFFICIENT_BUDGET = "INSUFFICIENT_BUDGET"
    STALE_PRICING = "STALE_PRICING"
    PAIR_NOT_ALLOWED = "PAIR_NOT_ALLOWED"
    STRATEGY_INACTIVE = "STRATEGY_INACTIVE"
    INSUFFICIENT_ALLOWANCE = "INSUFFICIENT_ALLOWANCE"
    MAX_TRADE_SIZE_EXCEEDED = "MAX_TRADE_SIZE_EXCEEDED"
    DAILY_CAP_EXCEEDED = "DAILY_CAP_EXCEEDED"


# ============================================================================
# State Management
# ============================================================================

class StrategyAgentState:
    """Manages per-maker state: nonces, quote cache, fills/reverts tracking"""
    
    def __init__(self):
        # maker => current nonce
        self.maker_nonces: Dict[str, int] = {}
        
        # idempotencyKey => QuoteIntent (for replay protection)
        self.quote_cache: Dict[str, QuoteIntent] = {}
        
        # maker => strategyHash => token => budget snapshot
        self.budget_snapshots: Dict[str, Dict[str, Dict[str, str]]] = {}
        
        # maker => daily volume tracking (for daily caps)
        # Format: maker => "tokenIn-tokenOut" => {"date": "YYYY-MM-DD", "volume": "amount"}
        self.daily_volumes: Dict[str, Dict[str, Dict[str, str]]] = {}
    
    def get_next_nonce(self, maker: str) -> int:
        """Get and increment the next nonce for a maker"""
        if maker not in self.maker_nonces:
            self.maker_nonces[maker] = 0
        self.maker_nonces[maker] += 1
        return self.maker_nonces[maker]
    
    def get_cached_quote(self, idempotency_key: str) -> Optional[QuoteIntent]:
        """Get cached quote by idempotency key"""
        if not idempotency_key:
            return None
        cached = self.quote_cache.get(idempotency_key)
        if cached and cached.expiry > int(time.time()):
            return cached
        # Remove expired cache entry
        if cached:
            del self.quote_cache[idempotency_key]
        return None
    
    def cache_quote(self, idempotency_key: str, intent: QuoteIntent):
        """Cache a quote by idempotency key"""
        if idempotency_key:
            self.quote_cache[idempotency_key] = intent
    
    def update_budget_snapshot(self, maker: str, strategy_hash: str, token: str, balance: str):
        """Update budget snapshot for quick checks"""
        if maker not in self.budget_snapshots:
            self.budget_snapshots[maker] = {}
        if strategy_hash not in self.budget_snapshots[maker]:
            self.budget_snapshots[maker][strategy_hash] = {}
        self.budget_snapshots[maker][strategy_hash][token] = balance
    
    def get_daily_volume(self, maker: str, token_in: str, token_out: str) -> str:
        """Get today's volume for a maker's pair"""
        pair_key = f"{token_in.lower()}-{token_out.lower()}"
        today = datetime.now().strftime("%Y-%m-%d")
        
        if maker not in self.daily_volumes:
            self.daily_volumes[maker] = {}
        if pair_key not in self.daily_volumes[maker]:
            self.daily_volumes[maker][pair_key] = {"date": today, "volume": "0"}
        
        # Reset if it's a new day
        if self.daily_volumes[maker][pair_key]["date"] != today:
            self.daily_volumes[maker][pair_key] = {"date": today, "volume": "0"}
        
        return self.daily_volumes[maker][pair_key]["volume"]
    
    def add_daily_volume(self, maker: str, token_in: str, token_out: str, amount: str):
        """Add to today's volume for a maker's pair"""
        pair_key = f"{token_in.lower()}-{token_out.lower()}"
        today = datetime.now().strftime("%Y-%m-%d")
        
        if maker not in self.daily_volumes:
            self.daily_volumes[maker] = {}
        if pair_key not in self.daily_volumes[maker]:
            self.daily_volumes[maker][pair_key] = {"date": today, "volume": "0"}
        
        # Reset if it's a new day
        if self.daily_volumes[maker][pair_key]["date"] != today:
            self.daily_volumes[maker][pair_key] = {"date": today, "volume": "0"}
        
        current_volume = int(self.daily_volumes[maker][pair_key]["volume"])
        new_volume = current_volume + int(amount)
        self.daily_volumes[maker][pair_key]["volume"] = str(new_volume)


# Global state instance
state = StrategyAgentState()


# ============================================================================
# Helper Functions (for fetching data from external sources)
# ============================================================================

def get_web3_connection(chain_id: int) -> Optional[Web3]:
    """Get or create Web3 connection for a chain"""
    if chain_id in web3_connections:
        return web3_connections[chain_id]
    
    # RPC URLs per chain (would be in config in production)
    rpc_urls = {
        8453: "https://mainnet.base.org",  # Base mainnet
        1: "https://eth.llamarpc.com",  # Ethereum mainnet
    }
    
    if chain_id not in rpc_urls:
        return None
    
    try:
        w3 = Web3(Web3.HTTPProvider(rpc_urls[chain_id]))
        web3_connections[chain_id] = w3
        return w3
    except Exception as e:
        print(f"Error connecting to chain {chain_id}: {e}")
        return None


def fetch_maker_config_from_db(maker: str) -> Optional[MakerConfig]:
    """
    Fetch maker config from database.
    In production, this would query a real database.
    For now, returns a mock config.
    """
    # TODO: Implement actual database query
    # This is a placeholder that returns a default config
    return MakerConfig(
        maker=maker,
        allowedPairs=[],
        maxTradeSize="1000000000000000000000",  # 1000 tokens (assuming 18 decimals)
        dailyCaps=None,
        ttlRanges={"minSec": 60, "maxSec": 3600},
        spreadPresets=[{"name": "default", "spreadBps": 50}],
        paused=False,
        strategyHashes=[]
    )



def fetch_chain_snapshot(
    chain_id: int,
    maker: str,
    strategy_hash: str,
    token_out: str
) -> Optional[ChainSnapshot]:
    """
    Fetch chain snapshot via web3 calls.
    Fetches rawBalances from Aqua contract and allowances from ERC20 contracts.
    """
    w3 = get_web3_connection(chain_id)
    if not w3:
        return None
    
    aqua_address = AQUA_ADDRESSES.get(chain_id)
    if not aqua_address:
        return None
    
    try:
        # Fetch rawBalances from Aqua contract
        aqua_contract = w3.eth.contract(address=aqua_address, abi=AQUA_ABI)
        
        # Call rawBalances
        # Note: In production, you'd need the executor address (app parameter)
        # For now, using a placeholder
        executor_address = "0x0000000000000000000000000000000000000000"
        
        try:
            result = aqua_contract.functions.rawBalances(
                maker,
                executor_address,
                bytes.fromhex(strategy_hash[2:]) if strategy_hash.startswith('0x') else bytes.fromhex(strategy_hash),
                token_out
            ).call()
            
            balance = str(result[0])
            tokens_count = result[1]
            
            # Determine strategy status
            if tokens_count == 0:
                strategy_status = "INACTIVE"
            elif tokens_count == 0xff:  # 255
                strategy_status = "DOCKED"
            else:
                strategy_status = "ACTIVE"
            
            raw_balances = {
                'balance': balance,
                'tokensCount': tokens_count
            }
        except Exception as e:
            print(f"Error fetching rawBalances: {e}")
            # Return inactive status if call fails
            raw_balances = {'balance': '0', 'tokensCount': 0}
            strategy_status = "INACTIVE"
        
        # Fetch allowance (maker → Aqua for tokenOut)
        token_contract = w3.eth.contract(address=token_out, abi=ERC20_ABI)
        try:
            allowance = token_contract.functions.allowance(maker, aqua_address).call()
            allowances = [{
                'token': token_out,
                'allowance': str(allowance),
                'spender': aqua_address
            }]
        except Exception as e:
            print(f"Error fetching allowance: {e}")
            allowances = []
        
        return ChainSnapshot(
            chainId=chain_id,
            maker=maker,
            strategyHash=strategy_hash,
            rawBalances=raw_balances,
            allowances=allowances,
            strategyStatus=strategy_status
        )
    except Exception as e:
        print(f"Error fetching chain snapshot: {e}")
        return None


# ============================================================================
# Core Logic Functions
# ============================================================================

def check_policy_enforcement(
    quote_request: QuoteRequest,
    maker_config: MakerConfig
) -> Optional[str]:
    """
    Policy enforcement: honor maker settings.
    Returns rejection reason if policy violated, None otherwise.
    """
    # Check if maker is paused
    if maker_config.paused:
        return RejectionReason.MAKER_PAUSED
    
    # Check if pair is allowed
    pair_allowed = any(
        pair.get('tokenIn', '').lower() == quote_request.tokenIn.lower() and
        pair.get('tokenOut', '').lower() == quote_request.tokenOut.lower()
        for pair in maker_config.allowedPairs
    )
    if not pair_allowed and len(maker_config.allowedPairs) > 0:
        return RejectionReason.PAIR_NOT_ALLOWED
    
    # Check max trade size
    amount_int = int(quote_request.amount)
    max_trade_int = int(maker_config.maxTradeSize)
    if max_trade_int > 0 and amount_int > max_trade_int:
        return RejectionReason.MAX_TRADE_SIZE_EXCEEDED
    
    # Check daily caps if configured
    if maker_config.dailyCaps:
        pair_key = f"{quote_request.tokenIn.lower()}-{quote_request.tokenOut.lower()}"
        for cap in maker_config.dailyCaps:
            if (cap.get('tokenIn', '').lower() == quote_request.tokenIn.lower() and
                cap.get('tokenOut', '').lower() == quote_request.tokenOut.lower()):
                cap_amount = int(cap.get('cap', '0'))
                current_volume = int(state.get_daily_volume(
                    maker_config.maker,
                    quote_request.tokenIn,
                    quote_request.tokenOut
                ))
                if current_volume + amount_int > cap_amount:
                    return RejectionReason.DAILY_CAP_EXCEEDED
    
    return None


def check_on_chain_feasibility(
    quote_request: QuoteRequest,
    chain_snapshot: ChainSnapshot,
    amount_out: str
) -> Optional[str]:
    """
    On-chain feasibility gate: ensure strategy is active, has budget, and allowances.
    Returns rejection reason if not feasible, None otherwise.
    """
    # Check strategy status
    if chain_snapshot.strategyStatus != "ACTIVE":
        return RejectionReason.STRATEGY_INACTIVE
    
    # Check tokenOut budget
    required_budget = int(amount_out)
    available_budget = int(chain_snapshot.rawBalances.get('balance', '0'))
    if available_budget < required_budget:
        return RejectionReason.INSUFFICIENT_BUDGET
    
    # Check allowances (maker → Aqua for tokenOut)
    token_out_allowance = None
    for allowance in chain_snapshot.allowances:
        if allowance.get('token', '').lower() == quote_request.tokenOut.lower():
            token_out_allowance = int(allowance.get('allowance', '0'))
            break
    
    if token_out_allowance is None or token_out_allowance < required_budget:
        return RejectionReason.INSUFFICIENT_ALLOWANCE
    
    return None


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
    strategy_hash = chain_snapshot.strategyHash
    if not strategy_hash or strategy_hash == "0x0" or strategy_hash == "":
        if maker_config.strategyHashes:
            strategy_hash = maker_config.strategyHashes[0]
        else:
            strategy_hash = "0x0"  # Fallback
    
    # Calculate amounts based on side
    amount_in = int(quote_request.amount)
    try:
        mid_price = float(pricing_snapshot.midPrice)
    except (ValueError, TypeError):
        mid_price = 1.0  # Fallback price
    
    # Apply spread (use first spread preset or default)
    spread_bps = 50  # Default 0.5% spread
    if maker_config.spreadPresets:
        first_preset = maker_config.spreadPresets[0]
        if isinstance(first_preset, dict):
            spread_bps = int(first_preset.get('spreadBps', 50))
        else:
            spread_bps = 50
    
    if quote_request.side == "sell":
        # Selling tokenIn for tokenOut
        # Apply spread: reduce output by spread
        amount_out = int(amount_in * mid_price * (10000 - spread_bps) / 10000)
    else:
        # Buying tokenOut with tokenIn
        # Apply spread: increase input required by spread
        amount_out = int(amount_in / mid_price)
        amount_in = int(amount_out * mid_price * (10000 + spread_bps) / 10000)
    
    # Select TTL (use middle of range or default)
    ttl_sec = 300  # Default 5 minutes
    if maker_config.ttlRanges:
        min_sec = maker_config.ttlRanges.get('minSec', 0)
        max_sec = maker_config.ttlRanges.get('maxSec', 0)
        if max_sec > min_sec:
            ttl_sec = (min_sec + max_sec) // 2
        elif min_sec > 0:
            ttl_sec = min_sec
    
    expiry = int(time.time()) + ttl_sec
    
    # Calculate minOutNet (amountOut minus some buffer for slippage)
    # Use 99% of amountOut as minOutNet (1% slippage tolerance)
    min_out_net = int(amount_out * 99 / 100)
    
    # Get next nonce
    nonce = state.get_next_nonce(maker_config.maker)
    
    # Create quote intent
    intent = QuoteIntent(
        maker=maker_config.maker,
        tokenIn=quote_request.tokenIn,
        tokenOut=quote_request.tokenOut,
        amountIn=str(amount_in),
        amountOut=str(amount_out),
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


def process_quote_request(
    quote_request: QuoteRequest,
    maker_config: MakerConfig,
    pricing_snapshot: PricingSnapshot,
    chain_snapshot: ChainSnapshot
) -> Tuple[Optional[QuoteIntent], Optional[str], Optional[ExplainabilityPayload]]:
    """
    Main processing function: validates inputs and produces quote intent or rejection.
    Returns: (intent, rejection_reason, explainability)
    """
    # Check pricing staleness
    if pricing_snapshot.stale:
        return None, RejectionReason.STALE_PRICING, None
    
    # Policy enforcement
    policy_reason = check_policy_enforcement(quote_request, maker_config)
    if policy_reason:
        return None, policy_reason, None
    
    # Synthesize quote intent
    intent = synthesize_quote_intent(
        quote_request, maker_config, pricing_snapshot, chain_snapshot
    )
    
    # On-chain feasibility check
    feasibility_reason = check_on_chain_feasibility(
        quote_request, chain_snapshot, intent.amountOut
    )
    if feasibility_reason:
        intent.reason = feasibility_reason
        return None, feasibility_reason, None
    
    # Create explainability payload
    spread_bps = 50
    if maker_config.spreadPresets:
        first_preset = maker_config.spreadPresets[0]
        if isinstance(first_preset, dict):
            spread_bps = int(first_preset.get('spreadBps', 50))
    
    explainability = ExplainabilityPayload(
        description=f"Quote for {quote_request.side} {quote_request.amount} {quote_request.tokenIn}",
        rationale=f"Applied {spread_bps} bps spread, output: {intent.amountOut} {quote_request.tokenOut}",
        spreadApplied=f"{spread_bps} bps",
        ttlSec=intent.expiry - int(time.time()),
        strategySelectionReason=f"Selected strategy {intent.strategyHash}",
        metadata={
            'midPrice': pricing_snapshot.midPrice,
            'confidenceScore': pricing_snapshot.confidenceScore
        }
    )
    
    return intent, None, explainability


