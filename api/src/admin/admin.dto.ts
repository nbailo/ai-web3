import { IsBoolean, IsInt, IsOptional, IsUUID } from 'class-validator';

export class UpdateChainConfigDto {
  @IsInt()
  chainId!: number;

  @IsOptional()
  @IsUUID()
  activeStrategyId?: string;

  @IsOptional()
  @IsBoolean()
  paused?: boolean;
}

