import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { PairsService } from './pairs.service';
import { PairsController } from './pairs.controller';
import { PairEntity } from '../db/entities/pair.entity';

@Module({
  imports: [TypeOrmModule.forFeature([PairEntity])],
  providers: [PairsService],
  controllers: [PairsController],
  exports: [PairsService],
})
export class PairsModule {}

