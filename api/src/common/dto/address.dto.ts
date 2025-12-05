import { ApiProperty } from '@nestjs/swagger';
import { IsEthereumAddress } from 'class-validator';

export class AddressDto {
  @ApiProperty({ description: 'EIP-55 checksum address', example: '0x0000000000000000000000000000000000000000' })
  @IsEthereumAddress()
  address!: string;
}

