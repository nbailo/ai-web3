import { Global, Module } from '@nestjs/common';
import { ConfigModule as NestConfigModule, ConfigService } from '@nestjs/config';
import { existsSync, readFileSync } from 'fs';
import { isAbsolute, join } from 'path';
import { envValidationSchema } from './env.validation';
import { ChainsRegistry } from './chains.registry';

@Global()
@Module({
  imports: [
    NestConfigModule.forRoot({
      isGlobal: true,
      envFilePath: ['.env', '.env.local'],
      validationSchema: envValidationSchema,
      cache: true,
    }),
  ],
  providers: [
    {
      provide: ChainsRegistry,
      inject: [ConfigService],
      useFactory: (configService: ConfigService) => {
        const registry = new ChainsRegistry();
        const configPath = configService.get<string>('CHAINS_CONFIG_PATH', 'chains.config.json');
        const resolvedPath = isAbsolute(configPath) ? configPath : join(process.cwd(), configPath);
        if (!existsSync(resolvedPath)) {
          throw new Error(`Chains config file not found at ${resolvedPath}`);
        }
        const json = readFileSync(resolvedPath, 'utf8');
        const lookup = (key: string) => configService.get<string>(key);
        registry.loadFromJson(json, lookup);
        return registry;
      },
    },
  ],
  exports: [ChainsRegistry],
})
export class ConfigModule {}

