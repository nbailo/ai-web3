import { MigrationInterface, QueryRunner } from 'typeorm';

export class AddStrategyHash1712590000000 implements MigrationInterface {
  name = 'AddStrategyHash1712590000000';

  public async up(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(
      `ALTER TABLE "strategies" ADD "hash" character varying(66) NOT NULL DEFAULT ''`,
    );
    await queryRunner.query(`ALTER TABLE "strategies" ALTER COLUMN "hash" DROP DEFAULT`);
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(`ALTER TABLE "strategies" DROP COLUMN "hash"`);
  }
}

