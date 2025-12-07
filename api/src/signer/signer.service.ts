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
        { name: 'quoteId', type: 'string' },
        { name: 'maker', type: 'address' },
        { name: 'taker', type: 'address' },
        { name: 'recipient', type: 'address' },
        { name: 'sellToken', type: 'address' },
        { name: 'buyToken', type: 'address' },
        { name: 'sellAmount', type: 'uint256' },
        { name: 'buyAmount', type: 'uint256' },
        { name: 'feeAmount', type: 'uint256' },
        { name: 'feeBps', type: 'uint16' },
        { name: 'expiry', type: 'uint256' },
        { name: 'nonce', type: 'uint256' },
        { name: 'strategyId', type: 'bytes32' },
        { name: 'strategyHash', type: 'bytes32' },
      ],
    };

    const message: QuoteTypedMessage = {
      quoteId: payload.quoteId,
      maker: payload.maker,
      taker: payload.taker,
      recipient: payload.recipient,
      sellToken: payload.sellToken,
      buyToken: payload.buyToken,
      sellAmount: payload.sellAmount,
      buyAmount: payload.buyAmount,
      feeAmount: payload.feeAmount,
      feeBps: payload.feeBps,
      expiry: payload.expiry,
      nonce: payload.nonce,
      strategyId: payload.strategyId,
      strategyHash: payload.strategyHash,
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

