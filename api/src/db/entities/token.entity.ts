import { Column, CreateDateColumn, Entity, PrimaryColumn, UpdateDateColumn } from 'typeorm';

@Entity({ name: 'tokens' })
export class TokenEntity {
  @PrimaryColumn({ type: 'integer' })
  chainId!: number;

  @PrimaryColumn({ type: 'varchar', length: 64 })
  address!: string;

  @Column({ type: 'integer' })
  decimals!: number;

  @Column({ type: 'varchar', length: 32, nullable: true })
  symbol?: string;

  @CreateDateColumn({ type: 'timestamptz' })
  createdAt!: Date;

  @UpdateDateColumn({ type: 'timestamptz' })
  updatedAt!: Date;
}

