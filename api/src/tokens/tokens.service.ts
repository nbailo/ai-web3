import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { JsonRpcProvider, Contract } from 'ethers';
import { TokenEntity } from '../db/entities/token.entity';
import { ChainsRegistry } from '../config/chains.registry';
import { normalizeAddress } from '../common/utils/addresses';

const ERC20_ABI = [
  'function decimals() view returns (uint8)',
  'function symbol() view returns (string)',
];

@Injectable()
export class TokensService {
  private readonly providers = new Map<number, JsonRpcProvider>();

  constructor(
    @InjectRepository(TokenEntity)
    private readonly tokenRepository: Repository<TokenEntity>,
    private readonly chainsRegistry: ChainsRegistry,
  ) {}

  async ensureToken(chainId: number, address: string): Promise<TokenEntity> {
    const checksumAddress = normalizeAddress(address);
    const existing = await this.tokenRepository.findOne({
      where: { chainId, address: checksumAddress },
    });
    if (existing) {
      return existing;
    }

    const { decimals, symbol } = await this.fetchOnChainMetadata(chainId, checksumAddress);
    const token = this.tokenRepository.create({
      chainId,
      address: checksumAddress,
      decimals,
      symbol,
    });
    return this.tokenRepository.save(token);
  }

  async list(chainId: number): Promise<TokenEntity[]> {
    return this.tokenRepository.find({ where: { chainId } });
  }

  private async fetchOnChainMetadata(chainId: number, address: string): Promise<{ decimals: number; symbol?: string }> {
    const provider = this.getProvider(chainId);
    const contract = new Contract(address, ERC20_ABI, provider);
    const [decimals, symbol] = await Promise.all([
      contract.decimals(),
      contract.symbol().catch(() => undefined),
    ]);
    return {
      decimals: Number(decimals),
      symbol: typeof symbol === 'string' ? symbol : undefined,
    };
  }

  private getProvider(chainId: number): JsonRpcProvider {
    if (!this.providers.has(chainId)) {
      const chain = this.chainsRegistry.get(chainId);
      this.providers.set(chainId, new JsonRpcProvider(chain.rpcUrl, chainId));
    }
    return this.providers.get(chainId)!;
  }
}

