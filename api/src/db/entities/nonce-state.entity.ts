import { Column, Entity, PrimaryColumn } from 'typeorm';

@Entity({ name: 'nonce_state' })
export class NonceStateEntity {
  @PrimaryColumn({ type: 'integer' })
  chainId!: number;

  @PrimaryColumn({ type: 'varchar', length: 64 })
  makerAddress!: string;

  @Column({ type: 'numeric', precision: 78, scale: 0, default: 0 })
  nextNonce!: string;
}

