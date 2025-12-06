import { IsBoolean, IsInt, IsOptional, IsUUID } from 'class-validator';
import { ApiProperty } from '@nestjs/swagger';

export class UpdateChainConfigDto {
  @ApiProperty({ example: 8453 })
  @IsInt()
  chainId!: number;

  @ApiProperty({
    required: false,
    description: 'Strategy id to make active for the chain',
    example: '4e48abf7-7c6a-425f-8c9b-8c5a410a7b41',
  })
  @IsOptional()
  @IsUUID()
  activeStrategyId?: string;

  @ApiProperty({ required: false, example: false })
  @IsOptional()
  @IsBoolean()
  paused?: boolean;
}

