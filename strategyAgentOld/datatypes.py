from dataclasses import dataclass
from typing import Optional
from typing import List, Dict, Any
import time
from datetime import datetime

# ============================================================================
# Input Data 
# ============================================================================

@dataclass
class QuoteRequest:
    """Request for a quote from a taker."""
    chainId: int
    side: str  # "sell" | "buy"
    tokenIn: str
    tokenOut: str
    amount: str  # uint256 in base units (as string)
    taker: str
    recipient: Optional[str] = None
    idempotencyKey: Optional[str] = None

class DepthPoint:
    amount: float
    impliedPrice: float
    impactBps: float
    feeUsed: float

@dataclass
class PricingSnapshot:
    """Pricing data from the price-engine service."""
    midPrice: float
    depthCurve: List[DepthPoint]
    confidenceScore: float  # 0.0 to 1.0
    stale: bool
    sourcesUsed: List[str]
    asOf: float  # Unix timestamp
    #sourceBreakdown: Optional[Dict[str, Any]] = None
    #latencyMs: Optional[int] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PricingSnapshot':
        """Create PricingSnapshot from dictionary"""
        return cls(
            midPrice=str(data['midPrice']),
            depthPoints=data.get('depthPoints', []),
            confidenceScore=float(data.get('confidenceScore', 0.0)),
            stale=bool(data.get('stale', False)),
            sourcesUsed=data.get('sourcesUsed', []),
            asOf=float(data.get('asOf', time.time())),
            #sourceBreakdown=data.get('sourceBreakdown'),
            #latencyMs=data.get('latencyMs')
        )

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

#     @dataclass
    # class MakerConfig:
    #     allowed_pairs: List[str] = field(default_factory=list)
    #     max_trade_size: Optional[float] = None
    #     daily_caps: Dict[str, float] = field(default_factory=dict)
    #     ttl_ranges: Dict[str, Any] = field(default_factory=dict)  # Can be adjusted for real structure
    #     spread_presets: Dict[str, float] = field(default_factory=dict)
    #     paused: bool = False
    #     strategy: Optional[str] = None
    #     strategyBytes: Optional[str] = None  # Placeholder for bytes, e.g. base64 string
    #     strategyHash: Optional[str] = None

# ============================================================================
# Validation
# ============================================================================

@dataclass
class AllowedPair:
    """Allowed pair configuration"""
    tokenIn: str
    tokenOut: str

@dataclass
class DailyCap:
    """Daily cap configuration"""
    tokenIn: str
    tokenOut: str
    cap: str  # uint256 in base units


# ============================================================================
# Output Generation
# ============================================================================

@dataclass
class QuoteIntent:
    """Deterministic quote intent output."""
    maker: str
    tokenIn: str
    tokenOut: str
    amountIn: float
    amountOut: float
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


class DailyCapExceededError(Exception):
    """Raised when adding daily volume would exceed the configured cap/budget."""

    def __init__(self, maker: str, token_in: str, token_out: str, attempted_volume: float, cap: float):
        self.maker = maker
        self.token_in = token_in
        self.token_out = token_out
        self.attempted_volume = attempted_volume
        self.cap = cap
        pair_key = f"{token_in}-{token_out}"
        message = (
            f"{RejectionReason.DAILY_CAP_EXCEEDED}: maker={maker}, pair={pair_key}, "
            f"attempted_volume={attempted_volume}, cap={cap}"
        )
        super().__init__(message)

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
        self.daily_volumes: Dict[str, Dict[str, Dict[str, Any]]] = {}
    
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
        #not sure what is in a budget or budget_snapshot...
        if maker not in self.budget_snapshots:
            self.budget_snapshots[maker] = {}
        if strategy_hash not in self.budget_snapshots[maker]:
            self.budget_snapshots[maker][strategy_hash] = {}
        self.budget_snapshots[maker][strategy_hash][token] = balance
    
    def get_daily_volume(self, maker: str, token_in: str, token_out: str) -> float:
        """Get today's volume for a maker's pair"""
        pair_key = f"{token_in.lower()}-{token_out.lower()}"
        today = datetime.now().strftime("%Y-%m-%d")
        
        if maker not in self.daily_volumes:
            self.daily_volumes[maker] = {}
        if pair_key not in self.daily_volumes[maker]:
            self.daily_volumes[maker][pair_key] = {"date": today, "volume": 0}
        
        # Reset if it's a new day
        if self.daily_volumes[maker][pair_key]["date"] != today:
            self.daily_volumes[maker][pair_key] = {"date": today, "volume": 0}
        
        volume = self.daily_volumes[maker][pair_key]["volume"]
        # Handle case where volume might be stored as string (legacy)
        if isinstance(volume, str):
            return float(volume)
        return volume
    
    def add_daily_volume(
        self,
        maker: str,
        token_in: str,
        token_out: str,
        amount: float,
        cap: Optional[float] = None,
    ):
        """
        Add to today's volume for a maker's pair.

        If `cap` is provided, this will raise DailyCapExceededError when the new
        cumulative volume would exceed that cap. Volumes and caps are treated as
        integer base units encoded as decimal strings.
        """
        pair_key = f"{token_in.lower()}-{token_out.lower()}"
        today = datetime.now().strftime("%Y-%m-%d")
        
        if maker not in self.daily_volumes:
            self.daily_volumes[maker] = {}
        if pair_key not in self.daily_volumes[maker]:
            self.daily_volumes[maker][pair_key] = {"date": today, "volume": 0}
        
        # Reset if it's a new day
        if self.daily_volumes[maker][pair_key]["date"] != today:
            self.daily_volumes[maker][pair_key] = {"date": today, "volume": 0}

        current_volume = self.daily_volumes[maker][pair_key]["volume"]
        new_volume = current_volume + amount

        if cap is not None:
            if new_volume > cap:
                # Do not mutate state; signal to caller that cap would be exceeded
                raise DailyCapExceededError(
                    maker=maker,
                    token_in=token_in,
                    token_out=token_out,
                    attempted_volume=new_volume,
                    cap=cap
                )

        self.daily_volumes[maker][pair_key]["volume"] = new_volume


# Global state instance
state = StrategyAgentState()