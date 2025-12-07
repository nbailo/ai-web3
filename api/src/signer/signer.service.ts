import { Injectable } from '@nestjs/common';
import { TypedDataDomain, Wallet } from 'ethers';
import { ChainsRegistry } from '../config/chains.registry';
import { QuoteSignatureResult, QuoteSigningPayload, QuoteTypedMessage } from './eip712.types';

@Injectable()
export class SignerService {
  private readonly wallets = new Map<number, Wallet>();

  constructor(private readonly chainsRegistry: ChainsRegistry) {}

  async signQuote(payload: QuoteSigningPayload): Promise<QuoteSignatureResult> {
    const wallet = this.getWallet(payload.chainId);

    const domain: TypedDataDomain = {
      name: 'AquaQuoteExecutor',
      version: '1',
      chainId: payload.chainId,
      verifyingContract: payload.executor,
    };

    const types = {
      Quote: [
        { name: 'maker', type: 'address' },
        { name: 'tokenIn', type: 'address' },
        { name: 'tokenOut', type: 'address' },
        { name: 'amountIn', type: 'uint256' },
        { name: 'amountOut', type: 'uint256' },
        { name: 'strategyHash', type: 'bytes32' },
        { name: 'nonce', type: 'uint256' },
        { name: 'expiry', type: 'uint256' },
      ],
    };

    const message: QuoteTypedMessage = {
      maker: payload.maker,
      tokenIn: payload.tokenIn,
      tokenOut: payload.tokenOut,
      amountIn: payload.amountIn,
      amountOut: payload.amountOut,
      strategyHash: payload.strategyHash,
      nonce: payload.nonce,
      expiry: payload.expiry,
    };

    const signature = await wallet.signTypedData(domain, types, message);

    return {
      signature,
      typedData: {
        domain,
        types,
        primaryType: 'Quote',
        message,
      },
    };
  }

  private getWallet(chainId: number): Wallet {
    if (!this.wallets.has(chainId)) {
      const chain = this.chainsRegistry.get(chainId);
      this.wallets.set(chainId, new Wallet(chain.signingKey));
    }
    return this.wallets.get(chainId)!;
  }
}

