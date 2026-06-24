import { Router, Request, Response } from 'express';
import { query } from '../services/database';
import pino from 'pino';

const logger = pino();
const router = Router();

/**
 * GET /api/health
 * Dashboard health check
 */
router.get('/', (req: Request, res: Response) => {
  res.json({
    status: 'healthy',
    service: 'TallyBridge Dashboard Backend',
    timestamp: new Date().toISOString()
  });
});

/**
 * GET /api/health/agents
 * Get overall agents health
 */
router.get('/agents', async (req: Request, res: Response) => {
  try {
    const result = await query(`
      SELECT
        COUNT(*) as total_agents,
        SUM(CASE WHEN status = 'ACTIVE' THEN 1 ELSE 0 END) as active_agents,
        SUM(CASE WHEN status = 'INACTIVE' THEN 1 ELSE 0 END) as inactive_agents,
        SUM(CASE WHEN status = 'ERROR' THEN 1 ELSE 0 END) as error_agents,
        COUNT(DISTINCT DATE(last_seen_at)) as agents_seen_today
      FROM clients
    `);

    res.json(result.rows[0] || {
      total_agents: 0,
      active_agents: 0,
      inactive_agents: 0,
      error_agents: 0,
      agents_seen_today: 0
    });
  } catch (error) {
    logger.error('Error fetching agents health:', error);
    res.status(500).json({ error: 'Failed to fetch agents health' });
  }
});

/**
 * GET /api/health/database
 * Check database connectivity
 */
router.get('/database', async (req: Request, res: Response) => {
  try {
    const result = await query('SELECT NOW()');
    res.json({
      status: 'connected',
      database_time: result.rows[0].now
    });
  } catch (error) {
    logger.error('Database health check failed:', error);
    res.status(500).json({
      status: 'disconnected',
      error: 'Database connection failed'
    });
  }
});

export default router;
