from dataclasses import dataclass, field
from typing import Optional
from typing import List, Dict, Any
import time
from datetime import datetime

# ============================================================================
# Input Data 
# ============================================================================

# import { PricingSnapshotDto } from '../pricing/pricing.types';
@dataclass
class StrategyInfo:
    """Strategy information for intent requests"""
    id: str
    version: int
    params: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Provenance:
  venue: str
  feeTier: Optional[int] = None

@dataclass
class DepthPointDto:
  amountInRaw: int  # uint256 in base units
  amountOutRaw: int  # uint256 in base units
  price: float
  impactBps: int
  provenance: List[Provenance]


@dataclass
class PricingSnapshotDto:
  asOfMs: int
  midPrice: str
  depthPoints: List[DepthPointDto]
  sourcesUsed: List[str]
  confidenceScore: int
  stale: bool
  reasonCodes: List[str]

@dataclass
class StrategyIntentRequest:
    """Request for a strategy intent"""
    chainId: int
    maker: str
    executor: str
    taker: str
    sellToken: str
    buyToken: str
    sellAmount: int  # uint256 in base units
    recipient: str
    pricingSnapshot: PricingSnapshotDto
    strategy: StrategyInfo

@dataclass
class StrategyInfoResponse:
    """Strategy information in response"""
    id: str
    version: int
    hash: str

@dataclass
class TransactionInfo:
    """Transaction information"""
    to: str
    data: str
    value: int  # uint256 in base units

@dataclass
class PricingInfo:
    """Pricing information in response"""
    asOfMs: int
    confidenceScore: float
    stale: bool
    sourcesUsed: List[str]
    reasonCodes: List[str]

@dataclass
class StrategyIntentResponse:
    """Response containing strategy intent details"""
    decision: str
    strategy: StrategyInfoResponse
    buyAmount: int  # uint256 in base units
    feeBps: int
    feeAmount: int  # uint256 in base units
    expiry: int
    pricing: PricingInfo
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response"""
        return {
            'decision': self.decision,
            'strategy': {
                'id': self.strategy.id,
                'version': self.strategy.version,
                'hash': self.strategy.hash
            },
            'buyAmount': str(self.buyAmount),
            'feeBps': self.feeBps,
            'feeAmount': str(self.feeAmount),
            'expiry': self.expiry,
            'pricing': {
                'asOfMs': self.pricing.asOfMs,
                'confidenceScore': self.pricing.confidenceScore,
                'stale': self.pricing.stale,
                'sourcesUsed': self.pricing.sourcesUsed,
                'reasonCodes': self.pricing.reasonCodes
            },
        }

class RejectionReason:
    STALE_PRICING = "STALE_PRICING"
    MAX_IMPACT_BPS_EXCEEDED = "MAX_IMPACT_BPS_EXCEEDED"
    MAX_TRADE_SIZE_EXCEEDED = "MAX_TRADE_SIZE_EXCEEDED"


