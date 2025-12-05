import {
  Column,
  CreateDateColumn,
  Entity,
  Index,
  PrimaryColumn,
} from 'typeorm';

@Entity({ name: 'quotes' })
@Index(['chainId', 'createdAt'])
@Index(['chainId', 'status'])
@Index(['chainId', 'taker'])
export class QuoteEntity {
  @PrimaryColumn({ type: 'varchar', length: 64 })
  quoteId!: string;

  @Column({ type: 'integer' })
  chainId!: number;

  @Column({ type: 'varchar', length: 64 })
  maker!: string;

  @Column({ type: 'varchar', length: 64 })
  taker!: string;

  @Column({ type: 'varchar', length: 64 })
  recipient!: string;

  @Column({ type: 'varchar', length: 64 })
  executor!: string;

  @Column({ type: 'uuid' })
  strategyId!: string;

  @Column({ type: 'integer' })
  strategyVersion!: number;

  @Column({ type: 'varchar', length: 66 })
  strategyHash!: string;

  @Column({ type: 'varchar', length: 64 })
  sellToken!: string;

  @Column({ type: 'varchar', length: 64 })
  buyToken!: string;

  @Column({ type: 'numeric', precision: 78, scale: 0 })
  sellAmount!: string;

  @Column({ type: 'numeric', precision: 78, scale: 0 })
  buyAmount!: string;

  @Column({ type: 'integer' })
  feeBps!: number;

  @Column({ type: 'numeric', precision: 78, scale: 0 })
  feeAmount!: string;

  @Column({ type: 'numeric', precision: 78, scale: 0 })
  nonce!: string;

  @Column({ type: 'integer' })
  expiry!: number;

  @Column({ type: 'jsonb' })
  typedData!: Record<string, unknown>;

  @Column({ type: 'varchar', length: 256 })
  signature!: string;

  @Column({ type: 'varchar', length: 64 })
  txTo!: string;

  @Column({ type: 'text' })
  txData!: string;

  @Column({ type: 'varchar', length: 64 })
  txValue!: string;

  @Column({ type: 'varchar', length: 32 })
  status!: string;

  @Column({ type: 'varchar', length: 64, nullable: true })
  rejectCode?: string;

  @Column({ type: 'bigint', nullable: true })
  pricingAsOfMs?: string;

  @Column({ type: 'double precision', nullable: true })
  pricingConfidence?: number;

  @Column({ type: 'boolean', nullable: true })
  pricingStale?: boolean;

  @Column({ type: 'text', array: true, nullable: true })
  pricingSources?: string[];

  @CreateDateColumn({ type: 'timestamptz' })
  createdAt!: Date;
}

