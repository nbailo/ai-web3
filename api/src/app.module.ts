import { Module } from '@nestjs/common';
import { ConfigModule } from './config/config.module';
import { DatabaseModule } from './db/prisma.module';
import { TokensModule } from './tokens/tokens.module';
import { PairsModule } from './pairs/pairs.module';
import { StrategiesModule } from './strategies/strategies.module';
import { PricingModule } from './pricing/pricing.module';
import { StrategyModule } from './strategy/strategy.module';
import { SignerModule } from './signer/signer.module';
import { QuotesModule } from './quotes/quotes.module';
import { AdminModule } from './admin/admin.module';
import { AppController } from './app.controller';

@Module({
  imports: [
    ConfigModule,
    DatabaseModule,
    TokensModule,
    PairsModule,
    StrategiesModule,
    PricingModule,
    StrategyModule,
    SignerModule,
    QuotesModule,
    AdminModule,
  ],
  controllers: [AppController],
})
export class AppModule {}

