import { Router, Request, Response } from 'express';
import { query } from '../services/database';
import pino from 'pino';

const logger = pino();
const router = Router();

/**
 * GET /api/sync/history/:company_guid
 * Get sync history for an agent
 */
router.get('/history/:company_guid', async (req: Request, res: Response) => {
  try {
    const { company_guid } = req.params;
    const { limit = 50, offset = 0 } = req.query;

    // Get client ID
    const clientResult = await query(`
      SELECT id FROM clients WHERE company_guid = $1
    `, [company_guid]);

    if (clientResult.rows.length === 0) {
      return res.status(404).json({ error: 'Agent not found' });
    }

    const client_id = clientResult.rows[0].id;

    const result = await query(`
      SELECT
        id,
        sync_type,
        records_synced,
        duration_ms,
        status,
        error_message,
        started_at,
        completed_at
      FROM sync_history
      WHERE client_id = $1
      ORDER BY completed_at DESC
      LIMIT $2 OFFSET $3
    `, [client_id, limit, offset]);

    res.json({
      total: result.rows.length,
      limit,
      offset,
      syncs: result.rows
    });
  } catch (error) {
    logger.error('Error fetching sync history:', error);
    res.status(500).json({ error: 'Failed to fetch sync history' });
  }
});

/**
 * POST /api/sync/record
 * Record a sync operation (called by agent after sync completes)
 */
router.post('/record', async (req: Request, res: Response) => {
  try {
    const {
      company_guid,
      sync_type,
      records_synced,
      duration_ms,
      status,
      error_message,
      started_at,
      completed_at
    } = req.body;

    if (!company_guid) {
      return res.status(400).json({ error: 'Missing company_guid' });
    }

    // Get client ID
    const clientResult = await query(`
      SELECT id FROM clients WHERE company_guid = $1
    `, [company_guid]);

    if (clientResult.rows.length === 0) {
      return res.status(404).json({ error: 'Agent not found' });
    }

    const client_id = clientResult.rows[0].id;

    // Record sync
    const result = await query(`
      INSERT INTO sync_history (
        client_id,
        sync_type,
        records_synced,
        duration_ms,
        status,
        error_message,
        started_at,
        completed_at
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
      RETURNING id
    `, [
      client_id,
      sync_type || 'DELTA',
      records_synced || 0,
      duration_ms || 0,
      status || 'SUCCESS',
      error_message || null,
      started_at || null,
      completed_at || null
    ]);

    res.status(201).json({
      success: true,
      sync_id: result.rows[0].id,
      message: 'Sync recorded successfully'
    });
  } catch (error) {
    logger.error('Error recording sync:', error);
    res.status(500).json({ error: 'Failed to record sync' });
  }
});

/**
 * GET /api/sync/stats/:company_guid
 * Get sync statistics for an agent
 */
router.get('/stats/:company_guid', async (req: Request, res: Response) => {
  try {
    const { company_guid } = req.params;

    // Get client ID
    const clientResult = await query(`
      SELECT id FROM clients WHERE company_guid = $1
    `, [company_guid]);

    if (clientResult.rows.length === 0) {
      return res.status(404).json({ error: 'Agent not found' });
    }

    const client_id = clientResult.rows[0].id;

    // Get stats
    const result = await query(`
      SELECT
        COUNT(*) as total_syncs,
        SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) as successful_syncs,
        SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failed_syncs,
        AVG(CASE WHEN status = 'SUCCESS' THEN duration_ms ELSE NULL END)::BIGINT as avg_duration_ms,
        MAX(CASE WHEN status = 'SUCCESS' THEN duration_ms ELSE NULL END)::BIGINT as max_duration_ms,
        MIN(CASE WHEN status = 'SUCCESS' THEN duration_ms ELSE NULL END)::BIGINT as min_duration_ms,
        SUM(CASE WHEN status = 'SUCCESS' THEN records_synced ELSE 0 END) as total_records_synced,
        MAX(completed_at) as last_sync_at
      FROM sync_history
      WHERE client_id = $1
    `, [client_id]);

    res.json(result.rows[0] || {
      total_syncs: 0,
      successful_syncs: 0,
      failed_syncs: 0,
      avg_duration_ms: 0,
      max_duration_ms: 0,
      min_duration_ms: 0,
      total_records_synced: 0,
      last_sync_at: null
    });
  } catch (error) {
    logger.error('Error fetching sync stats:', error);
    res.status(500).json({ error: 'Failed to fetch sync stats' });
  }
});

export default router;
