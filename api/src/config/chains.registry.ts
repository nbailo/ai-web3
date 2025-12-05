import { BadRequestException, Injectable, Logger } from '@nestjs/common';
import { getAddress, isAddress } from 'ethers';

export interface ChainConfig {
  chainId: number;
  name: string;
  rpcUrl: string;
  aqua: string;
  executor: string;
  maker: string;
  signingKey: string;
  pricingUrl: string;
  strategyUrl: string;
}

const REQUIRED_FIELDS: Array<keyof ChainConfig> = [
  'name',
  'rpcUrl',
  'aqua',
  'executor',
  'maker',
  'signingKey',
  'pricingUrl',
  'strategyUrl',
];

@Injectable()
export class ChainsRegistry {
  private readonly logger = new Logger(ChainsRegistry.name);
  private readonly registry = new Map<number, ChainConfig>();

  loadFromJson(json: string): void {
    let parsed: Record<string, any>;
    try {
      parsed = JSON.parse(json);
    } catch (error) {
      throw new Error(`Failed to parse chains config: ${error}`);
    }

    Object.entries(parsed).forEach(([chainIdStr, config]) => {
      const chainId = Number(chainIdStr);
      if (!Number.isInteger(chainId)) {
        throw new Error(`Invalid chain id ${chainIdStr} in chains config`);
      }
      const normalized = this.validateConfig(chainId, config as Record<string, any>);
      this.registry.set(chainId, normalized);
    });

    this.logger.log(`Loaded ${this.registry.size} chain configs`);
  }

  list(): ChainConfig[] {
    return Array.from(this.registry.values());
  }

  get(chainId: number): ChainConfig {
    const config = this.registry.get(chainId);
    if (!config) {
      throw new BadRequestException({
        code: 'CHAIN_NOT_SUPPORTED',
        message: `chain ${chainId} is not configured`,
      });
    }
    return config;
  }

  private validateConfig(chainId: number, config: Record<string, any>): ChainConfig {
    for (const field of REQUIRED_FIELDS) {
      if (!config[field]) {
        throw new Error(`Missing field ${field} for chain ${chainId}`);
      }
    }

    const normalizedAddresses = ['aqua', 'executor', 'maker']
      .map((key) => ({ key, value: config[key] }))
      .reduce<Record<string, string>>((acc, { key, value }) => {
        if (!isAddress(value)) {
          throw new Error(`Invalid address for ${key} on chain ${chainId}`);
        }
        acc[key] = getAddress(value);
        return acc;
      }, {});

    const signingKey: string = config.signingKey;
    if (typeof signingKey !== 'string' || !signingKey.startsWith('0x') || signingKey.length !== 66) {
      throw new Error(`Invalid signingKey for chain ${chainId}`);
    }

    return {
      chainId,
      name: String(config.name),
      rpcUrl: String(config.rpcUrl),
      pricingUrl: String(config.pricingUrl),
      strategyUrl: String(config.strategyUrl),
      signingKey,
      aqua: normalizedAddresses.aqua,
      executor: normalizedAddresses.executor,
      maker: normalizedAddresses.maker,
    };
  }
}

