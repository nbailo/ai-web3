import { Body, Controller, Get, NotFoundException, Param, Post } from '@nestjs/common';
import { ApiTags } from '@nestjs/swagger';
import { PriceRequestDto, QuoteRequestDto } from './quotes.dto';
import { QuotesService } from './quotes.service';

@ApiTags('quotes')
@Controller()
export class QuotesController {
  constructor(private readonly quotesService: QuotesService) {}

  @Post('price')
  price(@Body() dto: PriceRequestDto) {
    return this.quotesService.getPrice(dto);
  }

  @Post('quote')
  quote(@Body() dto: QuoteRequestDto) {
    return this.quotesService.createQuote(dto);
  }

  @Get('quotes/:quoteId')
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

