import { Injectable } from '@nestjs/common';
import { InjectDataSource } from '@nestjs/typeorm';
import { DataSource } from 'typeorm';
import { NonceStateEntity } from '../db/entities/nonce-state.entity';
import { normalizeAddress } from '../common/utils/addresses';

@Injectable()
export class NoncesService {
  constructor(
    @InjectDataSource()
    private readonly dataSource: DataSource,
  ) {}

  async allocate(chainId: number, makerAddress: string): Promise<string> {
    const checksum = normalizeAddress(makerAddress);
    const queryRunner = this.dataSource.createQueryRunner();
    await queryRunner.connect();
    await queryRunner.startTransaction();
    try {
      let state = await queryRunner.manager.findOne(NonceStateEntity, {
        where: { chainId, makerAddress: checksum },
        lock: { mode: 'pessimistic_write' },
      });
      if (!state) {
        state = queryRunner.manager.create(NonceStateEntity, {
          chainId,
          makerAddress: checksum,
          nextNonce: '0',
        });
      }
      const currentNonce = BigInt(state.nextNonce ?? '0');
      state.nextNonce = (currentNonce + 1n).toString();
      await queryRunner.manager.save(state);
      await queryRunner.commitTransaction();
      return currentNonce.toString();
    } catch (error) {
      await queryRunner.rollbackTransaction();
      throw error;
    } finally {
      await queryRunner.release();
    }
  }
}

