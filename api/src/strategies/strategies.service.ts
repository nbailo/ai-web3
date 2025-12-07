import { BadRequestException, Injectable, NotFoundException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { StrategyEntity } from '../db/entities/strategy.entity';
import { AppConfigEntity } from '../db/entities/app-config.entity';

@Injectable()
export class StrategiesService {
  constructor(
    @InjectRepository(StrategyEntity)
    private readonly strategyRepository: Repository<StrategyEntity>,
    @InjectRepository(AppConfigEntity)
    private readonly appConfigRepository: Repository<AppConfigEntity>,
  ) {}

  createStrategy(
    data: Pick<StrategyEntity, 'chainId' | 'name' | 'version' | 'params' | 'hash'>,
  ): Promise<StrategyEntity> {
    const entity = this.strategyRepository.create({ ...data, enabled: true });
    return this.strategyRepository.save(entity);
  }

  listStrategies(chainId: number): Promise<StrategyEntity[]> {
    return this.strategyRepository.find({ where: { chainId } });
  }

  findById(id: string): Promise<StrategyEntity | null> {
    return this.strategyRepository.findOne({ where: { id } });
  }

  async setActiveStrategy(chainId: number, strategyId: string): Promise<AppConfigEntity> {
    const strategy = await this.strategyRepository.findOne({ where: { id: strategyId, chainId } });
    if (!strategy) {
      throw new NotFoundException({
        code: 'STRATEGY_NOT_FOUND',
        message: `Strategy ${strategyId} not found for chain ${chainId}`,
      });
    }

    const config = await this.ensureConfig(chainId);
    config.activeStrategyId = strategy.id;
    return this.appConfigRepository.save(config);
  }

  async toggleChainPaused(chainId: number, paused: boolean): Promise<AppConfigEntity> {
    const config = await this.ensureConfig(chainId);
    config.paused = paused;
    return this.appConfigRepository.save(config);
  }

  async getActiveStrategy(chainId: number): Promise<StrategyEntity> {
    const config = await this.ensureConfig(chainId);
    if (!config.activeStrategyId) {
      throw new BadRequestException({
        code: 'STRATEGY_NOT_CONFIGURED',
        message: `No active strategy configured for chain ${chainId}`,
      });
    }
    const strategy = await this.strategyRepository.findOne({
      where: { id: config.activeStrategyId, enabled: true },
    });
    if (!strategy) {
      throw new BadRequestException({
        code: 'STRATEGY_NOT_ENABLED',
        message: `Active strategy ${config.activeStrategyId} is not enabled`,
      });
    }
    return strategy;
  }

  async getChainMetadata(chainId: number): Promise<{
    activeStrategyId?: string | null;
    paused: boolean;
  }> {
    const config = await this.ensureConfig(chainId);
    return {
      activeStrategyId: config.activeStrategyId,
      paused: config.paused,
    };
  }

  private async ensureConfig(chainId: number): Promise<AppConfigEntity> {
    let config = await this.appConfigRepository.findOne({ where: { chainId } });
    if (!config) {
      config = this.appConfigRepository.create({ chainId, paused: false });
      config = await this.appConfigRepository.save(config);
    }
    return config;
  }
}

