import { Body, Controller, Get, ParseIntPipe, Post, Query } from '@nestjs/common';
import { ApiTags } from '@nestjs/swagger';
import { IsBoolean, IsEthereumAddress, IsInt } from 'class-validator';
import { PairsService } from './pairs.service';

class UpsertPairDto {
  @IsInt()
  chainId!: number;

  @IsEthereumAddress()
  tokenA!: string;

  @IsEthereumAddress()
  tokenB!: string;

  @IsBoolean()
  enabled!: boolean;
}

@ApiTags('admin')
@Controller('admin/pairs')
export class PairsController {
  constructor(private readonly pairsService: PairsService) {}

  @Get()
  list(@Query('chainId', ParseIntPipe) chainId: number) {
    return this.pairsService.list(chainId);
  }

  @Post()
  upsert(@Body() dto: UpsertPairDto) {
    return this.pairsService.upsertPair(dto.chainId, dto.tokenA, dto.tokenB, dto.enabled);
  }
}

