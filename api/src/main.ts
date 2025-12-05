import { NestFactory } from '@nestjs/core';
import { ValidationPipe } from '@nestjs/common';
import { DocumentBuilder, SwaggerModule } from '@nestjs/swagger';
import { json } from 'body-parser';
import { AppModule } from './app.module';
import { HttpExceptionFilter } from './common/filters/http-exception.filter';
import { TimeoutInterceptor } from './common/interceptors/timeout.interceptor';
import { RequestIdInterceptor } from './common/interceptors/request-id.interceptor';
import { ConfigService } from '@nestjs/config';

async function bootstrap(): Promise<void> {
  const app = await NestFactory.create(AppModule, { bufferLogs: true });
  const configService = app.get(ConfigService);

  app.setGlobalPrefix('v1');
  app.useGlobalPipes(
    new ValidationPipe({
      whitelist: true,
      transform: true,
      transformOptions: { enableImplicitConversion: true },
      forbidUnknownValues: false,
    }),
  );
  app.useGlobalFilters(new HttpExceptionFilter());
  const timeoutMs = configService.get<number>('GLOBAL_TIMEOUT_MS', 8000);
  app.useGlobalInterceptors(new RequestIdInterceptor(), new TimeoutInterceptor(timeoutMs));

  app.use(json({ limit: '1mb' }));

  const swaggerEnabled = configService.get<boolean>('SWAGGER_ENABLED', true);
  if (swaggerEnabled) {
    const documentBuilder = new DocumentBuilder()
      .setTitle('Aqua Maker API')
      .setDescription('REST API for quoting, strategy orchestration, and admin operations')
      .setVersion('1.0.0');
    const document = SwaggerModule.createDocument(app, documentBuilder.build());
    SwaggerModule.setup('docs', app, document, {
      jsonDocumentUrl: 'docs-json',
    });
  }

  const port = configService.get<number>('PORT', 8080);
  await app.listen(port);
}

bootstrap().catch((error) => {
  // eslint-disable-next-line no-console
  console.error('Application failed to start', error);
  process.exit(1);
});

