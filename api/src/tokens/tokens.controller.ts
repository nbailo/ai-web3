import { Controller, Get, ParseIntPipe, Query } from '@nestjs/common';
import { ApiTags } from '@nestjs/swagger';
import { TokensService } from './tokens.service';

@ApiTags('admin')
@Controller('admin/tokens')
export class TokensController {
  constructor(private readonly tokensService: TokensService) {}

  @Get()
  list(@Query('chainId', ParseIntPipe) chainId: number) {
    return this.tokensService.list(chainId);
  }
}

