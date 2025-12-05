import { BadRequestException, Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { PairEntity } from '../db/entities/pair.entity';
import { toCanonicalPair } from '../common/utils/canonical-pair';

@Injectable()
export class PairsService {
  constructor(
    @InjectRepository(PairEntity)
    private readonly pairsRepository: Repository<PairEntity>,
  ) {}

  async ensureEnabledPair(chainId: number, sellToken: string, buyToken: string): Promise<PairEntity> {
    const { token0, token1 } = toCanonicalPair(sellToken, buyToken);
    const pair = await this.pairsRepository.findOne({
      where: { chainId, token0, token1 },
    });
    if (!pair || !pair.enabled) {
      throw new BadRequestException({
        code: 'PAIR_NOT_ENABLED',
        message: 'Pair is not enabled for quoting',
      });
    }
    return pair;
  }

  async list(chainId: number): Promise<PairEntity[]> {
    return this.pairsRepository.find({ where: { chainId } });
  }

  async upsertPair(chainId: number, tokenA: string, tokenB: string, enabled: boolean): Promise<PairEntity> {
    const { token0, token1 } = toCanonicalPair(tokenA, tokenB);
    let pair = await this.pairsRepository.findOne({
      where: { chainId, token0, token1 },
    });
    if (!pair) {
      pair = this.pairsRepository.create({
        chainId,
        token0,
        token1,
        enabled,
      });
    } else {
      pair.enabled = enabled;
    }
    return this.pairsRepository.save(pair);
  }
}

