import { Injectable, NotFoundException } from '@nestjs/common';
import { InjectDataSource, InjectRepository } from '@nestjs/typeorm';
import { Repository, DataSource } from 'typeorm';
import { AppConfigEntity } from '../db/entities/app-config.entity';
import { StrategyEntity } from '../db/entities/strategy.entity';
import { StrategiesService } from '../strategies/strategies.service';
import { UpdateChainConfigDto } from './admin.dto';

@Injectable()
export class AdminService {
  constructor(
    @InjectRepository(AppConfigEntity)
    private readonly appConfigRepository: Repository<AppConfigEntity>,
    @InjectRepository(StrategyEntity)
    private readonly strategyRepository: Repository<StrategyEntity>,
    private readonly strategiesService: StrategiesService,
    @InjectDataSource()
    private readonly dataSource: DataSource,
  ) {}

  async updateChainConfig(dto: UpdateChainConfigDto) {
    await this.dataSource.transaction(async (manager) => {
      const appConfigRepo = manager.getRepository(AppConfigEntity);
      const strategyRepo = manager.getRepository(StrategyEntity);

      let config = await appConfigRepo.findOne({
        where: { chainId: dto.chainId },
        lock: { mode: 'pessimistic_write' },
      });
      if (!config) {
        config = appConfigRepo.create({ chainId: dto.chainId, paused: false });
      }

      if (dto.activeStrategyId) {
        const strategy = await strategyRepo.findOne({
          where: { id: dto.activeStrategyId, chainId: dto.chainId },
        });
        if (!strategy) {
          throw new NotFoundException({
            code: 'STRATEGY_NOT_FOUND',
            message: `Strategy ${dto.activeStrategyId} not found for chain ${dto.chainId}`,
          });
        }
        config.activeStrategyId = strategy.id;
      }

      if (dto.paused !== undefined) {
        config.paused = dto.paused;
      }

      await appConfigRepo.save(config);
    });

    return this.strategiesService.getChainMetadata(dto.chainId);
  }
}

