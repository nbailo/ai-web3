import { Module } from '@nestjs/common';
import { HttpModule } from '@nestjs/axios';
import { ConfigService } from '@nestjs/config';
import { PricingClient } from './pricing.client';

@Module({
  imports: [
    HttpModule.registerAsync({
      inject: [ConfigService],
      useFactory: (configService: ConfigService) => ({
        timeout: configService.get<number>('REQUEST_TIMEOUT_MS', 5000),
        maxRedirects: 0,
      }),
    }),
  ],
  providers: [PricingClient],
  exports: [PricingClient],
})
export class PricingModule {}

