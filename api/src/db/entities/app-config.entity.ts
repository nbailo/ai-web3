import { Column, Entity, PrimaryColumn, UpdateDateColumn } from 'typeorm';

@Entity({ name: 'app_config' })
export class AppConfigEntity {
  @PrimaryColumn({ type: 'integer' })
  chainId!: number;

  @Column({ type: 'uuid', nullable: true })
  activeStrategyId?: string | null;

  @Column({ type: 'boolean', default: false })
  paused!: boolean;

  @UpdateDateColumn({ type: 'timestamptz' })
  updatedAt!: Date;
}

