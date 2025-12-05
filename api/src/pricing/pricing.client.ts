import { HttpService } from '@nestjs/axios';
import { Injectable, Logger } from '@nestjs/common';
import { AxiosError } from 'axios';
import { firstValueFrom } from 'rxjs';
import { PricingDepthRequest, PricingSnapshotDto } from './pricing.types';

@Injectable()
export class PricingClient {
  private readonly logger = new Logger(PricingClient.name);

  constructor(private readonly httpService: HttpService) {}

  async requestDepth(pricingUrl: string, payload: PricingDepthRequest): Promise<PricingSnapshotDto> {
    const url = new URL('/depth', pricingUrl).toString();
    try {
      const response = await firstValueFrom(this.httpService.post<PricingSnapshotDto>(url, payload));
      return response.data;
    } catch (error) {
      const axiosError = error as AxiosError;
      this.logger.error(
        `Pricing request failed: ${axiosError.code} ${axiosError.message}`,
        axiosError.stack,
      );
      throw axiosError;
    }
  }
}

