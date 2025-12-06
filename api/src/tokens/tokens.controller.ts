import { Controller, Get, ParseIntPipe, Query } from '@nestjs/common';
import { ApiOkResponse, ApiOperation, ApiQuery, ApiTags } from '@nestjs/swagger';
import { TokensService } from './tokens.service';
import { TokenEntity } from '../db/entities/token.entity';

@ApiTags('admin')
@Controller('admin/tokens')
export class TokensController {
  constructor(private readonly tokensService: TokensService) {}

  @Get()
  @ApiOperation({ summary: 'List cached token metadata for a chain' })
  @ApiQuery({ name: 'chainId', type: Number })
  @ApiOkResponse({ type: TokenEntity, isArray: true })
  list(@Query('chainId', ParseIntPipe) chainId: number) {
    return this.tokensService.list(chainId);
  }
}

