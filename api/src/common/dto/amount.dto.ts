import { ApiProperty } from '@nestjs/swagger';
import { Matches } from 'class-validator';

export class AmountDto {
  @ApiProperty({ description: 'Unsigned integer amount represented as a string', example: '1000000000000000000' })
  @Matches(/^\d+$/, { message: 'amount must be provided as a numeric string' })
  amount!: string;
}

