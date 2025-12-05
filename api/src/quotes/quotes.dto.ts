import { ApiProperty } from '@nestjs/swagger';
import { IsEthereumAddress, IsInt, IsOptional, Matches } from 'class-validator';
import { PricingSnapshotDto } from '../pricing/pricing.types';

export class PriceRequestDto {
  @ApiProperty({ example: 8453 })
  @IsInt()
  chainId!: number;

  @ApiProperty()
  @IsEthereumAddress()
  sellToken!: string;

  @ApiProperty()
  @IsEthereumAddress()
  buyToken!: string;

  @ApiProperty({ example: '1000000000000000000' })
  @Matches(/^\d+$/)
  sellAmount!: string;
}

export class PriceResponseDto {
  @ApiProperty()
  chainId!: number;

  @ApiProperty()
  sellToken!: string;

  @ApiProperty()
  buyToken!: string;

  @ApiProperty()
  sellAmount!: string;

  @ApiProperty()
  buyAmount!: string;

  @ApiProperty({ type: () => Object })
  pricingSnapshot!: PricingSnapshotDto;
}

export class QuoteRequestDto extends PriceRequestDto {
  @ApiProperty()
  @IsEthereumAddress()
  taker!: string;

  @ApiProperty({ required: false })
  @IsOptional()
  @IsEthereumAddress()
  recipient?: string;
}

export class QuoteResponseDto {
  @ApiProperty()
  quoteId!: string;

  @ApiProperty()
  chainId!: number;

  @ApiProperty()
  maker!: string;

  @ApiProperty()
  taker!: string;

  @ApiProperty()
  recipient!: string;

  @ApiProperty()
  executor!: string;

  @ApiProperty({ example: { id: 'strategy-id', version: 1, hash: '0x1234' } })
  strategy!: { id: string; version: number; hash: string };

  @ApiProperty()
  sellToken!: string;

  @ApiProperty()
  buyToken!: string;

  @ApiProperty()
  sellAmount!: string;

  @ApiProperty()
  buyAmount!: string;

  @ApiProperty()
  feeBps!: number;

  @ApiProperty()
  feeAmount!: string;

  @ApiProperty()
  expiry!: number;

  @ApiProperty()
  nonce!: string;

  @ApiProperty({ type: () => Object })
  typedData!: unknown;

  @ApiProperty()
  signature!: string;

  @ApiProperty({ example: { to: '0x...', data: '0xabcd', value: '0' } })
  tx!: { to: string; data: string; value: string };

  @ApiProperty({
    example: {
      asOfMs: 123456789,
      confidenceScore: 0.9,
      stale: false,
      sourcesUsed: ['uniswap'],
    },
  })
  pricing!: {
    asOfMs: number;
    confidenceScore: number;
    stale: boolean;
    sourcesUsed: string[];
  };
}

