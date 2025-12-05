import { Body, Controller, Get, Param, ParseIntPipe, Post, Query } from '@nestjs/common';
import { ApiTags } from '@nestjs/swagger';
import { IsInt, IsNotEmpty, IsObject, IsString } from 'class-validator';
import { StrategiesService } from './strategies.service';

class CreateStrategyDto {
  @IsInt()
  chainId!: number;

  @IsString()
  @IsNotEmpty()
  name!: string;

  @IsInt()
  version!: number;

  @IsObject()
  params!: Record<string, unknown>;
}

class ActivateStrategyDto {
  @IsInt()
  chainId!: number;
}

@ApiTags('admin')
@Controller('admin/strategies')
export class StrategiesController {
  constructor(private readonly strategiesService: StrategiesService) {}

  @Get()
  list(@Query('chainId', ParseIntPipe) chainId: number) {
    return this.strategiesService.listStrategies(chainId);
  }

  @Post()
  create(@Body() dto: CreateStrategyDto) {
    return this.strategiesService.createStrategy(dto);
  }

  @Post(':id/activate')
  activate(@Param('id') id: string, @Body() dto: ActivateStrategyDto) {
    return this.strategiesService.setActiveStrategy(dto.chainId, id);
  }
}

