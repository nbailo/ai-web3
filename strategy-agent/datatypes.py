from dataclasses import dataclass
from typing import Optional
from typing import List, Dict, Any
import time

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


@dataclass
class AllowedPair:
    """Allowed pair configuration"""
    tokenIn: str
    tokenOut: str

@dataclass
class PricingSnapshot:
    """Pricing data from the price-engine service."""
    chainId: int
    tokenIn: str
    tokenOut: str
    side: str
    midPrice: str
    depthPoints: List[Dict[str, Any]]
    confidenceScore: float  # 0.0 to 1.0
    stale: bool
    sourcesUsed: List[str]
    asOf: float  # Unix timestamp
    sourceBreakdown: Optional[Dict[str, Any]] = None
    latencyMs: Optional[int] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PricingSnapshot':
        """Create PricingSnapshot from dictionary"""
        return cls(
            chainId=data['chainId'],
            tokenIn=data['tokenIn'],
            tokenOut=data['tokenOut'],
            side=data['side'],
            midPrice=str(data['midPrice']),
            depthPoints=data.get('depthPoints', []),
            confidenceScore=float(data.get('confidenceScore', 0.0)),
            stale=bool(data.get('stale', False)),
            sourcesUsed=data.get('sourcesUsed', []),
            asOf=float(data.get('asOf', time.time())),
            sourceBreakdown=data.get('sourceBreakdown'),
            latencyMs=data.get('latencyMs')
        )


@dataclass
class DailyCap:
    """Daily cap configuration"""
    tokenIn: str
    tokenOut: str
    cap: str  # uint256 in base units