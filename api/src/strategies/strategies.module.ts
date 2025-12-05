import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { StrategiesService } from './strategies.service';
import { StrategiesController } from './strategies.controller';
import { StrategyEntity } from '../db/entities/strategy.entity';
import { AppConfigEntity } from '../db/entities/app-config.entity';

@Module({
  imports: [TypeOrmModule.forFeature([StrategyEntity, AppConfigEntity])],
  providers: [StrategiesService],
  controllers: [StrategiesController],
  exports: [StrategiesService],
})
export class StrategiesModule {}

