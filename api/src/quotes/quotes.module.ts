import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { QuoteEntity } from '../db/entities/quote.entity';
import { NonceStateEntity } from '../db/entities/nonce-state.entity';
import { TokensModule } from '../tokens/tokens.module';
import { PairsModule } from '../pairs/pairs.module';
import { StrategiesModule } from '../strategies/strategies.module';
import { PricingModule } from '../pricing/pricing.module';
import { StrategyModule } from '../strategy/strategy.module';
import { SignerModule } from '../signer/signer.module';
import { QuotesController } from './quotes.controller';
import { QuotesService } from './quotes.service';
import { NoncesService } from './nonces.service';

@Module({
  imports: [
    TypeOrmModule.forFeature([QuoteEntity, NonceStateEntity]),
    TokensModule,
    PairsModule,
    StrategiesModule,
    PricingModule,
    StrategyModule,
    SignerModule,
  ],
  controllers: [QuotesController],
  providers: [QuotesService, NoncesService],
  exports: [QuotesService],
})
export class QuotesModule {}

