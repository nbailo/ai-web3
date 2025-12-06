import { Body, Controller, Get, Param, ParseIntPipe, Post, Query } from '@nestjs/common';
import { ApiBody, ApiOkResponse, ApiOperation, ApiQuery, ApiTags } from '@nestjs/swagger';
import { IsInt, IsNotEmpty, IsObject, IsString } from 'class-validator';
import { StrategiesService } from './strategies.service';
import { ApiProperty } from '@nestjs/swagger';
import { StrategyEntity } from '../db/entities/strategy.entity';

class CreateStrategyDto {
  @ApiProperty({ example: 8453 })
  @IsInt()
  chainId!: number;

  @ApiProperty({ example: 'HighVelocity' })
  @IsString()
  @IsNotEmpty()
  name!: string;

  @ApiProperty({ example: 1 })
  @IsInt()
  version!: number;

  @ApiProperty({ example: { maxSlippageBps: 30 } })
  @IsObject()
  params!: Record<string, unknown>;
}

class ActivateStrategyDto {
  @ApiProperty({ example: 8453 })
  @IsInt()
  chainId!: number;
}

@ApiTags('admin')
@Controller('admin/strategies')
export class StrategiesController {
  constructor(private readonly strategiesService: StrategiesService) {}

  @Get()
  @ApiOperation({ summary: 'List strategies configured for a chain' })
  @ApiQuery({ name: 'chainId', type: Number })
  @ApiOkResponse({ type: StrategyEntity, isArray: true })
  list(@Query('chainId', ParseIntPipe) chainId: number) {
    return this.strategiesService.listStrategies(chainId);
  }

  @Post()
  @ApiOperation({ summary: 'Create a new strategy definition' })
  @ApiBody({ type: CreateStrategyDto })
  @ApiOkResponse({ type: StrategyEntity })
  create(@Body() dto: CreateStrategyDto) {
    return this.strategiesService.createStrategy(dto);
  }

  @Post(':id/activate')
  @ApiOperation({ summary: 'Make strategy active for a chain' })
  @ApiBody({ type: ActivateStrategyDto })
  @ApiOkResponse({ description: 'Updated chain config' })
  activate(@Param('id') id: string, @Body() dto: ActivateStrategyDto) {
    return this.strategiesService.setActiveStrategy(dto.chainId, id);
  }
}

