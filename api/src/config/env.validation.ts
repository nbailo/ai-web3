import * as Joi from 'joi';

export const envValidationSchema = Joi.object({
  NODE_ENV: Joi.string().valid('development', 'test', 'production').default('development'),
  PORT: Joi.number().default(8080),
  DATABASE_URL: Joi.string().uri().required(),
  CHAINS_CONFIG_PATH: Joi.string().default('chains.config.json'),
  PRICING_URL: Joi.string().uri().required(),
  STRATEGY_URL: Joi.string().uri().required(),
  REQUEST_TIMEOUT_MS: Joi.number().default(5000),
  GLOBAL_TIMEOUT_MS: Joi.number().default(8000),
  QUOTE_EXPIRY_SECONDS: Joi.number().default(120),
  NONCE_WINDOW_SECONDS: Joi.number().default(30),
  SWAGGER_ENABLED: Joi.boolean().default(true),
});

