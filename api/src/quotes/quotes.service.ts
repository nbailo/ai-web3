import { BadRequestException, Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { randomUUID } from 'crypto';
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
    const pricingSnapshot = await this.pricingClient.requestDepth(chain.pricingUrl, {
      chainId: dto.chainId,
      sellToken: dto.sellToken,
      buyToken: dto.buyToken,
      sellAmount: dto.sellAmount,
    });

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
    const strategyIntent = await this.requestStrategyIntent(dto, price.pricingSnapshot, strategy, recipient);
    const nonce = await this.noncesService.allocate(dto.chainId, chain.maker);
    const quoteId = randomUUID();

    const signatureResult = await this.signerService.signQuote({
      quoteId,
      chainId: dto.chainId,
      executor: chain.executor,
      maker: chain.maker,
      taker: dto.taker,
      recipient,
      sellToken: dto.sellToken,
      buyToken: dto.buyToken,
      sellAmount: dto.sellAmount,
      buyAmount: strategyIntent.buyAmount,
      feeAmount: strategyIntent.feeAmount,
      feeBps: strategyIntent.feeBps,
      expiry: strategyIntent.expiry,
      nonce,
      strategyId: strategyIntent.strategy.id,
      strategyHash: strategyIntent.strategy.hash,
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
      buyAmount: strategyIntent.buyAmount,
      feeBps: strategyIntent.feeBps,
      feeAmount: strategyIntent.feeAmount,
      nonce,
      expiry: strategyIntent.expiry,
      typedData: signatureResult.typedData,
      signature: signatureResult.signature,
      txTo: strategyIntent.tx.to,
      txData: strategyIntent.tx.data,
      txValue: strategyIntent.tx.value,
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
      strategy: { id: strategy.id, params: strategy.params, version: strategy.version },
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
}

