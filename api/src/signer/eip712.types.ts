import { TypedDataDomain } from 'ethers';
export interface QuoteTypedMessage {
  quoteId: string;
  maker: string;
  taker: string;
  recipient: string;
  sellToken: string;
  buyToken: string;
  sellAmount: string;
  buyAmount: string;
  feeAmount: string;
  feeBps: number;
  expiry: number;
  nonce: string;
  strategyId: string;
  strategyHash: string;
}

export interface QuoteSigningPayload extends QuoteTypedMessage {
  chainId: number;
  executor: string;
}

export interface QuoteSignatureResult {
  typedData: {
    domain: TypedDataDomain;
    types: Record<string, Array<{ name: string; type: string }>>;
    primaryType: string;
    message: QuoteTypedMessage;
  };
  signature: string;
}

