import 'reflect-metadata';
import { config as loadEnv } from 'dotenv';
import dataSource from '../src/typeorm.config';

loadEnv({ path: process.env.ENV_FILE ?? '.env' });

type Command = 'run' | 'revert' | 'show';

async function migrate() {
  const command = (process.argv[2] as Command) ?? 'run';
  console.log(`[migrate] command: ${command}`);

  await dataSource.initialize();
  console.log('[migrate] data source initialized');

  try {
    if (command === 'run') {
      const migrations = await dataSource.runMigrations();
      migrations.forEach((migration) => {
        console.log(`[migrate] executed: ${migration.name}`);
      });
      console.log(`[migrate] completed (${migrations.length} migration(s))`);
    } else if (command === 'revert') {
      await dataSource.undoLastMigration();
      console.log('[migrate] revert completed (if a migration was pending, it was reverted)');
    } else if (command === 'show') {
      const pending = await dataSource.showMigrations();
      console.log(pending ? '[migrate] pending migrations exist' : '[migrate] no pending migrations');
    } else {
      throw new Error(`Unknown migration command: ${command}`);
    }
  } finally {
    await dataSource.destroy();
    console.log('[migrate] data source closed');
  }
}

migrate().catch((error) => {
  console.error('[migrate] failed', error);
  process.exit(1);
});

