import { MigrationInterface, QueryRunner } from 'typeorm';

export class InitSchema1711770000000 implements MigrationInterface {
  name = 'InitSchema1711770000000';

  public async up(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(`CREATE EXTENSION IF NOT EXISTS "pgcrypto";`);

    await queryRunner.query(`
      CREATE TABLE "tokens" (
        "chainId" integer NOT NULL,
        "address" character varying(64) NOT NULL,
        "decimals" integer NOT NULL,
        "symbol" character varying(32),
        "createdAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
        "updatedAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
        CONSTRAINT "PK_tokens" PRIMARY KEY ("chainId", "address")
      )
    `);

    await queryRunner.query(`
      CREATE TABLE "pairs" (
        "chainId" integer NOT NULL,
        "token0" character varying(64) NOT NULL,
        "token1" character varying(64) NOT NULL,
        "enabled" boolean NOT NULL DEFAULT true,
        "meta" jsonb,
        "createdAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
        "updatedAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
        CONSTRAINT "PK_pairs" PRIMARY KEY ("chainId", "token0", "token1")
      )
    `);

    await queryRunner.query(`
      CREATE TABLE "strategies" (
        "id" uuid NOT NULL DEFAULT gen_random_uuid(),
        "chainId" integer NOT NULL,
        "name" character varying(128) NOT NULL,
        "version" integer NOT NULL,
        "params" jsonb NOT NULL,
        "enabled" boolean NOT NULL DEFAULT true,
        "createdAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
        "updatedAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
        CONSTRAINT "PK_strategies" PRIMARY KEY ("id")
      )
    `);
    await queryRunner.query(
      `CREATE INDEX "IDX_strategies_chainId_enabled" ON "strategies" ("chainId", "enabled")`,
    );

    await queryRunner.query(`
      CREATE TABLE "app_config" (
        "chainId" integer NOT NULL,
        "activeStrategyId" uuid,
        "paused" boolean NOT NULL DEFAULT false,
        "updatedAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
        CONSTRAINT "PK_app_config" PRIMARY KEY ("chainId")
      )
    `);

    await queryRunner.query(`
      CREATE TABLE "nonce_state" (
        "chainId" integer NOT NULL,
        "makerAddress" character varying(64) NOT NULL,
        "nextNonce" numeric(78, 0) NOT NULL DEFAULT 0,
        CONSTRAINT "PK_nonce_state" PRIMARY KEY ("chainId", "makerAddress")
      )
    `);

    await queryRunner.query(`
      CREATE TABLE "quotes" (
        "quoteId" character varying(64) NOT NULL,
        "chainId" integer NOT NULL,
        "maker" character varying(64) NOT NULL,
        "taker" character varying(64) NOT NULL,
        "recipient" character varying(64) NOT NULL,
        "executor" character varying(64) NOT NULL,
        "strategyId" uuid NOT NULL,
        "strategyVersion" integer NOT NULL,
        "strategyHash" character varying(66) NOT NULL,
        "sellToken" character varying(64) NOT NULL,
        "buyToken" character varying(64) NOT NULL,
        "sellAmount" numeric(78, 0) NOT NULL,
        "buyAmount" numeric(78, 0) NOT NULL,
        "feeBps" integer NOT NULL,
        "feeAmount" numeric(78, 0) NOT NULL,
        "nonce" numeric(78, 0) NOT NULL,
        "expiry" integer NOT NULL,
        "typedData" jsonb NOT NULL,
        "signature" character varying(256) NOT NULL,
        "txTo" character varying(64) NOT NULL,
        "txData" text NOT NULL,
        "txValue" character varying(64) NOT NULL,
        "status" character varying(32) NOT NULL,
        "rejectCode" character varying(64),
        "pricingAsOfMs" bigint,
        "pricingConfidence" double precision,
        "pricingStale" boolean,
        "pricingSources" text[],
        "createdAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
        CONSTRAINT "PK_quotes" PRIMARY KEY ("quoteId")
      )
    `);
    await queryRunner.query(`CREATE INDEX "IDX_quotes_chain_created" ON "quotes" ("chainId", "createdAt")`);
    await queryRunner.query(`CREATE INDEX "IDX_quotes_chain_status" ON "quotes" ("chainId", "status")`);
    await queryRunner.query(`CREATE INDEX "IDX_quotes_chain_taker" ON "quotes" ("chainId", "taker")`);
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(`DROP INDEX "IDX_quotes_chain_taker"`);
    await queryRunner.query(`DROP INDEX "IDX_quotes_chain_status"`);
    await queryRunner.query(`DROP INDEX "IDX_quotes_chain_created"`);
    await queryRunner.query(`DROP TABLE "quotes"`);
    await queryRunner.query(`DROP TABLE "nonce_state"`);
    await queryRunner.query(`DROP TABLE "app_config"`);
    await queryRunner.query(`DROP INDEX "IDX_strategies_chainId_enabled"`);
    await queryRunner.query(`DROP TABLE "strategies"`);
    await queryRunner.query(`DROP TABLE "pairs"`);
    await queryRunner.query(`DROP TABLE "tokens"`);
  }
}

