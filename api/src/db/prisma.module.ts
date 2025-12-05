import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { ConfigService } from '@nestjs/config';
import { TokenEntity } from './entities/token.entity';
import { PairEntity } from './entities/pair.entity';
import { StrategyEntity } from './entities/strategy.entity';
import { AppConfigEntity } from './entities/app-config.entity';
import { NonceStateEntity } from './entities/nonce-state.entity';
import { QuoteEntity } from './entities/quote.entity';

@Module({
  imports: [
    TypeOrmModule.forRootAsync({
      inject: [ConfigService],
      useFactory: (configService: ConfigService) => ({
        type: 'postgres',
        url: configService.getOrThrow<string>('DATABASE_URL'),
        synchronize: false,
        logging: configService.get<string>('NODE_ENV') !== 'production',
        entities: [
          TokenEntity,
          PairEntity,
          StrategyEntity,
          AppConfigEntity,
          NonceStateEntity,
          QuoteEntity,
        ],
      }),
    }),
  ],
  exports: [TypeOrmModule],
})
export class DatabaseModule {}

