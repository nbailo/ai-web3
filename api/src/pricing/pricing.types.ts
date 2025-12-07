export interface DepthPointDto {
  amountInRaw: string;
  amountOutRaw: string;
  price: string;
  impactBps: number;
  provenance: Array<{
    venue: string;
    feeTier?: number;
  }>;
}

export interface PricingSnapshotDto {
  asOfMs: number;
  blockNumber?: number;
  midPrice: string;
  depthPoints: DepthPointDto[];
  sourcesUsed: string[];
  latencyMs: number;
  confidenceScore: number;
  stale: boolean;
  reasonCodes: string[];
}

export interface PricingDepthRequest {
  chainId: number;
  sellToken: string;
  buyToken: string;
  sellAmount: string;
}

