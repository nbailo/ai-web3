import { TypedDataDomain } from 'ethers';
export interface QuoteTypedMessage {
  maker: string;
  tokenIn: string;
  tokenOut: string;
  amountIn: string;
  amountOut: string;
  strategyHash: string;
  nonce: string;
  expiry: number;
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

