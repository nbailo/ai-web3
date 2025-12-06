import { Controller, Get, ParseIntPipe, Query } from '@nestjs/common';
import { ApiOkResponse, ApiOperation, ApiQuery, ApiTags } from '@nestjs/swagger';
import { ChainsRegistry } from './config/chains.registry';
import { StrategiesService } from './strategies/strategies.service';

@Controller()
export class AppController {
  constructor(
    private readonly chainsRegistry: ChainsRegistry,
    private readonly strategiesService: StrategiesService,
  ) {}

  @Get('health')
  @ApiOperation({ summary: 'Liveness check' })
  @ApiOkResponse({ description: 'Service status' })
  health() {
    return {
      status: 'ok',
      timestamp: new Date().toISOString(),
    };
  }

  @Get('metadata')
  @ApiOperation({ summary: 'Chain metadata (maker, executor, active strategy)' })
  @ApiQuery({ name: 'chainId', type: Number })
  @ApiOkResponse({ description: 'Chain metadata' })
  async getMetadata(@Query('chainId', ParseIntPipe) chainId: number) {
    const chain = this.chainsRegistry.get(chainId);
    const meta = await this.strategiesService.getChainMetadata(chainId);
    let activeStrategy = null;
    if (meta.activeStrategyId) {
      activeStrategy = await this.strategiesService.findById(meta.activeStrategyId);
    }
    return {
      chainId,
      chainName: chain.name,
      maker: chain.maker,
      executor: chain.executor,
      paused: meta.paused,
      activeStrategy: activeStrategy
        ? {
            id: activeStrategy.id,
            version: activeStrategy.version,
            name: activeStrategy.name,
          }
        : null,
    };
  }

  @Get('chains')
  @ApiOperation({ summary: 'List supported chains (public safe data)' })
  @ApiOkResponse({
    description: 'Array of chains with public fields',
  })
  getChains() {
    return this.chainsRegistry.list().map(({ chainId, name, maker, executor, aqua }) => ({
      chainId,
      name,
      maker,
      executor,
      aqua,
    }));
  }
}

