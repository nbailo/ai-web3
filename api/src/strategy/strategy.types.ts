import { PricingSnapshotDto } from '../pricing/pricing.types';

export interface StrategyIntentRequest {
  chainId: number;
  maker: string;
  executor: string;
  taker: string;
  sellToken: string;
  buyToken: string;
  sellAmount: string;
  recipient: string;
  pricingSnapshot: PricingSnapshotDto;
  strategy: {
    id: string;
    version: number;
    params: Record<string, unknown>;
  };
}

export interface StrategyIntentResponse {
  strategy: {
    id: string;
    version: number;
    hash: string;
  };
  buyAmount: string;
  feeBps: number;
  feeAmount: string;
  expiry: number;
  tx: {
    to: string;
    data: string;
    value: string;
  };
  pricing: {
    asOfMs: number;
    confidenceScore: number;
    stale: boolean;
    sourcesUsed: string[];
  };
}

