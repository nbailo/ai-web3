import { ApiProperty } from '@nestjs/swagger';

export class ErrorResponseDto {
  @ApiProperty({ example: 'CHAIN_NOT_SUPPORTED' })
  code!: string;

  @ApiProperty({ example: 'chain 999 is not configured' })
  message!: string;
}

