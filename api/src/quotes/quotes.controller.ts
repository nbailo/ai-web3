import { Body, Controller, Get, NotFoundException, Param, Post } from '@nestjs/common';
import { ApiBody, ApiOkResponse, ApiOperation, ApiTags } from '@nestjs/swagger';
import { PriceRequestDto, PriceResponseDto, QuoteRequestDto, QuoteResponseDto } from './quotes.dto';
import { QuotesService } from './quotes.service';

@ApiTags('quotes')
@Controller()
export class QuotesController {
  constructor(private readonly quotesService: QuotesService) {}

  @Post('price')
  @ApiOperation({ summary: 'Get indicative price for a sell amount' })
  @ApiBody({
    type: PriceRequestDto,
    examples: {
      baseUsdc: {
        summary: 'Base: WETH -> USDC',
        value: {
          chainId: 8453,
          sellToken: '0x4200000000000000000000000000000000000006',
          buyToken: '0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA',
          sellAmount: '100000000000000000',
        },
      },
    },
  })
  @ApiOkResponse({ type: PriceResponseDto })
  price(@Body() dto: PriceRequestDto) {
    return this.quotesService.getPrice(dto);
  }

  @Post('quote')
  @ApiOperation({ summary: 'Request firm RFQ quote (signed)' })
  @ApiBody({
    type: QuoteRequestDto,
    examples: {
      baseUsdc: {
        summary: 'Base: WETH -> USDC',
        value: {
          chainId: 8453,
          sellToken: '0x4200000000000000000000000000000000000006',
          buyToken: '0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA',
          sellAmount: '100000000000000000',
          taker: '0x1111111111111111111111111111111111111111',
          recipient: '0x1111111111111111111111111111111111111111',
        },
      },
    },
  })
  @ApiOkResponse({ type: QuoteResponseDto })
  quote(@Body() dto: QuoteRequestDto) {
    return this.quotesService.createQuote(dto);
  }

  @Get('quotes/:quoteId')
  @ApiOperation({ summary: 'Fetch previously issued quote by id' })
  @ApiOkResponse({ type: QuoteResponseDto })
  async getQuote(@Param('quoteId') quoteId: string) {
    const quote = await this.quotesService.getQuoteById(quoteId);
    if (!quote) {
      throw new NotFoundException({
        code: 'QUOTE_NOT_FOUND',
        message: `Quote ${quoteId} not found`,
      });
    }
    return quote;
  }
}

