import { Body, Controller, Get, ParseIntPipe, Post, Query } from '@nestjs/common';
import { ApiBody, ApiOkResponse, ApiOperation, ApiQuery, ApiTags } from '@nestjs/swagger';
import { IsBoolean, IsEthereumAddress, IsInt } from 'class-validator';
import { PairsService } from './pairs.service';
import { ApiProperty } from '@nestjs/swagger';
import { PairEntity } from '../db/entities/pair.entity';

class UpsertPairDto {
  @ApiProperty({ example: 8453 })
  @IsInt()
  chainId!: number;

  @ApiProperty({ example: '0x4200000000000000000000000000000000000006' })
  @IsEthereumAddress()
  tokenA!: string;

  @ApiProperty({ example: '0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA' })
  @IsEthereumAddress()
  tokenB!: string;

  @ApiProperty({ example: true })
  @IsBoolean()
  enabled!: boolean;
}

@ApiTags('admin')
@Controller('admin/pairs')
export class PairsController {
  constructor(private readonly pairsService: PairsService) {}

  @Get()
  @ApiOperation({ summary: 'List canonical pairs for a chain' })
  @ApiQuery({ name: 'chainId', type: Number })
  @ApiOkResponse({ type: PairEntity, isArray: true })
  list(@Query('chainId', ParseIntPipe) chainId: number) {
    return this.pairsService.list(chainId);
  }

  @Post()
  @ApiOperation({ summary: 'Create or update a pair toggle' })
  @ApiBody({ type: UpsertPairDto })
  @ApiOkResponse({ type: PairEntity })
  upsert(@Body() dto: UpsertPairDto) {
    return this.pairsService.upsertPair(dto.chainId, dto.tokenA, dto.tokenB, dto.enabled);
  }
}

