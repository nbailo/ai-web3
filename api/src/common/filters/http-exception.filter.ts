import {
  ArgumentsHost,
  BadRequestException,
  Catch,
  ExceptionFilter,
  HttpException,
  HttpStatus,
} from '@nestjs/common';
import { Request, Response } from 'express';

@Catch()
export class HttpExceptionFilter implements ExceptionFilter {
  catch(exception: unknown, host: ArgumentsHost) {
    const ctx = host.switchToHttp();
    const response = ctx.getResponse<Response>();
    const request = ctx.getRequest<Request>();

    let status = HttpStatus.INTERNAL_SERVER_ERROR;
    let body: Record<string, any> = {
      code: 'INTERNAL_SERVER_ERROR',
      message: 'Unexpected server error',
    };

    if (exception instanceof HttpException) {
      status = exception.getStatus();
      const responseBody = exception.getResponse();
      if (typeof responseBody === 'string') {
        body = { code: exception.name, message: responseBody };
      } else {
        body = responseBody as Record<string, unknown>;
      }
      if (!body['code']) {
        body['code'] = exception.name;
      }
      if (!body['message']) {
        body['message'] = exception.message;
      }
    } else if (exception instanceof Error) {
      body = {
        code: exception.name,
        message: exception.message,
      };
    }

    response.status(status).json({
      ...body,
      statusCode: status,
      requestId: request.headers['x-request-id'] ?? null,
      path: request.url,
      timestamp: new Date().toISOString(),
    });
  }
}

