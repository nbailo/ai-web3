import { BadRequestException, Injectable, Logger } from '@nestjs/common';
import { Wallet, getAddress, isAddress } from 'ethers';

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
  executorFeeBps: number;
}

const REQUIRED_FIELDS: Array<string> = [
  'name',
  'rpcUrl',
  'aqua',
  'executor',
  'signingKeyEnv',
];

@Injectable()
export class ChainsRegistry {
  private readonly logger = new Logger(ChainsRegistry.name);
  private readonly registry = new Map<number, ChainConfig>();

  loadFromJson(
    json: string,
    envLookup: (variable: string) => string | undefined,
  ): void {
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
      const normalized = this.validateConfig(chainId, config as Record<string, any>, envLookup);
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

  private validateConfig(
    chainId: number,
    config: Record<string, any>,
    envLookup: (variable: string) => string | undefined,
  ): ChainConfig {
    for (const field of REQUIRED_FIELDS) {
      if (!config[field]) {
        throw new Error(`Missing field ${field} for chain ${chainId}`);
      }
    }

    const normalizedAddresses = ['aqua', 'executor']
      .map((key) => ({ key, value: config[key] }))
      .reduce<Record<string, string>>((acc, { key, value }) => {
        if (!isAddress(value)) {
          throw new Error(`Invalid address for ${key} on chain ${chainId}`);
        }
        acc[key] = getAddress(value);
        return acc;
      }, {});

    const signingKeyEnv: string = config.signingKeyEnv;
    if (typeof signingKeyEnv !== 'string') {
      throw new Error(`Invalid signingKeyEnv for chain ${chainId}`);
    }
    const signingKey = envLookup(signingKeyEnv);
    if (!signingKey) {
      throw new Error(`Env var ${signingKeyEnv} (signing key for chain ${chainId}) is not set`);
    }
    if (typeof signingKey !== 'string' || !signingKey.startsWith('0x') || signingKey.length !== 66) {
      throw new Error(`Invalid signing key loaded from ${signingKeyEnv} for chain ${chainId}`);
    }
    const makerAddress = new Wallet(signingKey).address;

    const pricingUrl = envLookup('PRICING_URL');
    const strategyUrl = envLookup('STRATEGY_URL');
    if (!pricingUrl) {
      throw new Error('PRICING_URL environment variable is not set');
    }
    if (!strategyUrl) {
      throw new Error('STRATEGY_URL environment variable is not set');
    }

    const executorFeeBps =
      config.executorFeeBps === undefined ? 0 : Number(config.executorFeeBps);
    if (!Number.isFinite(executorFeeBps) || executorFeeBps < 0 || executorFeeBps >= 10000) {
      throw new Error(`Invalid executorFeeBps for chain ${chainId}`);
    }

    return {
      chainId,
      name: String(config.name),
      rpcUrl: String(config.rpcUrl),
      pricingUrl,
      strategyUrl,
      signingKey,
      aqua: normalizedAddresses.aqua,
      executor: normalizedAddresses.executor,
      maker: getAddress(makerAddress),
      executorFeeBps,
    };
  }
}

