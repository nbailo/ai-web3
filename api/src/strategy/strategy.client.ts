import { HttpService } from '@nestjs/axios';
import { Injectable, Logger } from '@nestjs/common';
import { AxiosError } from 'axios';
import { firstValueFrom } from 'rxjs';
import { StrategyIntentRequest, StrategyIntentResponse } from './strategy.types';

@Injectable()
export class StrategyClient {
  private readonly logger = new Logger(StrategyClient.name);

  constructor(private readonly httpService: HttpService) {}

  async requestIntent(strategyUrl: string, payload: StrategyIntentRequest): Promise<StrategyIntentResponse> {
    const url = new URL('/intent', strategyUrl).toString();
    try {
      const response = await firstValueFrom(
        this.httpService.post<StrategyIntentResponse>(url, payload),
      );
      return response.data;
    } catch (error) {
      const axiosError = error as AxiosError;
      this.logger.error(
        `Strategy request failed: ${axiosError.code} ${axiosError.message}`,
        axiosError.stack,
      );
      throw axiosError;
    }
  }
}

