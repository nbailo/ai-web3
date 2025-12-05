import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { AdminController } from './admin.controller';
import { StrategiesModule } from '../strategies/strategies.module';
import { AdminService } from './admin.service';
import { AppConfigEntity } from '../db/entities/app-config.entity';
import { StrategyEntity } from '../db/entities/strategy.entity';

@Module({
  imports: [StrategiesModule, TypeOrmModule.forFeature([AppConfigEntity, StrategyEntity])],
  controllers: [AdminController],
  providers: [AdminService],
})
export class AdminModule {}

