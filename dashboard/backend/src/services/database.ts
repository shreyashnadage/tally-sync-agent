import { Pool, Client } from 'pg';
import pino from 'pino';

const logger = pino();

const pool = new Pool({
  user: process.env.DB_USER || 'postgres',
  password: process.env.DB_PASSWORD || 'postgres',
  host: process.env.DB_HOST || 'localhost',
  port: parseInt(process.env.DB_PORT || '5432'),
  database: process.env.DB_NAME || 'tallybridge'
});

pool.on('error', (err) => {
  logger.error('Unexpected error on idle client', err);
});

/**
 * Initialize database: create tables if they don't exist
 */
export async function initializeDatabase() {
  const client = new Client({
    user: process.env.DB_USER || 'postgres',
    password: process.env.DB_PASSWORD || 'postgres',
    host: process.env.DB_HOST || 'localhost',
    port: parseInt(process.env.DB_PORT || '5432'),
    database: process.env.DB_NAME || 'tallybridge'
  });

  try {
    await client.connect();
    logger.info('Connected to PostgreSQL');

    // Create clients table
    await client.query(`
      CREATE TABLE IF NOT EXISTS clients (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        company_name VARCHAR(255) NOT NULL,
        company_guid VARCHAR(36) NOT NULL UNIQUE,
        api_key_hash VARCHAR(255) NOT NULL,
        tally_version VARCHAR(50),
        agent_version VARCHAR(50),
        status VARCHAR(50) DEFAULT 'INACTIVE',
        last_seen_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);
    logger.info('Table: clients');

    // Create sync_history table
    await client.query(`
      CREATE TABLE IF NOT EXISTS sync_history (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
        sync_type VARCHAR(50) DEFAULT 'DELTA',
        records_synced INTEGER DEFAULT 0,
        duration_ms INTEGER,
        status VARCHAR(50) DEFAULT 'SUCCESS',
        error_message TEXT,
        started_at TIMESTAMP,
        completed_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);
    logger.info('Table: sync_history');

    // Create audit_logs table
    await client.query(`
      CREATE TABLE IF NOT EXISTS audit_logs (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
        event_type VARCHAR(100) NOT NULL,
        event_severity VARCHAR(20) DEFAULT 'INFO',
        event_data JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);
    logger.info('Table: audit_logs');

    // Create inbound_commands table
    await client.query(`
      CREATE TABLE IF NOT EXISTS inbound_commands (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
        command_id VARCHAR(36) NOT NULL UNIQUE,
        command_type VARCHAR(50) NOT NULL,
        payload JSONB,
        status VARCHAR(50) DEFAULT 'PENDING',
        response_json JSONB,
        received_at TIMESTAMP,
        executed_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);
    logger.info('Table: inbound_commands');

    // Create indexes
    await client.query(`
      CREATE INDEX IF NOT EXISTS idx_sync_history_client_id ON sync_history(client_id);
      CREATE INDEX IF NOT EXISTS idx_sync_history_created_at ON sync_history(created_at);
      CREATE INDEX IF NOT EXISTS idx_audit_logs_client_id ON audit_logs(client_id);
      CREATE INDEX IF NOT EXISTS idx_audit_logs_event_type ON audit_logs(event_type);
      CREATE INDEX IF NOT EXISTS idx_commands_client_id ON inbound_commands(client_id);
      CREATE INDEX IF NOT EXISTS idx_commands_status ON inbound_commands(status);
    `);
    logger.info('Indexes created');

    await client.end();
    logger.info('Database initialization complete');
  } catch (error) {
    logger.error('Database initialization failed:', error);
    throw error;
  }
}

/**
 * Get database pool for queries
 */
export function getPool() {
  return pool;
}

/**
 * Execute a query
 */
export async function query(text: string, params?: any[]) {
  const start = Date.now();
  try {
    const result = await pool.query(text, params);
    const duration = Date.now() - start;
    if (duration > 1000) {
      logger.warn(`Slow query (${duration}ms): ${text}`);
    }
    return result;
  } catch (error) {
    logger.error(`Query failed: ${text}`, error);
    throw error;
  }
}

/**
 * Close database connection
 */
export async function closeDatabase() {
  await pool.end();
  logger.info('Database pool closed');
}
