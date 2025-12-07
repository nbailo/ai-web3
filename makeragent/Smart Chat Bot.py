import os

# Configure OpenAI-compatible API for Membase LTM summarization
# Membase uses OpenAI internally for LLM calls - we redirect to ASI1 (OpenAI-compatible)
_ASI1_API_KEY = os.getenv("LLM_API_KEY", "sk_d95b81ac6db6406a82c9ba3baf078fa207b863c9a0d3422292c05033a3a2f397")
_ASI1_BASE_URL = os.getenv("LLM_API_ENDPOINT", "https://api.asi1.ai/v1")
_ASI1_MODEL = os.getenv("LLM_MODEL", "asi1-mini")  # Use asi1-mini for Membase LTM

# Set OpenAI env vars to use ASI1 instead (OpenAI-compatible endpoint)
os.environ["OPENAI_API_KEY"] = _ASI1_API_KEY
os.environ["OPENAI_BASE_URL"] = _ASI1_BASE_URL
os.environ["OPENAI_MODEL"] = _ASI1_MODEL  # Override default model
os.environ["_CHROMA_SKIP_OPENAI_WARNING"] = "1"

import json
import requests
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
import datetime
import re
import subprocess
import tempfile
import hashlib
import numpy as np

# Helper for timezone-aware UTC timestamps (Python 3.12+ compatible)
def _utc_now() -> datetime.datetime:
    """Return current UTC time (timezone-aware)."""
    try:
        return datetime.datetime.now(datetime.UTC)
    except AttributeError:
        # Python < 3.11 fallback
        return datetime.datetime.utcnow()

def _utc_timestamp() -> str:
    """Return current UTC time as ISO string."""
    return _utc_now().isoformat()

def _utc_date_str() -> str:
    """Return current UTC date as ISO string."""
    return _utc_now().date().isoformat()

def _utc_unix() -> int:
    """Return current UTC time as Unix timestamp."""
    return int(_utc_now().timestamp())

# Try to import Hyperon (MeTTa) for Windows/Python-native support
try:
    from hyperon import MeTTa as HyperonMeTTa
    _HYPERON_AVAILABLE = True
    print("[INIT] Hyperon (MeTTa) library loaded successfully")
except ImportError:
    _HYPERON_AVAILABLE = False
    print("[INIT] Hyperon library not found. Will try to use 'metta' CLI if available.")

# ---- CONFIG ----
LLM_API_ENDPOINT = os.getenv("LLM_API_ENDPOINT", "https://api.asi1.ai/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "sk_d95b81ac6db6406a82c9ba3baf078fa207b863c9a0d3422292c05033a3a2f397")
LLM_MODEL = os.getenv("LLM_MODEL", "asi1-extended")

METTA_ENABLED = os.getenv("METTA_ENABLED", "true").lower() == "true"
METTA_STORAGE_DIR = os.getenv("METTA_STORAGE_DIR", "./metta_kb")
METTA_EXEC_PATH = os.getenv("METTA_EXEC_PATH", "metta")

# Optional remote MeTTa / knowledge-graph backend (e.g. SingularityNET)
USE_REMOTE_METTA = os.getenv("USE_REMOTE_METTA", "false").lower() == "true"
REMOTE_METTA_ENDPOINT = os.getenv("REMOTE_METTA_ENDPOINT", "")
REMOTE_METTA_API_KEY = os.getenv("REMOTE_METTA_API_KEY", "")

# ASI Alliance Decentralized Inference (formerly CUDOS)
# Now uses ASI1 API (same infrastructure as main LLM)
USE_CUDOS = os.getenv("USE_CUDOS", "true").lower() == "true"
CUDOS_ENDPOINT = os.getenv("CUDOS_ENDPOINT", "https://api.asi1.ai/v1")  # ASI Alliance endpoint
# Use the same API key as the main LLM (ASI1 key)
CUDOS_API_KEY = os.getenv("CUDOS_API_KEY", LLM_API_KEY)  # Fallback to main LLM key
CUDOS_MODEL = os.getenv("CUDOS_MODEL", "asi1-mini")  # ASI1 Mini model
CUDOS_TIMEOUT = int(os.getenv("CUDOS_TIMEOUT", "60"))

BINANCE_API = "https://api.binance.com/api/v3"
MARKET_DATA_TIMEOUT = int(os.getenv("MARKET_DATA_TIMEOUT", "10"))

CONFIG_DIR = os.getenv("CONFIG_DIR", "./config")
TOKENS_CONFIG = os.path.join(CONFIG_DIR, "tokens.json")
TRADING_RULES_CONFIG = os.path.join(CONFIG_DIR, "trading_rules.json")
USER_PROFILES_CONFIG = os.path.join(CONFIG_DIR, "user_profiles.json")
PAIRS_CONFIG = os.path.join(CONFIG_DIR, "pairs.json")

MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "4"))
IMPROVEMENT_THRESHOLD = float(os.getenv("IMPROVEMENT_THRESHOLD", "0.1"))

REASONING_LOG_FILE = 'reasoning_log.json'
CONVERSATION_LOG_FILE = 'conversation_log.json'

# --- MEMBASE CONFIG ---
MEMBASE_ENABLED = os.getenv("MEMBASE_ENABLED", "true").lower() == "true"
MEMBASE_ACCOUNT = os.getenv("MEMBASE_ACCOUNT", "trading_bot_v1")
# Default to false - Membase testnet hub is often unreliable
MEMBASE_AUTO_UPLOAD = os.getenv("MEMBASE_AUTO_UPLOAD", "false").lower() == "true"
MEMBASE_PRELOAD = os.getenv("MEMBASE_PRELOAD", "false").lower() == "true"
TRADE_KB_DIR = os.getenv("TRADE_KB_DIR", "./trade_kb")

# --- AGENT CONFIG ---
AGENT_NAME = os.getenv("AGENT_NAME", "trading_reasoner")
AGENT_SEED = os.getenv("AGENT_SEED", "trading_bot_seed_v1")
AGENT_PORT = int(os.getenv("AGENT_PORT", "8000"))
AGENT_ENDPOINT = os.getenv("AGENT_ENDPOINT", f"http://localhost:{AGENT_PORT}/submit")
ENABLE_AGENT_SERVER = os.getenv("ENABLE_AGENT_SERVER", "true").lower() == "true"

# --- ON-CHAIN IDENTITY ---
ONCHAIN_REGISTER = os.getenv("ONCHAIN_REGISTER", "false").lower() == "true"

# --- DATA MODELS ---

@dataclass
class MarketData:
    pair: str
    current_price: float
    volatility: float
    volume_24h: float
    trend: str
    atr: float
    rsi: float
    bid_ask_spread: float
    liquidity_score: float
    timestamp: str = field(default_factory=_utc_timestamp)

@dataclass
class RiskMetrics:
    risk_reward_ratio: float
    win_probability: float
    max_drawdown: float
    kelly_percentage: float
    sharpe_ratio: float
    calmar_ratio: float
    portfolio_impact: float
    vega_exposure: float

@dataclass
class Strategy:
    name: str
    description: str
    entry_price: float
    exit_price: float
    position_size: float
    stop_loss: float
    take_profit: float
    expected_return: float
    risk_level: str
    rationale: str
    confidence: float
    pair: str = "ETH/USD"  # Trading pair for this strategy
    iteration: int = 1
    validation_passed: bool = False
    validation_errors: List[str] = field(default_factory=list)
    backtested: bool = False
    backtest_score: float = 0.0

@dataclass
class BacktestResult:
    strategy_name: str
    pair: str
    entry_price: float
    exit_price: float
    position_size: float
    simulated_return: float
    max_drawdown: float
    win_rate: float
    sharpe_ratio: float
    profit_factor: float
    num_trades: int = 100

@dataclass
class UserProfile:
    user_id: str
    risk_tolerance: str
    max_position_size: float
    max_daily_loss: float
    max_leverage: float
    preferred_pairs: List[str] = field(default_factory=list)
    blacklisted_pairs: List[str] = field(default_factory=list)
    max_portfolio_allocation: float = 10.0

@dataclass
class ConversationMessage:
    sender: str
    role: str  # "user" or "assistant"
    content: str
    message_type: str  # "chat", "strategy_approval", "execution_update"
    timestamp: str = field(default_factory=_utc_timestamp)
    related_reasoning_id: Optional[str] = None

@dataclass
class AutonomousReasoning:
    goal: str
    user_context: str
    final_strategy: Optional[Strategy] = None
    risk_metrics: Optional[RiskMetrics] = None
    backtest_result: Optional[BacktestResult] = None
    approval_summary: str = ""
    reasoning_id: str = field(default_factory=lambda: hashlib.md5(str(_utc_now()).encode()).hexdigest()[:8])
    created_at: str = field(default_factory=_utc_timestamp)
    state: str = "pending_approval"  # pending_approval, approved, executed, rejected, cancelled
    total_iterations: int = 0

@dataclass
class MakerConfig:
    """Maker-specified constraints for quote generation."""
    maker_address: str = ""
    allowed_pairs: List[str] = field(default_factory=list)
    max_trade_size: Optional[float] = None
    daily_caps: Dict[str, float] = field(default_factory=dict)  # token -> max daily volume
    paused: bool = False
    min_spread_bps: int = 10  # minimum spread in basis points
    max_spread_bps: int = 100
    default_ttl_sec: int = 60
    strategies: Dict[str, str] = field(default_factory=dict)  # strategyHash -> description


# --- STRATEGY AGENT DATA MODELS ---

class RejectReason:
    """Canonical reject reasons for quote requests."""
    MAKER_PAUSED = "MAKER_PAUSED"
    INSUFFICIENT_BUDGET = "INSUFFICIENT_BUDGET"
    STALE_PRICING = "STALE_PRICING"
    PAIR_NOT_ALLOWED = "PAIR_NOT_ALLOWED"
    EXCEEDS_MAX_TRADE_SIZE = "EXCEEDS_MAX_TRADE_SIZE"
    EXCEEDS_DAILY_CAP = "EXCEEDS_DAILY_CAP"
    STRATEGY_INACTIVE = "STRATEGY_INACTIVE"
    STRATEGY_DOCKED = "STRATEGY_DOCKED"
    INSUFFICIENT_ALLOWANCE = "INSUFFICIENT_ALLOWANCE"
    INVALID_CHAIN = "INVALID_CHAIN"
    INVALID_TOKEN = "INVALID_TOKEN"
    NONCE_EXHAUSTED = "NONCE_EXHAUSTED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


@dataclass
class QuoteRequest:
    """Incoming quote request from a taker."""
    chain_id: int
    side: str  # "BUY" or "SELL"
    token_in: str
    token_out: str
    amount: float  # amountIn for SELL, amountOut for BUY
    taker: str  # taker address
    recipient: Optional[str] = None  # defaults to taker if not specified
    idempotency_key: Optional[str] = None
    timestamp: str = field(default_factory=_utc_timestamp)

    def __post_init__(self):
        if self.recipient is None:
            self.recipient = self.taker
        if self.idempotency_key is None:
            # Generate deterministic idempotency key from request params
            key_data = f"{self.chain_id}:{self.side}:{self.token_in}:{self.token_out}:{self.amount}:{self.taker}:{self.timestamp[:19]}"
            self.idempotency_key = hashlib.sha256(key_data.encode()).hexdigest()[:16]


@dataclass
class PricingSnapshot:
    """Current pricing data from pricing service."""
    token_in: str
    token_out: str
    mid_price: float  # fair mid-market price
    bid_price: float
    ask_price: float
    spread_bps: int  # current market spread in basis points
    timestamp: str
    is_stale: bool = False  # True if pricing is older than threshold
    confidence: float = 1.0  # 0-1, lower if pricing uncertain


@dataclass
class ChainSnapshot:
    """On-chain state for feasibility checks."""
    chain_id: int
    strategy_hash: str
    is_active: bool  # rawBalances.tokensCount != 0
    is_docked: bool  # strategy is DOCKED
    token_out_budget: float  # available tokenOut in strategy
    token_in_budget: float  # available tokenIn in strategy
    maker_allowance: float  # maker → Aqua allowance for tokenOut
    last_updated: str
    
    @property
    def is_feasible(self) -> bool:
        """Check if strategy is in a usable state."""
        return self.is_active and not self.is_docked


@dataclass
class QuoteIntent:
    """Deterministic quote intent output."""
    maker: str
    token_in: str
    token_out: str
    amount_in: float
    amount_out: float
    strategy_hash: str
    nonce: int
    expiry: int  # Unix timestamp
    min_out_net: float  # minimum output after fees
    ttl_sec: int
    
    # Metadata
    idempotency_key: str
    created_at: str = field(default_factory=_utc_timestamp)
    reason: Optional[str] = None  # Only set if rejected
    rejected: bool = False
    
    # Explainability
    rationale: str = ""
    spread_bps: int = 0
    price_used: float = 0.0


@dataclass
class QuoteExplainability:
    """Plain-language explanation of quote decision."""
    intent: QuoteIntent
    description: str
    rationale: str
    pricing_source: str
    feasibility_checks: List[str]
    warnings: List[str] = field(default_factory=list)


class StrategyAgent:
    """
    Autonomous quoting brain that produces deterministic, on-chain-feasible quote intents.
    
    Responsibilities:
    - Quote Intent synthesis with side-aware amounts, spreads, TTL, and nonce allocation
    - Policy enforcement (maker settings, pair restrictions, caps, paused states)
    - On-chain feasibility gate (strategy active, budget sufficient, allowances valid)
    - State management (nonces, quote cache, fill tracking, budget snapshots)
    """

    def __init__(self, supported_chains: List[int] = None):
        self.supported_chains = supported_chains or [1, 56, 137, 42161]  # ETH, BSC, Polygon, Arbitrum
        
        # Per-maker state
        self._maker_nonces: Dict[str, int] = {}  # maker_address -> current nonce
        self._quote_cache: Dict[str, QuoteIntent] = {}  # idempotency_key -> QuoteIntent
        self._cache_expiry: Dict[str, int] = {}  # idempotency_key -> expiry timestamp
        self._daily_volumes: Dict[str, Dict[str, float]] = {}  # maker -> token -> volume today
        self._last_volume_reset: str = _utc_date_str()
        
        # Fill/revert tracking
        self._fills: Dict[str, Dict] = {}  # nonce -> fill data
        self._reverts: Dict[str, Dict] = {}  # nonce -> revert data
        
        print("[STRATEGY_AGENT] Initialized")

    def _reset_daily_volumes_if_needed(self):
        """Reset daily volume tracking at midnight UTC."""
        today = _utc_date_str()
        if today != self._last_volume_reset:
            self._daily_volumes.clear()
            self._last_volume_reset = today

    def _get_next_nonce(self, maker: str) -> int:
        """Get and increment monotonic nonce for maker."""
        if maker not in self._maker_nonces:
            self._maker_nonces[maker] = 0
        nonce = self._maker_nonces[maker]
        self._maker_nonces[maker] += 1
        return nonce

    def _get_cached_quote(self, idempotency_key: str) -> Optional[QuoteIntent]:
        """Return cached quote if still valid."""
        if idempotency_key in self._quote_cache:
            expiry = self._cache_expiry.get(idempotency_key, 0)
            if _utc_unix() < expiry:
                return self._quote_cache[idempotency_key]
            else:
                # Expired, remove from cache
                del self._quote_cache[idempotency_key]
                del self._cache_expiry[idempotency_key]
        return None

    def _cache_quote(self, quote: QuoteIntent):
        """Cache quote by idempotency key."""
        self._quote_cache[quote.idempotency_key] = quote
        self._cache_expiry[quote.idempotency_key] = quote.expiry

    def _update_daily_volume(self, maker: str, token: str, amount: float):
        """Track daily volume for cap enforcement."""
        if maker not in self._daily_volumes:
            self._daily_volumes[maker] = {}
        if token not in self._daily_volumes[maker]:
            self._daily_volumes[maker][token] = 0.0
        self._daily_volumes[maker][token] += amount

    def _get_daily_volume(self, maker: str, token: str) -> float:
        """Get current daily volume for a token."""
        return self._daily_volumes.get(maker, {}).get(token, 0.0)

    def _create_rejected_intent(
        self,
        request: QuoteRequest,
        maker_config: MakerConfig,
        reason: str,
        rationale: str
    ) -> QuoteIntent:
        """Create a rejected QuoteIntent with reason."""
        return QuoteIntent(
            maker=maker_config.maker_address,
            token_in=request.token_in,
            token_out=request.token_out,
            amount_in=0.0,
            amount_out=0.0,
            strategy_hash="",
            nonce=-1,
            expiry=0,
            min_out_net=0.0,
            ttl_sec=0,
            idempotency_key=request.idempotency_key,
            reason=reason,
            rejected=True,
            rationale=rationale
        )

    def _select_strategy_hash(
        self,
        maker_config: MakerConfig,
        token_in: str,
        token_out: str
    ) -> Optional[str]:
        """Select appropriate strategy hash for the pair."""
        pair_key = f"{token_in}/{token_out}"
        reverse_key = f"{token_out}/{token_in}"
        
        # Check if maker has a specific strategy for this pair
        if pair_key in maker_config.strategies:
            return maker_config.strategies[pair_key]
        if reverse_key in maker_config.strategies:
            return maker_config.strategies[reverse_key]
        
        # Default strategy hash (would be configured per deployment)
        default_hash = hashlib.sha256(f"aqua_default_{pair_key}".encode()).hexdigest()[:16]
        return default_hash

    def _calculate_amounts(
        self,
        request: QuoteRequest,
        pricing: PricingSnapshot,
        maker_config: MakerConfig
    ) -> Tuple[float, float, int]:
        """
        Calculate side-aware amountIn/amountOut and spread.
        Returns (amount_in, amount_out, spread_bps).
        """
        # Determine spread based on market conditions and maker config
        market_spread = pricing.spread_bps
        spread_bps = max(maker_config.min_spread_bps, min(market_spread, maker_config.max_spread_bps))
        
        # Adjust spread based on pricing confidence
        if pricing.confidence < 0.8:
            spread_bps = int(spread_bps * 1.5)  # Widen spread for uncertain pricing
        
        spread_multiplier = 1 + (spread_bps / 10000)
        
        if request.side == "BUY":
            # Taker wants to buy token_out, pays token_in
            # request.amount is the desired amount_out
            amount_out = request.amount
            # Calculate amount_in with spread (taker pays more)
            amount_in = amount_out * pricing.ask_price * spread_multiplier
        else:  # SELL
            # Taker wants to sell token_in, receives token_out
            # request.amount is the amount_in being sold
            amount_in = request.amount
            # Calculate amount_out with spread (taker receives less)
            amount_out = amount_in / pricing.bid_price / spread_multiplier
        
        return amount_in, amount_out, spread_bps

    def generate_quote(
        self,
        request: QuoteRequest,
        maker_config: MakerConfig,
        pricing: PricingSnapshot,
        chain_snapshot: ChainSnapshot
    ) -> Tuple[QuoteIntent, QuoteExplainability]:
        """
        Generate a deterministic quote intent for the given request.
        
        Returns:
            Tuple of (QuoteIntent, QuoteExplainability)
            
        The QuoteIntent will have rejected=True and reason set if the quote
        cannot be fulfilled due to policy or feasibility issues.
        """
        self._reset_daily_volumes_if_needed()
        feasibility_checks = []
        warnings = []

        # 1. Check idempotency - return cached quote if exists
        cached = self._get_cached_quote(request.idempotency_key)
        if cached is not None:
            return cached, QuoteExplainability(
                intent=cached,
                description="Returning cached quote for idempotency key",
                rationale="Quote was previously generated and is still valid",
                pricing_source="cached",
                feasibility_checks=["IDEMPOTENCY_HIT"]
            )

        # 2. Validate chain
        if request.chain_id not in self.supported_chains:
            intent = self._create_rejected_intent(
                request, maker_config, RejectReason.INVALID_CHAIN,
                f"Chain {request.chain_id} not supported"
            )
            return intent, QuoteExplainability(
                intent=intent,
                description=f"Quote rejected: unsupported chain {request.chain_id}",
                rationale="The requested chain is not in the list of supported chains",
                pricing_source="none",
                feasibility_checks=["CHAIN_CHECK: FAILED"]
            )
        feasibility_checks.append("CHAIN_CHECK: PASSED")

        # 3. Check maker paused state
        if maker_config.paused:
            intent = self._create_rejected_intent(
                request, maker_config, RejectReason.MAKER_PAUSED,
                "Maker is currently paused"
            )
            return intent, QuoteExplainability(
                intent=intent,
                description="Quote rejected: maker is paused",
                rationale="The maker has paused quote generation",
                pricing_source="none",
                feasibility_checks=["MAKER_PAUSED_CHECK: FAILED"]
            )
        feasibility_checks.append("MAKER_PAUSED_CHECK: PASSED")

        # 4. Check pair allowed
        pair = f"{request.token_in}/{request.token_out}"
        reverse_pair = f"{request.token_out}/{request.token_in}"
        if maker_config.allowed_pairs and pair not in maker_config.allowed_pairs and reverse_pair not in maker_config.allowed_pairs:
            intent = self._create_rejected_intent(
                request, maker_config, RejectReason.PAIR_NOT_ALLOWED,
                f"Pair {pair} not in allowed list"
            )
            return intent, QuoteExplainability(
                intent=intent,
                description=f"Quote rejected: pair {pair} not allowed",
                rationale=f"Maker only allows: {maker_config.allowed_pairs}",
                pricing_source="none",
                feasibility_checks=["PAIR_ALLOWED_CHECK: FAILED"]
            )
        feasibility_checks.append("PAIR_ALLOWED_CHECK: PASSED")

        # 5. Check pricing staleness
        if pricing.is_stale:
            intent = self._create_rejected_intent(
                request, maker_config, RejectReason.STALE_PRICING,
                "Pricing data is stale"
            )
            return intent, QuoteExplainability(
                intent=intent,
                description="Quote rejected: stale pricing data",
                rationale=f"Pricing timestamp {pricing.timestamp} is too old",
                pricing_source=pricing.timestamp,
                feasibility_checks=["PRICING_FRESHNESS_CHECK: FAILED"]
            )
        feasibility_checks.append("PRICING_FRESHNESS_CHECK: PASSED")

        # 6. Calculate amounts
        amount_in, amount_out, spread_bps = self._calculate_amounts(request, pricing, maker_config)

        # 7. Check max trade size
        if maker_config.max_trade_size is not None:
            if amount_in > maker_config.max_trade_size or amount_out > maker_config.max_trade_size:
                intent = self._create_rejected_intent(
                    request, maker_config, RejectReason.EXCEEDS_MAX_TRADE_SIZE,
                    f"Trade size exceeds max {maker_config.max_trade_size}"
                )
                return intent, QuoteExplainability(
                    intent=intent,
                    description=f"Quote rejected: exceeds max trade size",
                    rationale=f"Amount {max(amount_in, amount_out)} > max {maker_config.max_trade_size}",
                    pricing_source=pricing.timestamp,
                    feasibility_checks=["MAX_TRADE_SIZE_CHECK: FAILED"]
                )
        feasibility_checks.append("MAX_TRADE_SIZE_CHECK: PASSED")

        # 8. Check daily caps
        token_out_daily = self._get_daily_volume(maker_config.maker_address, request.token_out)
        if request.token_out in maker_config.daily_caps:
            cap = maker_config.daily_caps[request.token_out]
            if token_out_daily + amount_out > cap:
                intent = self._create_rejected_intent(
                    request, maker_config, RejectReason.EXCEEDS_DAILY_CAP,
                    f"Would exceed daily cap for {request.token_out}"
                )
                return intent, QuoteExplainability(
                    intent=intent,
                    description=f"Quote rejected: exceeds daily cap for {request.token_out}",
                    rationale=f"Current: {token_out_daily}, requested: {amount_out}, cap: {cap}",
                    pricing_source=pricing.timestamp,
                    feasibility_checks=["DAILY_CAP_CHECK: FAILED"]
                )
        feasibility_checks.append("DAILY_CAP_CHECK: PASSED")

        # 9. On-chain feasibility: strategy active
        if not chain_snapshot.is_active:
            intent = self._create_rejected_intent(
                request, maker_config, RejectReason.STRATEGY_INACTIVE,
                "Strategy is not active (tokensCount == 0)"
            )
            return intent, QuoteExplainability(
                intent=intent,
                description="Quote rejected: strategy inactive on-chain",
                rationale="The Aqua strategy has no tokens (rawBalances.tokensCount == 0)",
                pricing_source=pricing.timestamp,
                feasibility_checks=["STRATEGY_ACTIVE_CHECK: FAILED"]
            )
        feasibility_checks.append("STRATEGY_ACTIVE_CHECK: PASSED")

        # 10. On-chain feasibility: strategy not docked
        if chain_snapshot.is_docked:
            intent = self._create_rejected_intent(
                request, maker_config, RejectReason.STRATEGY_DOCKED,
                "Strategy is DOCKED"
            )
            return intent, QuoteExplainability(
                intent=intent,
                description="Quote rejected: strategy is docked",
                rationale="The Aqua strategy is in DOCKED state and cannot process trades",
                pricing_source=pricing.timestamp,
                feasibility_checks=["STRATEGY_DOCKED_CHECK: FAILED"]
            )
        feasibility_checks.append("STRATEGY_DOCKED_CHECK: PASSED")

        # 11. On-chain feasibility: sufficient tokenOut budget
        if chain_snapshot.token_out_budget < amount_out:
            intent = self._create_rejected_intent(
                request, maker_config, RejectReason.INSUFFICIENT_BUDGET,
                f"Insufficient tokenOut budget: {chain_snapshot.token_out_budget} < {amount_out}"
            )
            return intent, QuoteExplainability(
                intent=intent,
                description="Quote rejected: insufficient budget",
                rationale=f"Strategy has {chain_snapshot.token_out_budget} {request.token_out}, need {amount_out}",
                pricing_source=pricing.timestamp,
                feasibility_checks=["BUDGET_CHECK: FAILED"]
            )
        feasibility_checks.append("BUDGET_CHECK: PASSED")

        # 12. On-chain feasibility: sufficient allowance
        if chain_snapshot.maker_allowance < amount_out:
            intent = self._create_rejected_intent(
                request, maker_config, RejectReason.INSUFFICIENT_ALLOWANCE,
                f"Insufficient maker allowance: {chain_snapshot.maker_allowance} < {amount_out}"
            )
            return intent, QuoteExplainability(
                intent=intent,
                description="Quote rejected: insufficient allowance",
                rationale=f"Maker → Aqua allowance is {chain_snapshot.maker_allowance}, need {amount_out}",
                pricing_source=pricing.timestamp,
                feasibility_checks=["ALLOWANCE_CHECK: FAILED"]
            )
        feasibility_checks.append("ALLOWANCE_CHECK: PASSED")

        # 13. All checks passed - generate quote intent
        strategy_hash = self._select_strategy_hash(maker_config, request.token_in, request.token_out)
        nonce = self._get_next_nonce(maker_config.maker_address)
        ttl_sec = maker_config.default_ttl_sec
        expiry = _utc_unix() + ttl_sec
        
        # Calculate minOutNet (amount_out minus estimated fees, e.g., 0.1%)
        fee_bps = 10  # 0.1% fee estimate
        min_out_net = amount_out * (1 - fee_bps / 10000)

        # Build rationale
        rationale = (
            f"Generated {request.side} quote for {pair} at {spread_bps}bps spread. "
            f"Mid price: {pricing.mid_price:.6f}, "
            f"Amount in: {amount_in:.6f} {request.token_in}, "
            f"Amount out: {amount_out:.6f} {request.token_out}. "
            f"Strategy budget: {chain_snapshot.token_out_budget:.2f} (sufficient). "
            f"TTL: {ttl_sec}s."
        )

        intent = QuoteIntent(
            maker=maker_config.maker_address,
            token_in=request.token_in,
            token_out=request.token_out,
            amount_in=amount_in,
            amount_out=amount_out,
            strategy_hash=strategy_hash,
            nonce=nonce,
            expiry=expiry,
            min_out_net=min_out_net,
            ttl_sec=ttl_sec,
            idempotency_key=request.idempotency_key,
            rationale=rationale,
            spread_bps=spread_bps,
            price_used=pricing.mid_price
        )

        # Cache the quote
        self._cache_quote(intent)
        
        # Update daily volume tracking
        self._update_daily_volume(maker_config.maker_address, request.token_out, amount_out)

        # Add warnings if applicable
        if pricing.confidence < 0.9:
            warnings.append(f"Pricing confidence is {pricing.confidence:.0%}, spread widened")
        if chain_snapshot.token_out_budget < amount_out * 2:
            warnings.append(f"Budget running low: {chain_snapshot.token_out_budget:.2f} remaining")

        explainability = QuoteExplainability(
            intent=intent,
            description=f"Quote generated successfully for {request.side} {pair}",
            rationale=rationale,
            pricing_source=pricing.timestamp,
            feasibility_checks=feasibility_checks,
            warnings=warnings
        )

        return intent, explainability

    def record_fill(self, maker: str, nonce: int, tx_hash: str, actual_out: float):
        """Record a successful fill for tracking."""
        key = f"{maker}:{nonce}"
        self._fills[key] = {
            "tx_hash": tx_hash,
            "actual_out": actual_out,
            "timestamp": _utc_timestamp()
        }

    def record_revert(self, maker: str, nonce: int, reason: str):
        """Record a revert for analysis."""
        key = f"{maker}:{nonce}"
        self._reverts[key] = {
            "reason": reason,
            "timestamp": _utc_timestamp()
        }
        # Log for debugging - this should never happen if feasibility checks are correct
        print(f"[STRATEGY_AGENT] WARNING: Revert recorded for {key}: {reason}")

    def get_maker_stats(self, maker: str) -> Dict[str, Any]:
        """Get statistics for a maker."""
        fills = sum(1 for k in self._fills if k.startswith(maker))
        reverts = sum(1 for k in self._reverts if k.startswith(maker))
        return {
            "maker": maker,
            "current_nonce": self._maker_nonces.get(maker, 0),
            "fills": fills,
            "reverts": reverts,
            "revert_rate": reverts / max(fills + reverts, 1),
            "daily_volumes": self._daily_volumes.get(maker, {})
        }


# --- CONFIG MANAGER ---

class ConfigManager:
    """Load and manage configuration from external files."""
    
    def __init__(self, config_dir: str = CONFIG_DIR):
        self.config_dir = config_dir
        self._ensure_config_dir()
        self.tokens = self._load_tokens()
        self.trading_rules = self._load_trading_rules()
        self.user_profiles = self._load_user_profiles()
        self.pairs = self._load_pairs()

    def _ensure_config_dir(self):
        os.makedirs(self.config_dir, exist_ok=True)

    def _load_tokens(self) -> Dict[str, Any]:
        if os.path.exists(TOKENS_CONFIG):
            try:
                with open(TOKENS_CONFIG, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[WARN] Failed to load tokens: {e}")
        
        default_tokens = {
            "stable": ["DAI", "USDC", "USDT", "TUSD"],
            "major": ["BTC", "ETH", "SOL", "AVAX"],
            "defi": ["AAVE", "UNI", "CURVE", "AQUA"]
        }
        self._save_tokens(default_tokens)
        return default_tokens

    def _load_pairs(self) -> List[str]:
        if os.path.exists(PAIRS_CONFIG):
            try:
                with open(PAIRS_CONFIG, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[WARN] Failed to load pairs: {e}")
        
        default_pairs = [
            "DAI/USDC", "ETH/USD", "BTC/USD", "USDT/USDC",
            "AQUA/USDT", "SOL/USD", "AAVE/USD"
        ]
        self._save_pairs(default_pairs)
        return default_pairs

    def _load_trading_rules(self) -> Dict[str, Any]:
        if os.path.exists(TRADING_RULES_CONFIG):
            try:
                with open(TRADING_RULES_CONFIG, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[WARN] Failed to load trading rules: {e}")
        
        default_rules = {
            "min_rr_ratio": 1.5,
            "min_confidence": 0.6,
            "min_liquidity_score": 60.0,
            "max_position_size": 100000.0,
            "max_leverage": 2.0,
            "acceptable_volatility_range": {"low": 0.5, "high": 15.0},
            "min_win_probability": 0.45,
            "max_kelly_percentage": 0.25,
            "spread_tolerance": 0.02
        }
        self._save_trading_rules(default_rules)
        return default_rules

    def _load_user_profiles(self) -> Dict[str, Any]:
        if os.path.exists(USER_PROFILES_CONFIG):
            try:
                with open(USER_PROFILES_CONFIG, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[WARN] Failed to load user profiles: {e}")
        
        default_profiles = {
            "conservative": {
                "risk_tolerance": "conservative",
                "max_position_size": 25000,
                "max_daily_loss": 500,
                "max_leverage": 1.0,
                "preferred_pairs": ["DAI/USDC", "USDT/USDC"],
                "max_portfolio_allocation": 5.0
            },
            "moderate": {
                "risk_tolerance": "moderate",
                "max_position_size": 50000,
                "max_daily_loss": 1500,
                "max_leverage": 2.0,
                "preferred_pairs": ["DAI/USDC", "ETH/USD", "BTC/USD"],
                "max_portfolio_allocation": 10.0
            },
            "aggressive": {
                "risk_tolerance": "aggressive",
                "max_position_size": 100000,
                "max_daily_loss": 5000,
                "max_leverage": 5.0,
                "preferred_pairs": ["DAI/USDC", "ETH/USD", "BTC/USD", "SOL/USD"],
                "max_portfolio_allocation": 20.0
            }
        }
        self._save_user_profiles(default_profiles)
        return default_profiles

    def _save_tokens(self, tokens: Dict[str, Any]):
        os.makedirs(self.config_dir, exist_ok=True)
        with open(TOKENS_CONFIG, 'w') as f:
            json.dump(tokens, f, indent=2)

    def _save_pairs(self, pairs: List[str]):
        os.makedirs(self.config_dir, exist_ok=True)
        with open(PAIRS_CONFIG, 'w') as f:
            json.dump(pairs, f, indent=2)

    def _save_trading_rules(self, rules: Dict[str, Any]):
        os.makedirs(self.config_dir, exist_ok=True)
        with open(TRADING_RULES_CONFIG, 'w') as f:
            json.dump(rules, f, indent=2)

    def _save_user_profiles(self, profiles: Dict[str, Any]):
        os.makedirs(self.config_dir, exist_ok=True)
        with open(USER_PROFILES_CONFIG, 'w') as f:
            json.dump(profiles, f, indent=2)

    def get_user_profile(self, risk_level: str) -> UserProfile:
        profile_data = self.user_profiles.get(risk_level.lower(), self.user_profiles["moderate"])
        return UserProfile(
            user_id="current_user",
            risk_tolerance=profile_data["risk_tolerance"],
            max_position_size=profile_data["max_position_size"],
            max_daily_loss=profile_data["max_daily_loss"],
            max_leverage=profile_data["max_leverage"],
            preferred_pairs=profile_data.get("preferred_pairs", []),
            max_portfolio_allocation=profile_data.get("max_portfolio_allocation", 10.0)
        )

    def is_pair_valid(self, pair: str) -> bool:
        return pair in self.pairs

    def get_rule(self, rule_name: str, default: Any = None) -> Any:
        return self.trading_rules.get(rule_name, default)

# --- MARKET DATA CLIENT ---

class MarketDataClient:
    """Fetch real market data from Binance with robust symbol discovery and retry logic."""
    
    def __init__(self, timeout: int = MARKET_DATA_TIMEOUT):
        self.binance_api = BINANCE_API
        self.binance_exchange_info_url = "https://api.binance.com/api/v3/exchangeInfo"
        self.timeout = timeout
        self.symbol_cache = {}
        self.cache_timestamps = {}
        self.cache_ttl = 3600  # 1 hour cache
        self.max_retries = 3
        self.retry_delay = 1  # seconds
        self.available_symbols = None  # Lazy-loaded once

    def _is_cache_valid(self, pair: str) -> bool:
        """Check if cached symbol is still valid."""
        if pair not in self.symbol_cache:
            return False
        
        timestamp = self.cache_timestamps.get(pair, 0)
        return (_utc_unix() - timestamp) < self.cache_ttl

    def _load_exchange_symbols(self) -> List[str]:
        """Load all valid trading pairs from Binance once."""
        if self.available_symbols is not None:
            return self.available_symbols
        
        try:
            print("[BINANCE] Fetching exchange info...")
            resp = requests.get(self.binance_exchange_info_url, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            
            symbols = []
            for symbol_obj in data.get("symbols", []):
                if symbol_obj.get("status") == "TRADING":
                    symbols.append(symbol_obj.get("symbol"))
            
            self.available_symbols = symbols
            print(f"[BINANCE] Loaded {len(symbols)} trading pairs")
            return symbols
        except Exception as e:
            print(f"[WARN] Failed to load exchange info: {e}")
            return []

    def _discover_trading_pair(self, pair: str) -> str:
        """Robustly discover correct Binance symbol for a trading pair."""
        
        # Check cache first
        if self._is_cache_valid(pair):
            return self.symbol_cache[pair]
        
        base, quote = pair.split("/") if "/" in pair else (pair[:3], pair[3:])
        base = base.upper()
        quote = quote.upper()
        
        # Load all available symbols
        available = self._load_exchange_symbols()
        if not available:
            raise Exception(f"[FAIL] Cannot access Binance exchange info")
        
        # Smart matching strategy
        candidates = []
        
        # Priority 1: Exact quote match
        for symbol in available:
            if symbol.startswith(base):
                quote_part = symbol[len(base):]
                if quote_part == quote:
                    candidates.append((symbol, 100))  # Highest priority
        
        # Priority 2: USDT fallback (very common)
        if quote == "USD":
            for symbol in available:
                if symbol == f"{base}USDT":
                    candidates.append((symbol, 90))
        
        # Priority 3: Partial matches
        for symbol in available:
            if symbol.startswith(base) and quote in symbol:
                candidates.append((symbol, 50))
        
        if not candidates:
            raise Exception(f"[FAIL] No Binance symbol found for {pair}. Available bases: {[s[:5] for s in available[:20]]}")
        
        # Sort by priority and verify with quick request
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        for symbol, priority in candidates:
            try:
                # Quick verification
                test_url = f"{self.binance_api}/ticker/price?symbol={symbol}"
                resp = requests.get(test_url, timeout=3)
                if resp.status_code == 200:
                    self.symbol_cache[pair] = symbol
                    self.cache_timestamps[pair] = _utc_unix()
                    print(f"[DISCOVER] {pair} → {symbol}")
                    return symbol
            except:
                continue
        
        raise Exception(f"[FAIL] All candidate symbols failed for {pair}: {[s[0] for s in candidates[:3]]}")

    def get_market_data(self, pair: str) -> MarketData:
        """Fetch real market data with retry logic and rate limit handling."""
        
        symbol = self._discover_trading_pair(pair)
        
        # Retry logic for network issues
        for attempt in range(self.max_retries):
            try:
                # Fetch ticker
                ticker_url = f"{self.binance_api}/ticker/24hr?symbol={symbol}"
                ticker_resp = requests.get(ticker_url, timeout=self.timeout)
                
                if ticker_resp.status_code == 429:  # Rate limited
                    print(f"[RATE-LIMIT] Attempt {attempt + 1}, waiting {self.retry_delay}s...")
                    import time
                    time.sleep(self.retry_delay)
                    continue
                
                ticker_resp.raise_for_status()
                ticker_data = ticker_resp.json()
                
                if "code" in ticker_data and ticker_data["code"] != 0:
                    raise Exception(f"Binance API error: {ticker_data.get('msg', 'Unknown')}")
                
                # Fetch orderbook
                depth_url = f"{self.binance_api}/depth?symbol={symbol}&limit=10"
                depth_resp = requests.get(depth_url, timeout=self.timeout)
                depth_resp.raise_for_status()
                depth_data = depth_resp.json()
                
                # Parse data
                current_price = float(ticker_data.get("lastPrice", 0))
                if current_price <= 0:
                    raise Exception(f"Invalid price for {pair}")
                
                # Better liquidity calculation from orderbook
                bids = depth_data.get("bids", [])
                asks = depth_data.get("asks", [])
                
                bid = float(bids[0][0]) if bids else current_price
                ask = float(asks[0][0]) if asks else current_price
                
                # Liquidity: sum of top 10 bid/ask volumes
                bid_volume = sum([float(b[1]) for b in bids])
                ask_volume = sum([float(a[1]) for a in asks])
                total_orderbook_volume = bid_volume + ask_volume
                
                high_price = float(ticker_data.get("highPrice", current_price))
                low_price = float(ticker_data.get("lowPrice", current_price))
                
                if high_price <= 0 or low_price <= 0:
                    raise Exception(f"Invalid high/low for {pair}")
                
                # More realistic volatility
                volatility = ((high_price - low_price) / current_price * 100)
                
                # Volume in quote currency
                volume_24h = float(ticker_data.get("quoteAssetVolume", 0))
                price_change = float(ticker_data.get("priceChangePercent", 0))
                
                # RSI approximation
                rsi = 50 + (price_change / 10)
                rsi = max(0, min(100, rsi))
                
                trend = "bullish" if price_change > 1 else "bearish" if price_change < -1 else "neutral"
                
                bid_ask_spread = ((ask - bid) / current_price * 100) if current_price > 0 else 0.01
                
                # Better liquidity score: based on orderbook depth and 24h volume
                volume_score = min(100, (volume_24h / 10000000) * 50)  # Calibrated for realistic volumes
                depth_score = min(100, (total_orderbook_volume / 100) * 50)
                liquidity_score = (volume_score + depth_score) / 2
                
                return MarketData(
                    pair=pair,
                    current_price=current_price,
                    volatility=volatility,
                    volume_24h=volume_24h,
                    trend=trend,
                    atr=volatility * 0.5,
                    rsi=rsi,
                    bid_ask_spread=bid_ask_spread,
                    liquidity_score=liquidity_score
                )
            
            except requests.Timeout:
                if attempt < self.max_retries - 1:
                    print(f"[RETRY] Timeout attempt {attempt + 1}/{self.max_retries}")
                    import time
                    time.sleep(self.retry_delay)
                    continue
                raise Exception(f"[FAIL] Market data timeout after {self.max_retries} attempts")
            
            except requests.RequestException as e:
                if attempt < self.max_retries - 1:
                    print(f"[RETRY] Request failed attempt {attempt + 1}/{self.max_retries}: {e}")
                    import time
                    time.sleep(self.retry_delay)
                    continue
                raise Exception(f"[FAIL] Market data request failed: {e}")
            
            except Exception as e:
                if attempt < self.max_retries - 1:
                    print(f"[RETRY] Error attempt {attempt + 1}/{self.max_retries}: {e}")
                    import time
                    time.sleep(self.retry_delay)
                    continue
                raise
        
        raise Exception(f"[FAIL] All retry attempts exhausted for {pair}")

# --- METTA KNOWLEDGE BASE ---

class MeTTaKnowledgeBase:
    def __init__(self, storage_dir: str = METTA_STORAGE_DIR):
        self.storage_dir = storage_dir
        self.enabled = METTA_ENABLED
        self.use_remote = USE_REMOTE_METTA and bool(REMOTE_METTA_ENDPOINT)
        self._metta = None
        if _HYPERON_AVAILABLE and self.enabled and not self.use_remote:
            try:
                self._metta = HyperonMeTTa()
                print("[METTA] Hyperon runner initialized")
            except Exception as e:
                print(f"[METTA] Failed to init Hyperon runner: {e}")
        
        self._initialize_storage()
        self._load_default_knowledge_base()

    def _initialize_storage(self):
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)

    def _load_default_knowledge_base(self):
        kb_file = os.path.join(self.storage_dir, "trading_rules.metta")
        
        if not os.path.exists(kb_file):
            default_kb = """
; Trading Rules Knowledge Base

(safe-pair "DAI" "USDC")
(safe-pair "ETH" "USD")
(safe-pair "BTC" "USD")
(safe-pair "USDT" "USDC")

(valid-position-size (Size) (if (<= Size 100000)))
(valid-stop-loss (Entry StopLoss) (if (< StopLoss Entry)))
(valid-take-profit (Entry TakeProfit) (if (> TakeProfit Entry)))
(valid-rr-ratio (RR) (if (>= RR 1.5)))

(strategy-valid (entry exit sl tp rr confidence) 
  (and 
    (valid-stop-loss entry sl)
    (valid-take-profit entry tp)
    (valid-rr-ratio rr)
    (>= confidence 0.6)))
"""
            with open(kb_file, 'w') as f:
                f.write(default_kb)
        
        # Load KB into Hyperon runner if available
        if self._metta:
            try:
                with open(kb_file, 'r') as f:
                    content = f.read()
                    self._metta.run(content)
                print(f"[METTA] Loaded KB from {kb_file}")
            except Exception as e:
                print(f"[METTA] Failed to load KB into Hyperon: {e}")

    def validate_strategy(self, strategy: Strategy, market_data: MarketData, config: ConfigManager) -> Tuple[bool, List[str]]:
        errors = []
        rules = config.trading_rules
        
        if strategy.stop_loss >= strategy.entry_price:
            errors.append(f"Stop loss must be < entry price")
        
        if strategy.take_profit <= strategy.entry_price:
            errors.append(f"Take profit must be > entry price")
        
        potential_loss = strategy.entry_price - strategy.stop_loss
        potential_gain = strategy.take_profit - strategy.entry_price
        if potential_loss > 0:
            rr_ratio = potential_gain / potential_loss
            min_rr = rules.get("min_rr_ratio", 1.5)
            if rr_ratio < min_rr:
                errors.append(f"RR ratio ({rr_ratio:.2f}) < minimum ({min_rr})")
        
        max_size = rules.get("max_position_size", 100000)
        if strategy.position_size > max_size:
            errors.append(f"Position size exceeds maximum")
        
        min_conf = rules.get("min_confidence", 0.6)
        if strategy.confidence < min_conf:
            errors.append(f"Confidence too low")
        
        min_liq = rules.get("min_liquidity_score", 60.0)
        if market_data.liquidity_score < min_liq:
            errors.append(f"Liquidity insufficient")
        
        return len(errors) == 0, errors

    def query_rule(self, rule_name: str, params: Dict[str, Any]) -> bool:
        """Query MeTTa for rule evaluation."""
        # Choose backend: remote KG (e.g. SingularityNET) or local CLI
        if self.use_remote:
            return self._query_rule_remote(rule_name, params)
        else:
            return self._query_rule_local(rule_name, params)

    def _query_rule_local(self, rule_name: str, params: Dict[str, Any]) -> bool:
        """Evaluate rule using local MeTTa CLI or Hyperon library."""
        try:
            param_str = " ".join([f"{k}={v}" for k, v in params.items()])
            query = f"({rule_name} {param_str})"

            # Use Hyperon library if available (Windows native support)
            if self._metta:
                results = self._metta.run(f"!{query}")
                # Check if any result is true/success
                # Hyperon returns a list of results. We check string representation.
                return any("True" in str(r) or "success" in str(r) for r in results)

            # Fallback to CLI (WSL/Linux)
            result = subprocess.run(
                [METTA_EXEC_PATH, "-c", query],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=self.storage_dir
            )

            return result.returncode == 0 and ("true" in result.stdout.lower() or "success" in result.stdout.lower())
        except Exception as e:
            print(f"[METTA] Rule query failed (local): {e}")
            return True

    def _query_rule_remote(self, rule_name: str, params: Dict[str, Any]) -> bool:
        """Evaluate rule using a remote MeTTa / knowledge-graph service."""
        if not REMOTE_METTA_ENDPOINT:
            return self._query_rule_local(rule_name, params)

        try:
            payload = {
                "rule": rule_name,
                "params": params,
            }
            headers = {
                "Content-Type": "application/json",
            }
            if REMOTE_METTA_API_KEY:
                headers["Authorization"] = f"Bearer {REMOTE_METTA_API_KEY}"

            resp = requests.post(
                REMOTE_METTA_ENDPOINT.rstrip("/") + "/query_rule",
                json=payload,
                headers=headers,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            return bool(data.get("result", True))
        except Exception as e:
            print(f"[METTA] Rule query failed (remote): {e}")
            return True

    def get_strategy_recommendation(self, market_conditions: Dict[str, float]) -> Optional[str]:
        """Query MeTTa for strategy recommendation based on market conditions."""
        if self.use_remote:
            return self._get_strategy_recommendation_remote(market_conditions)
        else:
            return self._get_strategy_recommendation_local(market_conditions)

    def _get_strategy_recommendation_local(self, market_conditions: Dict[str, float]) -> Optional[str]:
        """Get strategy recommendation via local MeTTa CLI or Hyperon."""
        try:
            conditions_str = " ".join([f"{k}={v}" for k, v in market_conditions.items()])
            query = f"(recommended-strategy {conditions_str})"

            # Use Hyperon library if available
            if self._metta:
                results = self._metta.run(f"!{query}")
                output = str(results).lower()
            else:
                # Fallback to CLI
                result = subprocess.run(
                    [METTA_EXEC_PATH, "-c", query],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    cwd=self.storage_dir
                )
                output = result.stdout.strip().lower() if result.returncode == 0 and result.stdout else ""

            if "mean-reversion" in output or "mean_reversion" in output:
                return "mean_reversion"
            elif "momentum" in output:
                return "momentum"
            elif "grid" in output:
                return "grid"
            elif "dca" in output:
                return "dca"

            return None
        except Exception as e:
            print(f"[METTA] Strategy recommendation failed (local): {e}")
            return None

    def _get_strategy_recommendation_remote(self, market_conditions: Dict[str, float]) -> Optional[str]:
        """Get strategy recommendation from a remote MeTTa / KG service.

        This is a generic HTTP client that can be pointed to SingularityNET or
        another MeTTa-based service. Adjust the endpoint and response parsing to
        match the actual API contract.
        """
        if not REMOTE_METTA_ENDPOINT:
            return self._get_strategy_recommendation_local(market_conditions)

        try:
            payload = {
                "market_conditions": market_conditions,
            }
            headers = {
                "Content-Type": "application/json",
            }
            if REMOTE_METTA_API_KEY:
                headers["Authorization"] = f"Bearer {REMOTE_METTA_API_KEY}"

            resp = requests.post(
                REMOTE_METTA_ENDPOINT.rstrip("/") + "/recommend_strategy",
                json=payload,
                headers=headers,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("strategy")
        except Exception as e:
            print(f"[METTA] Strategy recommendation failed (remote): {e}")
            return None

    def build_context_summary(self, config: "ConfigManager", user_profile: "UserProfile") -> str:
        """Build a concise symbolic-style summary of trading rules and user profile for LLM prompts.

        This does not call the MeTTa binary; instead, it serializes the key constraints and
        preferences that MeTTa/Python rules are expected to enforce so the LLM can reason
        with them explicitly as part of its context.
        """
        rules = config.trading_rules
        parts = []

        parts.append(
            f"min_rr_ratio={rules.get('min_rr_ratio', 1.5)}, "
            f"min_confidence={rules.get('min_confidence', 0.6)}, "
            f"min_liquidity_score={rules.get('min_liquidity_score', 60.0)}, "
            f"max_position_size={rules.get('max_position_size', 100000.0)}, "
            f"max_leverage={rules.get('max_leverage', 2.0)}"
        )

        vol_range = rules.get("acceptable_volatility_range", {})
        if vol_range:
            parts.append(
                f"acceptable_volatility_range=[{vol_range.get('low', 0.5)}, {vol_range.get('high', 15.0)}]"
            )

        parts.append(
            f"user_risk_tolerance={user_profile.risk_tolerance}, "
            f"user_max_position_size={user_profile.max_position_size}, "
            f"user_max_daily_loss={user_profile.max_daily_loss}, "
            f"user_max_leverage={user_profile.max_leverage}, "
            f"user_max_portfolio_allocation={user_profile.max_portfolio_allocation}"
        )

        if user_profile.preferred_pairs:
            parts.append(
                "preferred_pairs=" + ",".join(sorted(user_profile.preferred_pairs))
            )

        try:
            sample_pairs = ",".join(config.pairs[:5])
            parts.append(f"allowed_pairs_subset={sample_pairs}")
        except Exception:
            pass

        return "; ".join(parts)

# --- USER INTENT INTERPRETER ---

@dataclass
class InterpretedIntent:
    intent_type: str  # "trade", "config", "strategy", "query", "cancel"
    action: str  # "start", "stop", "configure", "explain"
    target: Optional[str] = None  # pair, strategy, etc.
    parameters: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.8
    raw_input: str = ""

class UserIntentInterpreter:
    """Interpret natural language user input into structured intents."""
    
    def __init__(self, llm_endpoint: str, llm_key: str, llm_model: str, 
                 cudos_client: Optional["CUDOSInferenceClient"] = None):
        self.llm_endpoint = llm_endpoint
        self.llm_key = llm_key
        self.llm_model = llm_model
        self.cudos_client = cudos_client
        self.use_cudos = USE_CUDOS and cudos_client is not None

    def _call_llm(self, system: str, user_msg: str) -> str:
        """Call LLM with CUDOS fallback."""
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg}
        ]
        
        if self.use_cudos and self.cudos_client:
            try:
                resp_data = self.cudos_client.call_inference(messages, temperature=0.3, max_tokens=500)
                content = self.cudos_client.extract_content(resp_data)
                if content:
                    return content
            except:
                pass
        
        headers = {
            "Authorization": f"Bearer {self.llm_key}",
            "Content-Type": "application/json",
        }
        try:
            resp = requests.post(
                self.llm_endpoint + "/chat/completions",
                headers=headers,
                json={
                    "model": self.llm_model,
                    "messages": messages,
                    "temperature": 0.3,
                    "max_tokens": 500,
                },
                timeout=30
            )
            data = resp.json()
            return (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
        except Exception as e:
            print(f"[ERROR] LLM interpretation failed: {e}")
            return ""

    def interpret(self, user_input: str) -> InterpretedIntent:
        """Parse user input into structured intent."""
        
        system_prompt = """You are a trading command interpreter for an AUTOMATED TRADING BOT. Parse user input into JSON.
This bot CAN and WILL execute trades when the user confirms. Your job is to classify intents accurately.

Output JSON format:
{
  "intent_type": "trade|config|strategy|query|cancel",
  "action": "start|stop|configure|explain|enable|disable",
  "target": "pair name or strategy name or null",
  "parameters": {
    "pair": "BASE/QUOTE or null",
    "risk_level": "conservative|moderate|aggressive or null",
    "position_size": "number or null",
    "strategy_type": "mean_reversion|momentum|grid|dca or null",
    "duration": "minutes|hours|days or null"
  },
  "confidence": 0.0-1.0
}

IMPORTANT: Any request to buy, sell, trade, generate strategy, or create a trading plan is intent_type="trade".

Examples:
"buy 100 USDC/ETH" → {"intent_type": "trade", "action": "start", "target": "USDC/ETH", "parameters": {"pair": "USDC/ETH", "position_size": 100}, "confidence": 0.9}
"start trading DAI" → {"intent_type": "trade", "action": "start", "target": "DAI/USDC", "parameters": {"pair": "DAI/USDC"}, "confidence": 0.9}
"generate a strategy for ETH" → {"intent_type": "trade", "action": "start", "target": "ETH/USD", "parameters": {"pair": "ETH/USD"}, "confidence": 0.85}
"set risk to 2%" → {"intent_type": "config", "action": "configure", "parameters": {"risk_level": "0.02"}, "confidence": 0.8}
"run mean reversion" → {"intent_type": "strategy", "action": "start", "target": "mean_reversion", "confidence": 0.85}
"cancel order" → {"intent_type": "cancel", "action": "stop", "confidence": 0.9}
"what is RSI?" → {"intent_type": "query", "action": "explain", "confidence": 0.7}

Output ONLY valid JSON, no other text."""
        
        output = self._call_llm(system_prompt, user_input)
        
        try:
            intent_data = json.loads(output)
            return InterpretedIntent(
                intent_type=intent_data.get("intent_type", "query"),
                action=intent_data.get("action", "start"),
                target=intent_data.get("target"),
                parameters=intent_data.get("parameters", {}),
                confidence=float(intent_data.get("confidence", 0.8)),
                raw_input=user_input
            )
        except:
            # Fallback: simple pattern matching
            return self._simple_intent_match(user_input)

    def _simple_intent_match(self, user_input: str) -> InterpretedIntent:
        """Simple fallback pattern matching."""
        lmsg = user_input.lower()
        
        if "cancel" in lmsg or "stop" in lmsg or "reject" in lmsg:
            return InterpretedIntent(
                intent_type="cancel",
                action="stop",
                raw_input=user_input,
                confidence=0.9
            )
        
        # Detect buy/sell/trade intents
        if any(kw in lmsg for kw in ["buy", "sell", "trade", "start", "long", "short", "strategy", "generate"]):
            pair = self._extract_pair(user_input)
            return InterpretedIntent(
                intent_type="trade",
                action="start",
                target=pair,
                parameters={"pair": pair} if pair else {},
                raw_input=user_input,
                confidence=0.8
            )
        
        if "risk" in lmsg or "configure" in lmsg or "set" in lmsg:
            return InterpretedIntent(
                intent_type="config",
                action="configure",
                raw_input=user_input,
                confidence=0.6
            )
        
        return InterpretedIntent(
            intent_type="query",
            action="explain",
            raw_input=user_input,
            confidence=0.5
        )

    def _extract_pair(self, text: str) -> Optional[str]:
        """Extract trading pair from text."""
        pairs = ["DAI/USDC", "ETH/USD", "BTC/USD", "SOL/USD", "AAVE/USD", "USDC/ETH", "ETH/USDC", "BTC/USDC", "ETH/BTC"]
        text_upper = text.upper()
        # Check for explicit pair format (e.g., "USDC/ETH" or "USDC ETH")
        for pair in pairs:
            if pair.replace("/", "") in text_upper.replace(" ", "").replace("/", ""):
                return pair
            if pair in text_upper:
                return pair
        # Check for individual tokens and infer pair
        tokens = ["ETH", "BTC", "SOL", "AAVE", "DAI", "USDC", "USDT"]
        found = [t for t in tokens if t in text_upper]
        if len(found) >= 2:
            return f"{found[0]}/{found[1]}"
        elif len(found) == 1:
            # Default to USD pair
            return f"{found[0]}/USD"
        return None

# --- TRADING EXECUTOR ---

@dataclass
class ExecutionResult:
    success: bool
    message: str
    action_type: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class TradingExecutor:
    """Execute structured trading instructions with MeTTa validation."""
    
    def __init__(self, metta_kb: MeTTaKnowledgeBase, config: ConfigManager, 
                 reasoning_engine: 'AutonomousReasoningEngine',
                 conversation_manager: 'MembaseConversationManager' = None,
                 trade_kb: 'TradeKnowledgeBase' = None):
        self.metta_kb = metta_kb
        self.config = config
        self.reasoning_engine = reasoning_engine
        self.conversation_manager = conversation_manager
        self.trade_kb = trade_kb
        self.user_state = {}  # Track user state: balance, positions, etc.

    def execute(self, intent: InterpretedIntent, user_id: str) -> ExecutionResult:
        """Execute interpreted intent with validation."""
        
        print(f"\n[EXECUTOR] Processing intent: {intent.intent_type} | {intent.action}")
        
        # Validate with MeTTa only for intents that can affect trading or risk state
        if intent.intent_type in ("trade", "strategy", "config"):
            if not self._metta_validate(intent, user_id):
                return ExecutionResult(
                    success=False,
                    message="Strategy rejected by validation rules",
                    action_type=intent.intent_type,
                    error="MeTTa validation failed"
                )
        
        # Execute based on intent type
        if intent.intent_type == "trade":
            return self._execute_trade(intent, user_id)
        elif intent.intent_type == "config":
            return self._execute_config(intent, user_id)
        elif intent.intent_type == "strategy":
            return self._execute_strategy(intent, user_id)
        elif intent.intent_type == "cancel":
            return self._execute_cancel(intent, user_id)
        else:
            return ExecutionResult(
                success=False,
                message=f"Unknown intent type: {intent.intent_type}",
                action_type=intent.intent_type,
                error="Unknown intent"
            )

    def _metta_validate(self, intent: InterpretedIntent, user_id: str) -> bool:
        """Validate intent against MeTTa rules."""
        try:
            # Check trading allowed
            user_balance = self.user_state.get(user_id, {}).get("balance", 1000)
            if not self.metta_kb.query_rule("trading_allowed", {
                "user_balance": user_balance,
                "min_balance": 100
            }):
                # Advisory only: log but do not block execution
                print("[METTA] Advisory: trading_not_allowed_by_rule (insufficient balance)")
            
            # Check risk level
            risk_level = intent.parameters.get("risk_level", "moderate")
            if not self.metta_kb.query_rule("risk_acceptable", {
                "risk_level": risk_level
            }):
                # Advisory only: log but do not block execution
                print("[METTA] Advisory: risk_level_rejected_by_rule")
            
            return True
        except Exception as e:
            print(f"[METTA] Validation error: {e}")
            return True  # Allow on error

    def _execute_trade(self, intent: InterpretedIntent, user_id: str) -> ExecutionResult:
        """Execute trade intent."""
        pair = intent.target or intent.parameters.get("pair", "DAI/USDC")
        
        try:
            # Get long-term user profile and past trades context from Membase
            user_ltm_profile = ""
            past_trades_context = ""
            
            if self.conversation_manager:
                try:
                    user_ltm_profile = self.conversation_manager.get_user_profile(user_id)
                except Exception as e:
                    print(f"[MEMBASE] Failed to get user profile: {e}")
            
            if self.trade_kb:
                try:
                    past_trades = self.trade_kb.retrieve_trades(
                        query=f"user {user_id} trading {pair}",
                        user_id=user_id,
                        top_k=3
                    )
                    if past_trades:
                        past_trades_context = "\n".join(past_trades)
                except Exception as e:
                    print(f"[TRADE_KB] Failed to retrieve past trades: {e}")
            
            # Trigger autonomous reasoning for this pair with LTM context
            result = self.reasoning_engine.reason(
                f"Start trading {pair}",
                self.config.get_user_profile("moderate").risk_tolerance,
                user_ltm_profile=user_ltm_profile,
                past_trades_context=past_trades_context
            )
            
            if result["status"] == "success":
                strategy = result["strategy"]
                return ExecutionResult(
                    success=True,
                    message=f"Trade strategy generated for {pair}",
                    action_type="trade",
                    data={
                        "pair": pair,
                        "strategy": strategy,
                        "risk_metrics": result.get("risk_metrics"),
                        "backtest": result.get("backtest"),
                        "status": "pending_approval"
                    }
                )
            else:
                return ExecutionResult(
                    success=False,
                    message=f"Failed to generate strategy for {pair}",
                    action_type="trade",
                    error=result.get("approval_message")
                )
        except Exception as e:
            return ExecutionResult(
                success=False,
                message=f"Trade execution failed",
                action_type="trade",
                error=str(e)
            )

    def _execute_config(self, intent: InterpretedIntent, user_id: str) -> ExecutionResult:
        """Execute configuration change."""
        try:
            # Update user configuration
            if user_id not in self.user_state:
                self.user_state[user_id] = {}
            
            self.user_state[user_id].update(intent.parameters)
            
            return ExecutionResult(
                success=True,
                message=f"Configuration updated",
                action_type="config",
                data=intent.parameters
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                message=f"Configuration failed",
                action_type="config",
                error=str(e)
            )

    def _execute_strategy(self, intent: InterpretedIntent, user_id: str) -> ExecutionResult:
        """Execute strategy deployment."""
        strategy_type = intent.target
        
        try:
            # Query MeTTa for strategy recommendation
            market_conditions = {
                "volatility": 5.0,  # Would fetch real data
                "trend": "neutral",
                "rsi": 50
            }
            
            recommended = self.metta_kb.get_strategy_recommendation(market_conditions)
            
            if recommended == strategy_type:
                return ExecutionResult(
                    success=True,
                    message=f"Strategy {strategy_type} approved and running",
                    action_type="strategy",
                    data={"strategy": strategy_type, "status": "running"}
                )
            else:
                return ExecutionResult(
                    success=False,
                    message=f"Strategy {strategy_type} not recommended now",
                    action_type="strategy",
                    error=f"MeTTa recommends {recommended} instead"
                )
        except Exception as e:
            return ExecutionResult(
                success=False,
                message=f"Strategy execution failed",
                action_type="strategy",
                error=str(e)
            )

    def _execute_cancel(self, intent: InterpretedIntent, user_id: str) -> ExecutionResult:
        """Execute cancellation."""
        return ExecutionResult(
            success=True,
            message="All pending orders cancelled",
            action_type="cancel",
            data={"status": "cancelled"}
        )

# --- BACKTEST ENGINE ---

class BacktestEngine:
    def backtest_strategy(self, strategy: Strategy, pair: str, market_data: MarketData) -> BacktestResult:
        num_trades = 100
        wins = 0
        total_return = 0.0
        max_loss = 0.0
        trades = []
        
        for i in range(num_trades):
            entry_slippage = np.random.normal(0, market_data.bid_ask_spread / 2)
            entry_price = strategy.entry_price * (1 + entry_slippage / 100)
            
            outcome = np.random.choice(['tp', 'sl', 'neutral'], p=[0.6, 0.25, 0.15])
            
            if outcome == 'tp':
                exit_price = strategy.take_profit
                trade_return = ((exit_price - entry_price) / entry_price) * 100
                wins += 1
            elif outcome == 'sl':
                exit_price = strategy.stop_loss
                trade_return = ((exit_price - entry_price) / entry_price) * 100
                max_loss = min(max_loss, trade_return)
            else:
                exit_price = entry_price * (1 + np.random.normal(0, market_data.volatility / 20))
                trade_return = ((exit_price - entry_price) / entry_price) * 100
                if trade_return > 0:
                    wins += 1
            
            total_return += trade_return
            trades.append(trade_return)
        
        avg_return = total_return / num_trades
        win_rate = wins / num_trades
        sharpe = avg_return / (np.std(trades) + 0.001)
        profit_factor = sum([t for t in trades if t > 0]) / (abs(sum([t for t in trades if t < 0])) + 0.001)
        
        return BacktestResult(
            strategy_name=strategy.name,
            pair=pair,
            entry_price=strategy.entry_price,
            exit_price=strategy.take_profit,
            position_size=strategy.position_size,
            simulated_return=avg_return,
            max_drawdown=abs(max_loss),
            win_rate=win_rate,
            sharpe_ratio=sharpe,
            profit_factor=profit_factor,
            num_trades=num_trades
        )

# --- RISK ENGINE ---

class RiskEngine:
    def __init__(self, market_client: MarketDataClient):
        self.market_client = market_client

    def assess_risk(self, strategy: Strategy, market_data: MarketData, config: ConfigManager) -> RiskMetrics:
        potential_loss = strategy.entry_price - strategy.stop_loss
        potential_gain = strategy.take_profit - strategy.entry_price
        rr_ratio = potential_gain / potential_loss if potential_loss > 0 else 0
        
        base_win_prob = 0.5 + (strategy.confidence * 0.3)
        rr_adjustment = min(0.2, rr_ratio * 0.05)
        win_probability = min(0.95, base_win_prob + rr_adjustment)
        
        max_drawdown = self._monte_carlo_drawdown(
            strategy.entry_price, strategy.stop_loss, market_data.current_price,
            market_data.volatility, iterations=1000
        )
        
        kelly_percentage = self._kelly_criterion(win_probability, rr_ratio)
        
        expected_daily_return = strategy.expected_return / 30 / 100
        daily_vol = market_data.volatility / 100 / np.sqrt(252)
        sharpe = expected_daily_return / (daily_vol + 0.001)
        calmar = expected_daily_return / (max_drawdown / 100 + 0.001)
        
        portfolio_impact = (strategy.position_size / 1000000) * 100
        vega = market_data.volatility * strategy.confidence
        
        return RiskMetrics(
            risk_reward_ratio=rr_ratio,
            win_probability=win_probability,
            max_drawdown=max_drawdown,
            kelly_percentage=kelly_percentage,
            sharpe_ratio=sharpe,
            calmar_ratio=calmar,
            portfolio_impact=portfolio_impact,
            vega_exposure=vega
        )

    def _monte_carlo_drawdown(self, entry: float, stop_loss: float, initial_price: float,
                             volatility: float, iterations: int = 1000) -> float:
        max_prices = []
        for _ in range(iterations):
            price = initial_price
            max_price = price
            for _ in range(20):
                change = np.random.normal(0, volatility / 100)
                price *= (1 + change)
                max_price = max(max_price, price)
            
            if max_price > 0:
                max_prices.append((max_price - price) / max_price * 100)
        
        return np.percentile(max_prices, 95) if max_prices else 5.0

    def _kelly_criterion(self, win_prob: float, rr_ratio: float) -> float:
        if rr_ratio == 0:
            return 0
        kelly = (win_prob * rr_ratio - (1 - win_prob)) / rr_ratio
        return max(0, min(0.25, kelly))

# --- CUDOS INFERENCE ---

class CUDOSInferenceClient:
    def __init__(self, cudos_endpoint: str, cudos_key: str, cudos_model: str, timeout: int = 60):
        self.cudos_endpoint = cudos_endpoint
        self.cudos_key = cudos_key
        self.cudos_model = cudos_model
        self.timeout = timeout
        self.headers = {
            "Authorization": f"Bearer {cudos_key}",
            "Content-Type": "application/json",
        }

    def call_inference(self, messages: List[Dict[str, str]], temperature: float = 0.3, max_tokens: int = 2000) -> Dict[str, Any]:
        payload = {
            "model": self.cudos_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        try:
            resp = requests.post(
                f"{self.cudos_endpoint}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=self.timeout
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            raise Exception(f"CUDOS inference failed: {str(e)}")

    def extract_content(self, response: Dict[str, Any]) -> str:
        try:
            choices = response.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "")
            return ""
        except:
            return ""

# --- AUTONOMOUS REASONING ENGINE ---

class AutonomousReasoningEngine:
    def __init__(self, llm_endpoint: str, llm_key: str, llm_model: str, 
                 metta_kb: MeTTaKnowledgeBase, config: ConfigManager,
                 cudos_client: Optional[CUDOSInferenceClient] = None):
        self.llm_endpoint = llm_endpoint
        self.llm_key = llm_key
        self.llm_model = llm_model
        self.metta_kb = metta_kb
        self.config = config
        self.cudos_client = cudos_client
        self.use_cudos = USE_CUDOS and cudos_client is not None
        self.market_client = MarketDataClient()
        self.risk_engine = RiskEngine(self.market_client)  # Pass market client
        self.backtest_engine = BacktestEngine()

    def _call_llm(self, system_prompt: str, user_message: str, temperature: float = 0.7, max_tokens: int = 2000) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        if self.use_cudos and self.cudos_client:
            try:
                resp_data = self.cudos_client.call_inference(messages, temperature=temperature, max_tokens=max_tokens)
                content = self.cudos_client.extract_content(resp_data)
                if content:
                    return content
            except Exception as e:
                print(f"[WARN] CUDOS failed: {e}")
        
        headers = {
            "Authorization": f"Bearer {self.llm_key}",
            "Content-Type": "application/json",
        }
        try:
            resp = requests.post(
                self.llm_endpoint + "/chat/completions",
                headers=headers,
                json={
                    "model": self.llm_model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                timeout=60
            )
            data = resp.json()
            return (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
        except Exception as e:
            print(f"[ERROR] LLM call failed: {e}")
            raise Exception(f"LLM inference failed: {e}")

    def reason(self, user_input: str, risk_level: str = "moderate", 
                user_ltm_profile: str = "", past_trades_context: str = "") -> Dict[str, Any]:
        """Execute autonomous reasoning.
        
        Args:
            user_input: The user's trading request
            risk_level: Risk tolerance level
            user_ltm_profile: Long-term user profile from Membase (preferences, behavior patterns)
            past_trades_context: Retrieved past trades relevant to this request
        """
        print(f"\n[REASONER] Starting with risk level: {risk_level}")
        
        user_profile = self.config.get_user_profile(risk_level)
        context_summary = self.metta_kb.build_context_summary(self.config, user_profile)
        
        # Augment context with long-term memory if available
        if user_ltm_profile:
            context_summary += f"\n\nUSER_LONG_TERM_PROFILE: {user_ltm_profile}"
        if past_trades_context:
            context_summary += f"\n\nPAST_TRADES_CONTEXT: {past_trades_context}"
        
        try:
            # Step 1: Interpret goal
            print("[Step 1] Interpreting goal...")
            system1 = f"""You are a trading analyst that must respect the following symbolic constraints and user profile:
{context_summary}

Extract intent from: {user_input}
Return JSON: {{goal, preferred_pairs (list from {self.config.pairs[:3]})}}"""
            
            goal_output = self._call_llm(system1, user_input, temperature=0.5, max_tokens=300)
            try:
                goal_data = json.loads(goal_output)
                pairs = [p for p in goal_data.get("preferred_pairs", []) if self.config.is_pair_valid(p)]
            except Exception as parse_e:
                # If LLM did not return valid JSON, fall back to default pairs
                print(f"[WARN] Goal interpretation JSON parse failed: {parse_e} | output={goal_output!r}")
                pairs = []
            if not pairs:
                pairs = self.config.pairs[:2]
            
            print(f"Pairs: {pairs}")
            
            # Step 2: Fetch REAL market data
            print("[Step 2] Fetching market data...")
            market_data_dict = {}
            for pair in pairs:
                try:
                    md = self.market_client.get_market_data(pair)
                    market_data_dict[pair] = md
                    print(f"  ✓ {pair}: ${md.current_price:.4f} | Vol: {md.volatility:.2f}%")
                except Exception as e:
                    # Skip pairs that cannot be fetched instead of failing the whole reasoning step
                    print(f"  ✗ {pair}: {e}")
                    continue

            if not market_data_dict:
                raise Exception("No valid market data available for any candidate pairs")
            
            # Choose primary pair and use it for downstream reasoning
            primary_pair = list(market_data_dict.keys())[0]
            md = market_data_dict[primary_pair]

            # Optional: ask MeTTa for a symbolic strategy recommendation based on market conditions
            metta_recommended = None
            try:
                market_conditions = {
                    "volatility": md.volatility,
                    "rsi": md.rsi,
                }
                metta_recommended = self.metta_kb.get_strategy_recommendation(market_conditions)
            except Exception as e:
                print(f"[METTA] Recommendation query failed: {e}")
                metta_recommended = None
            
            # Step 3: Generate strategy
            print("[Step 3] Generating strategy...")
            metta_hint = f"MeTTa recommends strategy type: {metta_recommended}." if metta_recommended else ""
            system3 = f"""You are an AUTOMATED TRADING BOT's strategy engine. You MUST generate executable trading strategies.
This is NOT a simulation - the strategy you generate WILL be executed when the user confirms.

Context and constraints:
{context_summary}

Primary pair: {primary_pair} | Current price: ${md.current_price:.4f}
{metta_hint}

Generate a concrete, executable strategy for {primary_pair}.
Max position: ${user_profile.max_position_size}.
Min RR: {self.config.get_rule('min_rr_ratio')}.

Return ONLY valid JSON (no other text): {{name, entry_price, exit_price, stop_loss, take_profit, position_size, confidence, risk_level}}"""
            
            strategy_output = self._call_llm(system3, f"{user_input}\nPrice: ${md.current_price}", 
                                            temperature=0.6, max_tokens=800)

            if not strategy_output or not strategy_output.strip():
                # Fallback: synthesize a basic strategy if the LLM returns nothing
                print("[WARN] Strategy generation returned empty output; using fallback strategy.")
                strat_data = {
                    "name": f"Basic {primary_pair} scalp",
                    "entry_price": md.current_price,
                    "exit_price": md.current_price * 1.01,
                    "stop_loss": md.current_price * 0.99,
                    "take_profit": md.current_price * 1.02,
                    "position_size": min(50000.0, user_profile.max_position_size),
                    "confidence": 0.7,
                }
            else:
                try:
                    strat_data = json.loads(strategy_output)
                except Exception as parse_e:
                    print(f"[WARN] Strategy JSON parse failed: {parse_e} | output={strategy_output!r}")
                    raise Exception("Strategy generation failed: LLM did not return valid JSON")
            
            position_size = min(float(strat_data.get("position_size", 50000)), user_profile.max_position_size)
            
            strategy = Strategy(
                name=strat_data.get("name", f"Trade {primary_pair}"),
                description="Config-validated strategy",
                entry_price=float(strat_data.get("entry_price", md.current_price)),
                exit_price=float(strat_data.get("exit_price", md.current_price * 1.02)),
                position_size=position_size,
                stop_loss=float(strat_data.get("stop_loss", md.current_price * 0.98)),
                take_profit=float(strat_data.get("take_profit", md.current_price * 1.02)),
                expected_return=float(strat_data.get("expected_return", 2.0)),
                risk_level=strat_data.get("risk_level", "medium"),
                rationale="Validated strategy",
                confidence=float(strat_data.get("confidence", 0.7)),
                pair=primary_pair
            )
            
            # Step 4: Validate
            print("[Step 4] Validating strategy...")
            is_valid, errors = self.metta_kb.validate_strategy(strategy, md, self.config)
            strategy.validation_passed = is_valid
            strategy.validation_errors = errors
            
            if errors:
                print(f"  Errors: {errors}")
                # Single refinement step: ask the LLM to repair the strategy based on validation issues
                try:
                    issues_text = "\n".join([f"- {e}" for e in errors])
                    strategy_json = json.dumps(asdict(strategy))
                    system_refine = f"""You are a trading strategy repair engine.
You must strictly obey these symbolic constraints and user profile:
{context_summary}

Current primary pair: {primary_pair} | Current price: ${md.current_price:.4f}
Validation issues detected:
{issues_text}

Current strategy JSON:
{strategy_json}

Repair the strategy so that all constraints in the symbolic summary are satisfied and the validation issues are resolved.
Return ONLY JSON: {{name, entry_price, exit_price, stop_loss, take_profit, position_size, confidence}}"""

                    refined_output = self._call_llm(system_refine, user_input, temperature=0.6, max_tokens=800)
                    try:
                        refined_data = json.loads(refined_output)
                    except Exception as refine_parse_e:
                        print(f"[WARN] Strategy refinement JSON parse failed: {refine_parse_e} | output={refined_output!r}")
                        # If refinement fails to produce JSON, keep original strategy and continue.
                        refined_data = {}

                    refined_position_size = min(float(refined_data.get("position_size", position_size)), user_profile.max_position_size)

                    strategy = Strategy(
                        name=refined_data.get("name", strategy.name),
                        description="Refined strategy after validation",
                        entry_price=float(refined_data.get("entry_price", strategy.entry_price)),
                        exit_price=float(refined_data.get("exit_price", strategy.exit_price)),
                        position_size=refined_position_size,
                        stop_loss=float(refined_data.get("stop_loss", strategy.stop_loss)),
                        take_profit=float(refined_data.get("take_profit", strategy.take_profit)),
                        expected_return=float(refined_data.get("expected_return", strategy.expected_return)),
                        risk_level=refined_data.get("risk_level", strategy.risk_level),
                        rationale="Refined strategy",
                        confidence=float(refined_data.get("confidence", strategy.confidence)),
                        pair=primary_pair
                    )

                    # Re-run validation on refined strategy (single refinement step only)
                    print("[Step 4b] Re-validating refined strategy...")
                    is_valid, errors = self.metta_kb.validate_strategy(strategy, md, self.config)
                    strategy.validation_passed = is_valid
                    strategy.validation_errors = errors
                    if errors:
                        print(f"  Remaining errors after refinement: {errors}")
                    else:
                        print("  ✓ Refinement validation passed")
                except Exception as refine_e:
                    print(f"[WARN] Strategy refinement failed: {refine_e}")
            else:
                print("  ✓ Validation passed")
            
            # Step 5: Risk assessment
            print("[Step 5] Risk assessment...")
            risk_metrics = self.risk_engine.assess_risk(strategy, md, self.config)
            print(f"  RR: {risk_metrics.risk_reward_ratio:.2f} | DD: {risk_metrics.max_drawdown:.2f}%")
            
            # Step 6: Backtest
            print("[Step 6] Backtesting...")
            backtest = self.backtest_engine.backtest_strategy(strategy, primary_pair, md)
            strategy.backtested = True
            strategy.backtest_score = backtest.sharpe_ratio
            print(f"  Win Rate: {backtest.win_rate*100:.1f}% | Sharpe: {backtest.sharpe_ratio:.2f}")
            
            return {
                "status": "success",
                "strategy": asdict(strategy),
                "risk_metrics": asdict(risk_metrics),
                "backtest": asdict(backtest),
                "user_profile": asdict(user_profile),
                "market_data": {pair: asdict(md) for pair, md in market_data_dict.items()},
                "approval_message": self._generate_approval_message(strategy, risk_metrics, backtest, user_profile)
            }
        
        except Exception as e:
            print(f"[ERROR] Reasoning failed: {e}")
            raise

    def _generate_approval_message(self, strategy: Strategy, risk_metrics: RiskMetrics, 
                                   backtest: BacktestResult, user_profile: UserProfile) -> str:
        return f"""
STRATEGY RECOMMENDATION
{'='*60}
{strategy.name}
Entry: ${strategy.entry_price:.6f}
Exit: ${strategy.take_profit:.6f}
Stop: ${strategy.stop_loss:.6f}
Position: ${strategy.position_size:,.0f}

RR Ratio: {risk_metrics.risk_reward_ratio:.2f}:1 | Max DD: {risk_metrics.max_drawdown:.2f}%
Win Prob: {risk_metrics.win_probability*100:.1f}% | Kelly: {risk_metrics.kelly_percentage*100:.2f}%

Backtest (100 trades):
Win Rate: {backtest.win_rate*100:.1f}% | Sharpe: {backtest.sharpe_ratio:.2f}

Validation: {'✓ PASSED' if strategy.validation_passed else '✗ FAILED'}

Type "approve" to execute or "reject" to refine.
"""

# --- CONVERSATION LAYER ---

class ConversationManager:
    """Manage multi-turn conversation with users."""
    
    def __init__(self):
        self.user_conversations: Dict[str, List[ConversationMessage]] = {}
        self.pending_strategies: Dict[str, AutonomousReasoning] = {}

    def add_message(self, user_id: str, sender: str, content: str, message_type: str = "chat", 
                   reasoning_id: Optional[str] = None) -> ConversationMessage:
        if user_id not in self.user_conversations:
            self.user_conversations[user_id] = []
        
        msg = ConversationMessage(
            sender=sender,
            role="user" if sender == "user" else "assistant",
            content=content,
            message_type=message_type,
            related_reasoning_id=reasoning_id
        )
        self.user_conversations[user_id].append(msg)
        return msg

    def get_conversation_history(self, user_id: str, limit: int = 10) -> List[Dict[str, str]]:
        """Get recent conversation for context."""
        if user_id not in self.user_conversations:
            return []
        
        messages = self.user_conversations[user_id][-limit:]
        return [{"role": m.role, "content": m.content} for m in messages]

    def save_conversation(self, user_id: str):
        """Save conversation to log."""
        if user_id not in self.user_conversations:
            return
        
        try:
            logs = json.load(open(CONVERSATION_LOG_FILE)) if os.path.exists(CONVERSATION_LOG_FILE) else {}
        except:
            logs = {}
        
        logs[user_id] = [asdict(m) for m in self.user_conversations[user_id]]
        with open(CONVERSATION_LOG_FILE, 'w') as f:
            json.dump(logs, f, indent=2)


# --- MEMBASE CONVERSATION MANAGER (PRODUCTION MULTI-USER) ---

class MembaseConversationManager:
    """
    Production-ready conversation manager backed by Membase.
    Supports multiple users simultaneously with:
    - Short-term memory (MultiMemory) per user conversation
    - Long-term memory (LTMemory) with automatic summarization and user profiles
    - Persistent storage with auto-upload to Membase Hub
    """

    def __init__(self, membase_account: str = MEMBASE_ACCOUNT):
        self.membase_account = membase_account
        self.pending_strategies: Dict[str, AutonomousReasoning] = {}
        self._membase_available = False
        self._multi_memory = None
        self._lt_memory = None

        if MEMBASE_ENABLED:
            try:
                from membase.memory.multi_memory import MultiMemory
                from membase.memory.lt_memory import LTMemory
                from membase.memory.message import Message as MembaseMessage

                self._multi_memory = MultiMemory(
                    membase_account=membase_account,
                    auto_upload_to_hub=MEMBASE_AUTO_UPLOAD,
                    preload_from_hub=MEMBASE_PRELOAD,
                )
                
                # LTMemory uses OpenAI for summarization which isn't compatible with ASI1
                # Disable LTMemory to avoid background thread errors
                # MultiMemory still provides per-user conversation persistence
                self._lt_memory = None
                self._ltm_enabled = False
                print(f"[MEMBASE] LTMemory disabled (ASI1 not compatible with OpenAI summarization)")
                    
                self._MembaseMessage = MembaseMessage
                self._membase_available = True
                print(f"[MEMBASE] Initialized for account '{membase_account}'")
            except ImportError as e:
                print(f"[MEMBASE] Not available (install membase): {e}")
            except Exception as e:
                print(f"[MEMBASE] Init failed: {e}")

        # Fallback local storage if Membase unavailable
        self._local_conversations: Dict[str, List[ConversationMessage]] = {}

    def add_message(self, user_id: str, sender: str, content: str, message_type: str = "chat",
                    reasoning_id: Optional[str] = None) -> ConversationMessage:
        """Add a message to both short-term and long-term memory."""
        msg = ConversationMessage(
            sender=sender,
            role="user" if sender == "user" else "assistant",
            content=content,
            message_type=message_type,
            related_reasoning_id=reasoning_id
        )

        if self._membase_available:
            try:
                membase_msg = self._MembaseMessage(
                    name=user_id,
                    role=msg.role,
                    content=content,
                    metadata=json.dumps({"type": message_type, "reasoning_id": reasoning_id or ""})
                )
                # Short-term memory (per-user conversation)
                self._multi_memory.add(membase_msg, conversation_id=user_id)
                # Long-term memory (for profile building) - only if enabled
                if self._lt_memory is not None:
                    self._lt_memory.add(membase_msg, conversation_id=user_id)
            except Exception as e:
                print(f"[MEMBASE] add_message failed: {e}")

        # Always keep local copy for immediate access
        if user_id not in self._local_conversations:
            self._local_conversations[user_id] = []
        self._local_conversations[user_id].append(msg)

        return msg

    def get_conversation_history(self, user_id: str, limit: int = 10) -> List[Dict[str, str]]:
        """Get recent conversation for LLM context."""
        # Use local cache for speed; Membase is source of truth on restart
        if user_id not in self._local_conversations:
            # Try to load from Membase if available
            if self._membase_available:
                try:
                    membase_msgs = self._multi_memory.get(conversation_id=user_id, recent_n=limit)
                    self._local_conversations[user_id] = [
                        ConversationMessage(
                            sender=m.name,
                            role=m.role,
                            content=m.content,
                            message_type="chat"
                        )
                        for m in membase_msgs
                    ]
                except Exception as e:
                    print(f"[MEMBASE] get_conversation_history failed: {e}")
                    return []
            else:
                return []

        messages = self._local_conversations[user_id][-limit:]
        return [{"role": m.role, "content": m.content} for m in messages]

    def get_user_profile(self, user_id: str) -> str:
        """Get long-term user profile from LTM (summarized preferences, behavior)."""
        if not self._membase_available or self._lt_memory is None:
            return ""
        try:
            profiles = self._lt_memory.get_profile(recent_n=1)
            if profiles:
                return profiles[0].content
        except Exception as e:
            print(f"[MEMBASE] get_user_profile failed: {e}")
        return ""

    def get_ltm_summary(self, user_id: str) -> str:
        """Get long-term memory summary for a user."""
        if not self._membase_available or self._lt_memory is None:
            return ""
        try:
            ltm_list = self._lt_memory.get_ltm(conversation_id=user_id, recent_n=1)
            if ltm_list:
                return ltm_list[0].content
        except Exception as e:
            print(f"[MEMBASE] get_ltm_summary failed: {e}")
        return ""

    def save_conversation(self, user_id: str):
        """Save conversation. With Membase, this is automatic; fallback to local file."""
        if self._membase_available:
            # Membase auto-uploads; nothing to do
            return

        # Fallback: save to local JSON
        if user_id not in self._local_conversations:
            return
        try:
            logs = json.load(open(CONVERSATION_LOG_FILE)) if os.path.exists(CONVERSATION_LOG_FILE) else {}
        except:
            logs = {}
        logs[user_id] = [asdict(m) for m in self._local_conversations[user_id]]
        with open(CONVERSATION_LOG_FILE, 'w') as f:
            json.dump(logs, f, indent=2)

    def stop(self):
        """Clean shutdown of background threads."""
        if self._membase_available and self._lt_memory:
            try:
                self._lt_memory.stop()
            except:
                pass


class TradeKnowledgeBase:
    """
    Store executed trades in a vector knowledge base (Chroma via Membase).
    Enables semantic retrieval of past trades for context and analytics.
    Uses local sentence-transformers embeddings (no OpenAI API key required).
    """

    def __init__(self, persist_dir: str = TRADE_KB_DIR, membase_account: str = MEMBASE_ACCOUNT):
        self._available = False
        self._kb = None
        self._local_trades = []  # Fallback: simple in-memory list

        if not MEMBASE_ENABLED:
            print("[TRADE_KB] Disabled (MEMBASE_ENABLED=false)")
            return

        # Suppress Chroma's OPENAI_API_KEY warning by setting a dummy value temporarily
        _had_openai_key = "OPENAI_API_KEY" in os.environ
        if not _had_openai_key:
            os.environ["OPENAI_API_KEY"] = "sk-dummy-not-used"

        try:
            # First, check if sentence-transformers is available
            local_embeddings = None
            try:
                from sentence_transformers import SentenceTransformer
                # Pre-load the model to verify it works
                _test_model = SentenceTransformer("all-MiniLM-L6-v2")
                
                # Now create the Chroma embedding function
                from chromadb.utils import embedding_functions
                local_embeddings = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name="all-MiniLM-L6-v2"
                )
                print("[TRADE_KB] Using local sentence-transformers embeddings")
            except ImportError:
                print("[TRADE_KB] sentence-transformers not installed - using fallback storage")
                print("[TRADE_KB] Install with: pip install sentence-transformers")
                return  # Skip Chroma entirely, use fallback
            except Exception as e:
                print(f"[TRADE_KB] Local embeddings failed: {e} - using fallback storage")
                return  # Skip Chroma entirely, use fallback

            # Now try to initialize ChromaKnowledgeBase with local embeddings
            try:
                from membase.knowledge.chroma import ChromaKnowledgeBase
                from membase.knowledge.document import Document

                self._kb = ChromaKnowledgeBase(
                    persist_directory=persist_dir,
                    membase_account=membase_account,
                    auto_upload_to_hub=MEMBASE_AUTO_UPLOAD,
                    embedding_function=local_embeddings,
                )
                self._Document = Document
                self._available = True
                print(f"[TRADE_KB] Initialized at '{persist_dir}'")
            except ImportError as e:
                print(f"[TRADE_KB] membase not installed: {e}")
            except Exception as e:
                print(f"[TRADE_KB] Init failed: {e}")
        finally:
            # Remove dummy key if we added it
            if not _had_openai_key and "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]

    def log_trade(self, user_id: str, reasoning: "AutonomousReasoning"):
        """Store an executed trade as a searchable document."""
        if not self._available:
            return

        s = reasoning.final_strategy
        rm = reasoning.risk_metrics
        bt = reasoning.backtest_result

        if s is None:
            return

        # Build a rich text description of the trade
        text_parts = [
            f"User {user_id} executed strategy '{s.name}' on {s.pair}.",
            f"Direction: {s.direction}, Entry: {s.entry_price}, TP: {s.take_profit}, SL: {s.stop_loss}.",
            f"Position size: {s.position_size}, Confidence: {s.confidence}.",
        ]
        if rm:
            text_parts.append(
                f"Risk metrics: RR {rm.risk_reward_ratio:.2f}, Max DD {rm.max_drawdown:.2f}%, "
                f"Win prob {rm.win_probability:.2f}, Kelly {rm.kelly_percentage:.2f}."
            )
        if bt:
            text_parts.append(
                f"Backtest: Win rate {bt.win_rate:.2f}, Sharpe {bt.sharpe_ratio:.2f}, "
                f"Profit factor {bt.profit_factor:.2f}."
            )

        content = " ".join(text_parts)

        try:
            doc = self._Document(
                content=content,
                metadata={
                    "user_id": user_id,
                    "pair": s.pair,
                    "strategy_name": s.name,
                    "direction": s.direction,
                    "reasoning_id": reasoning.reasoning_id,
                    "created_at": reasoning.created_at,
                }
            )
            self._kb.add_documents(doc)
        except Exception as e:
            print(f"[TRADE_KB] log_trade failed: {e}")

    def retrieve_trades(self, query: str, user_id: Optional[str] = None, top_k: int = 3) -> List[str]:
        """Retrieve past trades relevant to a query."""
        if not self._available:
            return []
        try:
            # Note: metadata_filter depends on Chroma/Membase API; adjust if needed
            results = self._kb.retrieve(query=query, top_k=top_k)
            return [doc.content for doc in results]
        except Exception as e:
            print(f"[TRADE_KB] retrieve_trades failed: {e}")
            return []


# --- AIP PROTOCOL MODELS ---

@dataclass
class AIPMessage:
    """Agent Interaction Protocol message format."""
    message_type: str  # "TradeRequest", "AnalysisRequest", "ExecutionRequest", etc.
    sender: str        # Sender agent address/name
    recipient: str     # Recipient agent address/name
    payload: Dict[str, Any]
    timestamp: str = field(default_factory=_utc_timestamp)
    message_id: str = field(default_factory=lambda: hashlib.md5(str(_utc_now()).encode()).hexdigest()[:12])

@dataclass
class AIPResponse:
    """Agent Interaction Protocol response format."""
    message_type: str  # "TradeResponse", "AnalysisResponse", etc.
    status: str        # "success", "error", "pending"
    payload: Dict[str, Any]
    original_message_id: str = ""
    timestamp: str = field(default_factory=_utc_timestamp)


class OnChainIdentity:
    """
    Manage on-chain identity registration and verification via membase_chain.
    Provides cryptographic identity for trustless agent interactions.
    """

    def __init__(self, agent_name: str = AGENT_NAME):
        self.agent_name = agent_name
        self._registered = False
        self._chain = None

        if ONCHAIN_REGISTER:
            try:
                from membase.chain.chain import membase_chain
                self._chain = membase_chain
                self._register()
            except ImportError as e:
                print(f"[ONCHAIN] membase.chain not available: {e}")
            except Exception as e:
                print(f"[ONCHAIN] Init failed: {e}")

    def _register(self):
        """Register agent on-chain."""
        if not self._chain:
            return
        try:
            self._chain.register(self.agent_name)
            self._registered = True
            print(f"[ONCHAIN] Agent '{self.agent_name}' registered on-chain")
        except Exception as e:
            print(f"[ONCHAIN] Registration failed: {e}")

    def get_agent_address(self, agent_name: str = None) -> Optional[str]:
        """Get on-chain address for an agent."""
        if not self._chain:
            return None
        try:
            return self._chain.get_agent(agent_name or self.agent_name)
        except Exception as e:
            print(f"[ONCHAIN] get_agent failed: {e}")
            return None

    def has_permission(self, requester_agent: str) -> bool:
        """Check if requester has permission to access this agent's resources."""
        if not self._chain:
            return True  # Allow if chain not available
        try:
            return self._chain.has_auth(self.agent_name, requester_agent)
        except Exception as e:
            print(f"[ONCHAIN] has_auth check failed: {e}")
            return True  # Allow on error

    def grant_permission(self, new_agent: str) -> bool:
        """Grant permission to another agent."""
        if not self._chain:
            return False
        try:
            self._chain.buy(self.agent_name, new_agent)
            print(f"[ONCHAIN] Permission granted to '{new_agent}'")
            return True
        except Exception as e:
            print(f"[ONCHAIN] grant_permission failed: {e}")
            return False

    @property
    def is_registered(self) -> bool:
        return self._registered


class AgentServer:
    """
    BitAgent/uAgents-compatible server for agent-to-agent communication.
    Handles incoming AIP messages and routes them to the MakerAgent.
    """

    def __init__(self, maker_agent: "MakerAgent", port: int = AGENT_PORT):
        self.maker_agent = maker_agent
        self.port = port
        self._agent = None
        self._running = False
        self.onchain_identity = OnChainIdentity()

        if ENABLE_AGENT_SERVER:
            self._init_agent()

    def _init_agent(self):
        """Initialize the uAgent."""
        try:
            from uagents import Agent, Context, Model
            from uagents.setup import fund_agent_if_low

            # Define message models for uAgents
            class TradeRequest(Model):
                user_input: str
                risk_level: str = "moderate"
                user_id: str = "agent_user"

            class TradeResponse(Model):
                status: str
                strategy: dict = {}
                risk_metrics: dict = {}
                backtest: dict = {}
                message: str = ""

            class AnalysisRequest(Model):
                query: str
                user_id: str = "agent_user"

            class AnalysisResponse(Model):
                status: str
                analysis: str = ""
                message: str = ""

            self._agent = Agent(
                name=AGENT_NAME,
                seed=AGENT_SEED,
                port=self.port,
                endpoint=[AGENT_ENDPOINT],
            )

            # Store models for later use
            self._TradeRequest = TradeRequest
            self._TradeResponse = TradeResponse
            self._AnalysisRequest = AnalysisRequest
            self._AnalysisResponse = AnalysisResponse

            @self._agent.on_message(model=TradeRequest)
            async def handle_trade_request(ctx: Context, sender: str, msg: TradeRequest):
                """Handle incoming trade requests from other agents."""
                print(f"[AGENT] Received TradeRequest from {sender}")
                
                # Check on-chain permission
                if not self.onchain_identity.has_permission(sender):
                    await ctx.send(sender, TradeResponse(
                        status="error",
                        message="Permission denied"
                    ))
                    return

                try:
                    # Use the reasoning engine to generate strategy
                    result = self.maker_agent.reasoning_engine.reason(
                        msg.user_input,
                        msg.risk_level
                    )
                    
                    if result["status"] == "success":
                        await ctx.send(sender, TradeResponse(
                            status="success",
                            strategy=result.get("strategy", {}),
                            risk_metrics=result.get("risk_metrics", {}),
                            backtest=result.get("backtest", {}),
                            message="Strategy generated successfully"
                        ))
                    else:
                        await ctx.send(sender, TradeResponse(
                            status="error",
                            message=result.get("approval_message", "Strategy generation failed")
                        ))
                except Exception as e:
                    await ctx.send(sender, TradeResponse(
                        status="error",
                        message=str(e)
                    ))

            @self._agent.on_message(model=AnalysisRequest)
            async def handle_analysis_request(ctx: Context, sender: str, msg: AnalysisRequest):
                """Handle incoming analysis requests from other agents."""
                print(f"[AGENT] Received AnalysisRequest from {sender}")
                
                if not self.onchain_identity.has_permission(sender):
                    await ctx.send(sender, AnalysisResponse(
                        status="error",
                        message="Permission denied"
                    ))
                    return

                try:
                    # Use the chat handler for analysis
                    # For now, return a simple acknowledgment
                    await ctx.send(sender, AnalysisResponse(
                        status="success",
                        analysis=f"Analysis for: {msg.query}",
                        message="Analysis request received"
                    ))
                except Exception as e:
                    await ctx.send(sender, AnalysisResponse(
                        status="error",
                        message=str(e)
                    ))

            print(f"[AGENT] uAgent '{AGENT_NAME}' initialized on port {self.port}")
            print(f"[AGENT] Address: {self._agent.address}")

        except ImportError as e:
            print(f"[AGENT] uagents not available (pip install uagents): {e}")
        except Exception as e:
            print(f"[AGENT] Init failed: {e}")

    def handle_aip_message(self, message: AIPMessage) -> AIPResponse:
        """
        Handle incoming AIP protocol messages.
        This is for direct HTTP/REST integration without uAgents.
        """
        try:
            # Check on-chain permission
            if not self.onchain_identity.has_permission(message.sender):
                return AIPResponse(
                    message_type="ErrorResponse",
                    status="error",
                    payload={"error": "Permission denied"},
                    original_message_id=message.message_id
                )

            if message.message_type == "TradeRequest":
                user_input = message.payload.get("user_input", "")
                risk_level = message.payload.get("risk_level", "moderate")
                
                result = self.maker_agent.reasoning_engine.reason(user_input, risk_level)
                
                return AIPResponse(
                    message_type="TradeResponse",
                    status="success" if result["status"] == "success" else "error",
                    payload=result,
                    original_message_id=message.message_id
                )

            elif message.message_type == "AnalysisRequest":
                query = message.payload.get("query", "")
                return AIPResponse(
                    message_type="AnalysisResponse",
                    status="success",
                    payload={"analysis": f"Analysis for: {query}"},
                    original_message_id=message.message_id
                )

            elif message.message_type == "HealthCheck":
                return AIPResponse(
                    message_type="HealthResponse",
                    status="success",
                    payload={
                        "agent_name": AGENT_NAME,
                        "onchain_registered": self.onchain_identity.is_registered,
                    },
                    original_message_id=message.message_id
                )

            else:
                return AIPResponse(
                    message_type="ErrorResponse",
                    status="error",
                    payload={"error": f"Unknown message type: {message.message_type}"},
                    original_message_id=message.message_id
                )

        except Exception as e:
            return AIPResponse(
                message_type="ErrorResponse",
                status="error",
                payload={"error": str(e)},
                original_message_id=message.message_id
            )

    def run(self):
        """Start the agent server (blocking)."""
        if self._agent:
            print(f"[AGENT] Starting agent server...")
            self._running = True
            self._agent.run()

    def run_async(self):
        """Start the agent server in background thread."""
        if self._agent:
            import threading
            thread = threading.Thread(target=self.run, daemon=True)
            thread.start()
            print(f"[AGENT] Agent server started in background")


# --- MAKER AGENT ---

class MakerAgent:
    def __init__(self, llm_endpoint, llm_key, llm_model, risk_level: str = "moderate",
                 cudos_endpoint=None, cudos_key=None, cudos_model=None):
        self.llm_endpoint = llm_endpoint
        self.llm_key = llm_key
        self.llm_model = llm_model
        self.risk_level = risk_level
        
        self.config = ConfigManager()
        print(f"[CONFIG] {len(self.config.pairs)} pairs, {len(self.config.trading_rules)} rules")
        
        self.metta_kb = MeTTaKnowledgeBase()
        
        self.cudos_client = None
        if USE_CUDOS and cudos_endpoint and cudos_key:
            try:
                self.cudos_client = CUDOSInferenceClient(
                    cudos_endpoint or CUDOS_ENDPOINT,
                    cudos_key or CUDOS_API_KEY,
                    cudos_model or CUDOS_MODEL,
                    CUDOS_TIMEOUT
                )
                print(f"[CUDOS] Ready")
            except Exception as e:
                print(f"[WARN] CUDOS init failed: {e}")
        
        self.reasoning_engine = AutonomousReasoningEngine(
            llm_endpoint, llm_key, llm_model, self.metta_kb, self.config, self.cudos_client
        )
        
        # NEW: Intent interpreter + executor
        self.interpreter = UserIntentInterpreter(
            llm_endpoint, llm_key, llm_model, self.cudos_client
        )
        
        # Use Membase-backed conversation manager for production multi-user support
        self.conversation = MembaseConversationManager()
        
        # Trade knowledge base for storing executed trades
        self.trade_kb = TradeKnowledgeBase()
        
        # Executor with access to conversation manager and trade KB for LTM context
        self.executor = TradingExecutor(
            self.metta_kb, self.config, self.reasoning_engine,
            conversation_manager=self.conversation,
            trade_kb=self.trade_kb
        )
        
        # Strategy Agent for deterministic quote generation
        self.strategy_agent = StrategyAgent()
        
        # Default maker config (can be customized per user)
        self.default_maker_config = MakerConfig(
            maker_address=os.getenv("MEMBASE_ACCOUNT", "0x0000000000000000000000000000000000000000"),
            allowed_pairs=self.config.pairs,
            max_trade_size=100000.0,
            daily_caps={"USDC": 1000000.0, "USDT": 1000000.0},
            paused=False,
            min_spread_bps=10,
            max_spread_bps=50,
            default_ttl_sec=60
        )
        
        # Agent server for BitAgent/uAgents communication
        self.agent_server = None
        if ENABLE_AGENT_SERVER:
            self.agent_server = AgentServer(self)

    def handle_message(self, message: str, user_id: str):
        """Handle user messages with full NLP + MeTTa + execution pipeline."""
        self.conversation.add_message(user_id, "user", message)
        lmsg = message.lower().strip()
        
        # Check if user is responding to pending strategy
        if user_id in self.conversation.pending_strategies:
            reasoning = self.conversation.pending_strategies[user_id]
            
            approval_keywords = ["approve", "confirm", "yes", "execute"]
            reject_keywords = ["reject", "no", "cancel", "dismiss"]

            if any(kw in lmsg for kw in approval_keywords):
                reasoning.state = "approved"
                s = reasoning.final_strategy
                if s is not None:
                    response = (
                        f"✓ Strategy '{s.name}' EXECUTED\n\n"
                        f"Entry: ${s.entry_price:.6f}\n"
                        f"Stop: ${s.stop_loss:.6f}\n"
                        f"Take profit: ${s.take_profit:.6f}\n"
                        f"Position size: ${s.position_size:,.0f}\n"
                        f"Confidence: {s.confidence*100:.1f}%"
                    )
                    if reasoning.risk_metrics is not None:
                        rm = reasoning.risk_metrics
                        response += (
                            "\n"
                            f"RR: {rm.risk_reward_ratio:.2f}:1 | Max DD: {rm.max_drawdown:.2f}%\n"
                            f"Win prob: {rm.win_probability*100:.1f}% | Kelly: {rm.kelly_percentage*100:.2f}%"
                        )
                    if reasoning.backtest_result is not None:
                        bt = reasoning.backtest_result
                        response += (
                            "\n"
                            f"Backtest win rate: {bt.win_rate*100:.1f}% | Sharpe: {bt.sharpe_ratio:.2f}"
                        )
                else:
                    response = "✓ Strategy EXECUTED"
                
                # Log executed trade to knowledge base for long-term retrieval
                try:
                    self.trade_kb.log_trade(user_id, reasoning)
                except Exception as e:
                    print(f"[TRADE_KB] Failed to log trade: {e}")
                
                self.conversation.add_message(user_id, "assistant", response, "execution_update", reasoning.reasoning_id)
                del self.conversation.pending_strategies[user_id]
                self.conversation.save_conversation(user_id)
                self.send_message(user_id, {"type": "execution", "status": "success", "message": response})
                return
            
            elif any(kw in lmsg for kw in reject_keywords):
                reasoning.state = "cancelled"
                response = f"✗ Strategy '{reasoning.final_strategy.name}' CANCELLED. What would you like to do instead?"
                self.conversation.add_message(user_id, "assistant", response, "chat", reasoning.reasoning_id)
                del self.conversation.pending_strategies[user_id]
                self.conversation.save_conversation(user_id)
                self.send_message(user_id, {"type": "chat", "message": response})
                return

            # User wants to review full details of the pending strategy
            elif any(kw in lmsg for kw in ["show", "see", "detail", "details", "strategy"]):
                summary = reasoning.approval_summary or "No detailed summary available for this strategy."
                self.conversation.add_message(user_id, "assistant", summary, "chat", reasoning.reasoning_id)
                self.conversation.save_conversation(user_id)
                self.send_message(user_id, {"type": "chat", "message": summary})
                return
        
        # NEW: Use intent interpreter
        print(f"\n[INTERPRETER] Processing: {message}")
        intent = self.interpreter.interpret(message)
        print(f"[INTENT] Type: {intent.intent_type} | Action: {intent.action} | Confidence: {intent.confidence:.1%}")
        
        # Execute intent
        if intent.confidence > 0.5:
            # Pure query/explain intents should be handled as chat, not as executable actions
            if intent.intent_type == "query":
                self._handle_trading_chat(message, user_id)
                return

            execution = self.executor.execute(intent, user_id)
            
            if execution.success:
                response = f"✓ {execution.message}"
                
                # If trade generated, show approval request with a concise summary
                if intent.intent_type == "trade" and execution.data:
                    strategy_data = execution.data.get("strategy", {})
                    strategy_obj = Strategy(**strategy_data) if strategy_data else None

                    rm_data = execution.data.get("risk_metrics") or {}
                    bt_data = execution.data.get("backtest") or {}

                    rm_obj = RiskMetrics(**rm_data) if rm_data else None
                    bt_obj = BacktestResult(**bt_data) if bt_data else None

                    reasoning = AutonomousReasoning(
                        goal=message,
                        user_context=f"User: {user_id}",
                        final_strategy=strategy_obj,
                        risk_metrics=rm_obj,
                        backtest_result=bt_obj,
                        approval_summary=execution.message
                    )
                    self.conversation.pending_strategies[user_id] = reasoning

                    if strategy_obj is not None:
                        s = strategy_obj
                        response += (
                            "\n\n"
                            f"Pair: {s.pair}\n"
                            f"Entry: ${s.entry_price:.6f}\n"
                            f"Stop: ${s.stop_loss:.6f}\n"
                            f"Take profit: ${s.take_profit:.6f}\n"
                            f"Position size: ${s.position_size:,.0f}\n"
                            f"Confidence: {s.confidence*100:.1f}%"
                        )

                        if rm_obj is not None:
                            rm = rm_obj
                            response += (
                                "\n"
                                f"RR: {rm.risk_reward_ratio:.2f}:1 | Max DD: {rm.max_drawdown:.2f}%\n"
                                f"Win prob: {rm.win_probability*100:.1f}% | Kelly: {rm.kelly_percentage*100:.2f}%"
                            )

                        if bt_obj is not None:
                            bt = bt_obj
                            response += (
                                "\n"
                                f"Backtest win rate: {bt.win_rate*100:.1f}% | Sharpe: {bt.sharpe_ratio:.2f}"
                            )

                    response += "\n\nReview strategy and type 'approve' to proceed."
                
                self.conversation.add_message(user_id, "assistant", response, "execution_update")
                self.conversation.save_conversation(user_id)
                self.send_message(user_id, {"type": "execution", "status": "success", "message": response})
            else:
                error_msg = f"✗ {execution.message}\nError: {execution.error}"
                self.conversation.add_message(user_id, "assistant", error_msg)
                self.send_message(user_id, {"type": "error", "message": error_msg})
        else:
            # Low confidence - treat as chat
            self._handle_trading_chat(message, user_id)

    def _handle_trading_chat(self, message: str, user_id: str):
        """Handle general trading questions and discussion."""
        system = """You are an autonomous trading bot assistant. You ARE capable of executing trades on behalf of the user.
This is a REAL trading system that:
- Generates trading strategies based on market data
- Validates strategies using MeTTa symbolic reasoning
- Performs risk assessment and backtesting
- Executes trades when the user confirms/approves

When users ask about trading or strategies, provide actionable advice. If they want to trade, tell them to use commands like:
- "buy ETH" or "trade ETH/USDC" to generate a strategy
- "approve" to execute a pending strategy

Be concise and practical. You are NOT just an advisor - you are part of an automated trading system."""
        
        history = self.conversation.get_conversation_history(user_id)
        
        try:
            llm_headers = {
                "Authorization": f"Bearer {self.llm_key}",
                "Content-Type": "application/json",
            }
            
            messages = [{"role": "system", "content": system}] + history + [{"role": "user", "content": message}]
            
            resp = requests.post(
                self.llm_endpoint + "/chat/completions",
                headers=llm_headers,
                json={
                    "model": self.llm_model,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 1500,
                },
                timeout=60
            )
            data = resp.json()
            response = (data.get("choices") or [{}])[0].get("message", {}).get("content", "Unable to respond")
            
            self.conversation.add_message(user_id, "assistant", response, "chat")
            self.conversation.save_conversation(user_id)
            self.send_message(user_id, {"type": "chat", "message": response})
        
        except Exception as e:
            error_msg = f"Chat failed: {e}"
            self.conversation.add_message(user_id, "assistant", error_msg)
            self.send_message(user_id, {"type": "error", "message": error_msg})

    def send_message(self, recipient: str, data: Dict):
        """Override in subclass to implement message sending."""
        pass

# --- TEST MODE ---

if __name__ == "__main__":
    class PrintBackAgent(MakerAgent):
        def send_message(self, recipient, data):
            print(f"\n{'='*80}")
            if data.get("type") == "execution":
                print(f"[EXECUTION] {data['message']}")
            elif data.get("type") == "error":
                print(f"[ERROR] {data['message']}")
            else:
                print(json.dumps(data, indent=2))
            print(f"{'='*80}\n")

    print("\n[SYSTEM] Autonomous Trading Reasoner - FULL PIPELINE")
    print("  ✓ Intent Interpreter (NLP → Structured Intent)")
    print("  ✓ MeTTa Validation (Symbolic Reasoning)")
    print("  ✓ Trading Executor (LLM + Market Data + Risk Engine)")
    print("  ✓ Strategy Agent (Deterministic Quoting)")
    print("  ✓ Membase Long-Term Memory (Multi-user, Persistent)")
    print("  ✓ Trade Knowledge Base (Local Embeddings)")
    print("  ✓ AIP Protocol (Agent Interaction)")
    print("  ✓ BitAgent/uAgents Server")
    print("  ✓ On-Chain Identity (membase_chain)")
    print("  ✓ Conversation Layer (Multi-turn Chat)\n")

    agent = PrintBackAgent(
        llm_endpoint=LLM_API_ENDPOINT,
        llm_key=LLM_API_KEY,
        llm_model=LLM_MODEL,
        risk_level="moderate",
        cudos_endpoint=CUDOS_ENDPOINT,
        cudos_key=CUDOS_API_KEY,
        cudos_model=CUDOS_MODEL,
    )

    # Start agent server in background if enabled
    if agent.agent_server:
        agent.agent_server.run_async()

    user_id = "trader_001"
    print("Examples:")
    print('  "start trading ETH"')
    print('  "set risk to conservative"')
    print('  "run mean reversion strategy"')
    print('  "explain volatility"')
    print('  "cancel all orders"')
    print("\nAgent Commands:")
    print('  Type "agent status" to see agent server status')
    print('  Type "quote BUY 1000 USDC/ETH" to test Strategy Agent')
    print('  Type "maker stats" to see maker statistics')
    print('  Type "exit" to quit\n')
    
    while True:
        user_input = input(">>> ").strip()
        if user_input.lower() == "exit":
            break
        if not user_input:
            continue
        
        # Special agent commands
        if user_input.lower() == "agent status":
            if agent.agent_server:
                print(f"\n[AGENT STATUS]")
                print(f"  Name: {AGENT_NAME}")
                print(f"  Port: {AGENT_PORT}")
                print(f"  On-chain registered: {agent.agent_server.onchain_identity.is_registered}")
                if agent.agent_server._agent:
                    print(f"  Address: {agent.agent_server._agent.address}")
                print()
            else:
                print("[AGENT] Agent server not enabled")
            continue
        
        # Strategy Agent quote command: "quote BUY 1000 USDC/ETH"
        if user_input.lower().startswith("quote "):
            parts = user_input.split()
            if len(parts) >= 4:
                try:
                    side = parts[1].upper()
                    amount = float(parts[2])
                    pair = parts[3].upper()
                    tokens = pair.split("/")
                    if len(tokens) == 2:
                        token_in, token_out = tokens if side == "SELL" else (tokens[1], tokens[0])
                        
                        # Create test request
                        request = QuoteRequest(
                            chain_id=56,  # BSC
                            side=side,
                            token_in=token_in,
                            token_out=token_out,
                            amount=amount,
                            taker="0xTestTaker"
                        )
                        
                        # Create test pricing snapshot
                        pricing = PricingSnapshot(
                            token_in=token_in,
                            token_out=token_out,
                            mid_price=1.0 if "USD" in token_in or "USD" in token_out else 2000.0,
                            bid_price=0.999 if "USD" in token_in or "USD" in token_out else 1998.0,
                            ask_price=1.001 if "USD" in token_in or "USD" in token_out else 2002.0,
                            spread_bps=20,
                            timestamp=_utc_timestamp(),
                            is_stale=False,
                            confidence=0.95
                        )
                        
                        # Create test chain snapshot
                        chain_snapshot = ChainSnapshot(
                            chain_id=56,
                            strategy_hash="test_strategy",
                            is_active=True,
                            is_docked=False,
                            token_out_budget=1000000.0,
                            token_in_budget=1000000.0,
                            maker_allowance=1000000.0,
                            last_updated=_utc_timestamp()
                        )
                        
                        # Generate quote
                        intent, explain = agent.strategy_agent.generate_quote(
                            request, agent.default_maker_config, pricing, chain_snapshot
                        )
                        
                        print(f"\n{'='*80}")
                        print("[STRATEGY AGENT QUOTE]")
                        if intent.rejected:
                            print(f"  Status: REJECTED")
                            print(f"  Reason: {intent.reason}")
                            print(f"  Rationale: {intent.rationale}")
                        else:
                            print(f"  Status: SUCCESS")
                            print(f"  Amount In: {intent.amount_in:.6f} {token_in}")
                            print(f"  Amount Out: {intent.amount_out:.6f} {token_out}")
                            print(f"  Min Out Net: {intent.min_out_net:.6f}")
                            print(f"  Spread: {intent.spread_bps} bps")
                            print(f"  Nonce: {intent.nonce}")
                            print(f"  Expiry: {intent.expiry}")
                            print(f"  Strategy Hash: {intent.strategy_hash}")
                            print(f"  Idempotency Key: {intent.idempotency_key}")
                        print(f"\n[EXPLAINABILITY]")
                        print(f"  {explain.description}")
                        print(f"  Checks: {', '.join(explain.feasibility_checks)}")
                        if explain.warnings:
                            print(f"  Warnings: {', '.join(explain.warnings)}")
                        print(f"{'='*80}\n")
                    else:
                        print("Invalid pair format. Use: quote BUY 1000 USDC/ETH")
                except ValueError as e:
                    print(f"Invalid amount: {e}")
            else:
                print("Usage: quote <BUY|SELL> <amount> <TOKEN_IN/TOKEN_OUT>")
            continue
        
        # Maker stats command
        if user_input.lower() == "maker stats":
            stats = agent.strategy_agent.get_maker_stats(agent.default_maker_config.maker_address)
            print(f"\n{'='*80}")
            print("[MAKER STATS]")
            print(f"  Address: {stats['maker']}")
            print(f"  Current Nonce: {stats['current_nonce']}")
            print(f"  Fills: {stats['fills']}")
            print(f"  Reverts: {stats['reverts']}")
            print(f"  Revert Rate: {stats['revert_rate']:.2%}")
            print(f"  Daily Volumes: {stats['daily_volumes']}")
            print(f"{'='*80}\n")
            continue
        
        agent.handle_message(user_input, user_id)