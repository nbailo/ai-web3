import { BadRequestException, Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { randomUUID } from 'crypto';
import { Interface, InterfaceAbi } from 'ethers';
import { PricingClient } from '../pricing/pricing.client';
import { StrategyClient } from '../strategy/strategy.client';
import { ChainsRegistry } from '../config/chains.registry';
import { TokensService } from '../tokens/tokens.service';
import { PairsService } from '../pairs/pairs.service';
import { StrategiesService } from '../strategies/strategies.service';
import { SignerService } from '../signer/signer.service';
import { NoncesService } from './nonces.service';
import { QuoteEntity } from '../db/entities/quote.entity';
import { PriceRequestDto, PriceResponseDto, QuoteRequestDto, QuoteResponseDto } from './quotes.dto';
import { PricingSnapshotDto } from '../pricing/pricing.types';
import { StrategyIntentResponse } from '../strategy/strategy.types';
import { StrategyEntity } from '../db/entities/strategy.entity';

const AQUA_EXECUTOR_ABI: InterfaceAbi = [
  'function fill((address maker,address tokenIn,address tokenOut,uint256 amountIn,uint256 amountOut,bytes32 strategyHash,uint256 nonce,uint256 expiry) q, bytes sig, uint256 minAmountOutNet)',
];
const AQUA_EXECUTOR_INTERFACE = new Interface(AQUA_EXECUTOR_ABI);
const ZERO_VALUE = '0';

interface BuildExecutorTxParams {
  executor: string;
  maker: string;
  sellToken: string;
  buyToken: string;
  sellAmount: string;
  buyAmount: string;
  strategyHash: string;
  nonce: string;
  expiry: string;
  minAmountOutNet: string;
  signature: string;
}

@Injectable()
export class QuotesService {
  constructor(
    private readonly pricingClient: PricingClient,
    private readonly strategyClient: StrategyClient,
    private readonly chainsRegistry: ChainsRegistry,
    private readonly tokensService: TokensService,
    private readonly pairsService: PairsService,
    private readonly strategiesService: StrategiesService,
    private readonly signerService: SignerService,
    private readonly noncesService: NoncesService,
    @InjectRepository(QuoteEntity)
    private readonly quotesRepository: Repository<QuoteEntity>,
  ) {}

  async getPrice(dto: PriceRequestDto): Promise<PriceResponseDto> {
    const chain = this.chainsRegistry.get(dto.chainId);
    const chainMeta = await this.strategiesService.getChainMetadata(dto.chainId);
    if (chainMeta.paused) {
      throw new BadRequestException({
        code: 'CHAIN_PAUSED',
        message: `Chain ${dto.chainId} is paused`,
      });
    }
    await this.pairsService.ensureEnabledPair(dto.chainId, dto.sellToken, dto.buyToken);
    await Promise.all([
      this.tokensService.ensureToken(dto.chainId, dto.sellToken),
      this.tokensService.ensureToken(dto.chainId, dto.buyToken),
    ]);
    const rawPricingSnapshot = await this.pricingClient.requestDepth(chain.pricingUrl, {
      chainId: dto.chainId,
      sellToken: dto.sellToken,
      buyToken: dto.buyToken,
      sellAmount: dto.sellAmount,
    });
    const pricingSnapshot = {
      ...rawPricingSnapshot,
      depthPoints: (rawPricingSnapshot.depthPoints ?? []).map((point) => ({
        ...point,
        provenance: Array.isArray(point.provenance)
          ? point.provenance
          : point.provenance
            ? [point.provenance]
            : [],
      })),
    };

    const topDepth = pricingSnapshot.depthPoints[0];
    const buyAmount = topDepth?.amountOutRaw ?? '0';

    return {
      chainId: dto.chainId,
      sellToken: dto.sellToken,
      buyToken: dto.buyToken,
      sellAmount: dto.sellAmount,
      buyAmount,
      pricingSnapshot,
    };
  }

  async createQuote(dto: QuoteRequestDto): Promise<QuoteResponseDto> {
    const recipient = dto.recipient ?? dto.taker;
    const price = await this.getPrice(dto);
    const chain = this.chainsRegistry.get(dto.chainId);
    const strategy = await this.strategiesService.getActiveStrategy(dto.chainId);

    console.log('price', JSON.stringify(price, null, 2));
    console.log('strategy', strategy);
    const strategyIntent = await this.requestStrategyIntent(dto, price.pricingSnapshot, strategy, recipient);
    console.log('strategyIntent', strategyIntent);
    const buyAmount = this.normalizeUint(strategyIntent.buyAmount);
    const feeAmount = this.normalizeUint(strategyIntent.feeAmount);
    const executorFeeBps = chain.executorFeeBps ?? 0;
    const { grossAmount: grossBuyAmount, minNetAmount: minNetBuyAmount } = this.applyExecutorFee(
      buyAmount,
      executorFeeBps,
    );
    const expirySeconds = this.normalizeExpiry(strategyIntent.expiry);
    const nonce = await this.noncesService.allocate(dto.chainId, chain.maker);
    const quoteId = randomUUID();


    const signatureResult = await this.signerService.signQuote({
      chainId: dto.chainId,
      executor: chain.executor,
      maker: chain.maker,
      tokenIn: dto.sellToken,
      tokenOut: dto.buyToken,
      amountIn: dto.sellAmount,
      amountOut: grossBuyAmount,
      strategyHash: strategyIntent.strategy.hash,
      nonce,
      expiry: expirySeconds,
    });

    const executorTx = this.buildExecutorTx({
      executor: chain.executor,
      maker: chain.maker,
      sellToken: dto.sellToken,
      buyToken: dto.buyToken,
      sellAmount: dto.sellAmount,
      buyAmount: grossBuyAmount,
      strategyHash: strategyIntent.strategy.hash,
      nonce,
      expiry: expirySeconds.toString(),
      minAmountOutNet: minNetBuyAmount,
      signature: signatureResult.signature,
    });

    const quote = this.quotesRepository.create({
      quoteId,
      chainId: dto.chainId,
      maker: chain.maker,
      taker: dto.taker,
      recipient,
      executor: chain.executor,
      strategyId: strategyIntent.strategy.id,
      strategyHash: strategyIntent.strategy.hash,
      strategyVersion: strategyIntent.strategy.version,
      sellToken: dto.sellToken,
      buyToken: dto.buyToken,
      sellAmount: dto.sellAmount,
      buyAmount,
      feeBps: strategyIntent.feeBps,
      feeAmount,
      nonce,
      expiry: expirySeconds,
      typedData: signatureResult.typedData,
      signature: signatureResult.signature,
      txTo: executorTx.to,
      txData: executorTx.data,
      txValue: executorTx.value,
      status: 'ISSUED',
      pricingAsOfMs: strategyIntent.pricing.asOfMs.toString(),
      pricingConfidence: strategyIntent.pricing.confidenceScore,
      pricingStale: strategyIntent.pricing.stale,
      pricingSources: strategyIntent.pricing.sourcesUsed,
    });
    await this.quotesRepository.save(quote);

    return this.toQuoteResponse(quote, strategyIntent);
  }

  async getQuoteById(quoteId: string): Promise<QuoteResponseDto | null> {
    const quote = await this.quotesRepository.findOne({ where: { quoteId } });
    if (!quote) {
      return null;
    }
    return this.toQuoteResponse(quote);
  }

  private async requestStrategyIntent(
    dto: QuoteRequestDto,
    pricingSnapshot: PricingSnapshotDto,
    strategy: StrategyEntity,
    recipient: string,
  ): Promise<StrategyIntentResponse> {
    const chain = this.chainsRegistry.get(dto.chainId);
    return this.strategyClient.requestIntent(chain.strategyUrl, {
      chainId: dto.chainId,
      maker: chain.maker,
      executor: chain.executor,
      taker: dto.taker,
      sellToken: dto.sellToken,
      buyToken: dto.buyToken,
      sellAmount: dto.sellAmount,
      recipient,
      pricingSnapshot,
      strategy: { id: strategy.id, hash: strategy.hash, version: strategy.version, params: strategy.params },
    });
  }

  private toQuoteResponse(
    quote: QuoteEntity,
    strategyIntent?: StrategyIntentResponse,
  ): QuoteResponseDto {
    return {
      quoteId: quote.quoteId,
      chainId: quote.chainId,
      maker: quote.maker,
      taker: quote.taker,
      recipient: quote.recipient,
      executor: quote.executor,
      strategy: {
        id: quote.strategyId,
        version: strategyIntent?.strategy.version ?? quote.strategyVersion,
        hash: quote.strategyHash,
      },
      sellToken: quote.sellToken,
      buyToken: quote.buyToken,
      sellAmount: quote.sellAmount,
      buyAmount: quote.buyAmount,
      feeBps: quote.feeBps,
      feeAmount: quote.feeAmount,
      expiry: quote.expiry,
      nonce: quote.nonce,
      typedData: quote.typedData,
      signature: quote.signature,
      tx: {
        to: quote.txTo,
        data: quote.txData,
        value: quote.txValue,
      },
      pricing: strategyIntent
        ? strategyIntent.pricing
        : {
            asOfMs: quote.pricingAsOfMs ? Number(quote.pricingAsOfMs) : 0,
            confidenceScore: quote.pricingConfidence ?? 0,
            stale: quote.pricingStale ?? false,
            sourcesUsed: quote.pricingSources ?? [],
          },
    };
  }

  private buildExecutorTx(params: BuildExecutorTxParams) {
    const quoteStruct = {
      maker: params.maker,
      tokenIn: params.sellToken,
      tokenOut: params.buyToken,
      amountIn: params.sellAmount,
      amountOut: params.buyAmount,
      strategyHash: params.strategyHash,
      nonce: params.nonce,
      expiry: params.expiry,
    };
    const minAmountOutNet = params.minAmountOutNet;
    const data = AQUA_EXECUTOR_INTERFACE.encodeFunctionData('fill', [
      quoteStruct,
      params.signature,
      minAmountOutNet,
    ]);
    return {
      to: params.executor,
      data,
      value: ZERO_VALUE,
    };
  }

  private normalizeUint(value: string | number | bigint): string {
    if (typeof value === 'bigint') {
      return value.toString();
    }
    if (typeof value === 'number') {
      if (!Number.isFinite(value)) {
        throw new Error(`Invalid numeric value ${value}`);
      }
      return Math.trunc(value).toString();
    }
    if (typeof value === 'string') {
      const trimmed = value.trim();
      if (trimmed === '') {
        return '0';
      }
      const [integerPart] = trimmed.split('.');
      const normalized = integerPart.startsWith('-') ? '0' : integerPart || '0';
      return normalized;
    }
    throw new Error(`Unsupported numeric value: ${value}`);
  }

  private normalizeExpiry(value: number | string): number {
    const numeric = typeof value === 'number' ? value : Number(value);
    if (!Number.isFinite(numeric)) {
      throw new Error(`Invalid expiry value: ${value}`);
    }
    // Heuristic: values > 1e12 are likely milliseconds
    const seconds = numeric > 1e12 ? Math.floor(numeric / 1000) : Math.floor(numeric);
    return Math.max(seconds, 0);
  }

  private applyExecutorFee(netAmount: string, feeBps: number): { grossAmount: string; minNetAmount: string } {
    const normalizedFee = Number.isFinite(feeBps) ? Math.max(0, Math.min(9999, Math.floor(feeBps))) : 0;
    const net = BigInt(netAmount);
    if (normalizedFee === 0 || net === 0n) {
      return { grossAmount: net.toString(), minNetAmount: net.toString() };
    }
    const numerator = net * 10000n;
    const denominator = BigInt(10000 - normalizedFee);
    const gross = (numerator + denominator - 1n) / denominator; // ceil to ensure net >= target
    return { grossAmount: gross.toString(), minNetAmount: net.toString() };
  }

}

