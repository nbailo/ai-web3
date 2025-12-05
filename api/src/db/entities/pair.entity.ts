import {
  Column,
  CreateDateColumn,
  Entity,
  PrimaryColumn,
  UpdateDateColumn,
} from 'typeorm';

@Entity({ name: 'pairs' })
export class PairEntity {
  @PrimaryColumn({ type: 'integer' })
  chainId!: number;

  @PrimaryColumn({ type: 'varchar', length: 64 })
  token0!: string;

  @PrimaryColumn({ type: 'varchar', length: 64 })
  token1!: string;

  @Column({ type: 'boolean', default: true })
  enabled!: boolean;

  @Column({ type: 'jsonb', nullable: true })
  meta?: Record<string, unknown>;

  @CreateDateColumn({ type: 'timestamptz' })
  createdAt!: Date;

  @UpdateDateColumn({ type: 'timestamptz' })
  updatedAt!: Date;
}

