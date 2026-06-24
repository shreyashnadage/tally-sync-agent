import { Router, Request, Response } from 'express';
import { query } from '../services/database';
import pino from 'pino';

const logger = pino();
const router = Router();

/**
 * GET /api/agents
 * List all connected agents with status
 */
router.get('/', async (req: Request, res: Response) => {
  try {
    const result = await query(`
      SELECT
        id,
        company_name,
        company_guid,
        tally_version,
        agent_version,
        status,
        last_seen_at,
        created_at,
        (SELECT COUNT(*) FROM sync_history WHERE client_id = clients.id) as total_syncs,
        (SELECT completed_at FROM sync_history WHERE client_id = clients.id ORDER BY completed_at DESC LIMIT 1) as last_sync_at
      FROM clients
      ORDER BY last_seen_at DESC NULLS LAST
    `);

    res.json({
      total: result.rows.length,
      agents: result.rows
    });
  } catch (error) {
    logger.error('Error fetching agents:', error);
    res.status(500).json({ error: 'Failed to fetch agents' });
  }
});

/**
 * GET /api/agents/:company_guid
 * Get specific agent details
 */
router.get('/:company_guid', async (req: Request, res: Response) => {
  try {
    const { company_guid } = req.params;

    const result = await query(`
      SELECT
        id,
        company_name,
        company_guid,
        tally_version,
        agent_version,
        status,
        last_seen_at,
        created_at,
        updated_at
      FROM clients
      WHERE company_guid = $1
    `, [company_guid]);

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Agent not found' });
    }

    const agent = result.rows[0];

    // Get recent sync history
    const syncResult = await query(`
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
      LIMIT 20
    `, [agent.id]);

    // Get sync statistics
    const statsResult = await query(`
      SELECT
        COUNT(*) as total_syncs,
        SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) as successful_syncs,
        SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failed_syncs,
        AVG(CASE WHEN status = 'SUCCESS' THEN duration_ms ELSE NULL END) as avg_duration_ms,
        SUM(CASE WHEN status = 'SUCCESS' THEN records_synced ELSE 0 END) as total_records_synced
      FROM sync_history
      WHERE client_id = $1
    `, [agent.id]);

    res.json({
      agent,
      recent_syncs: syncResult.rows,
      statistics: statsResult.rows[0]
    });
  } catch (error) {
    logger.error('Error fetching agent details:', error);
    res.status(500).json({ error: 'Failed to fetch agent details' });
  }
});

/**
 * POST /api/agents
 * Register a new agent (called by agent on first connection)
 */
router.post('/', async (req: Request, res: Response) => {
  try {
    const {
      company_guid,
      company_name,
      api_key_hash,
      tally_version,
      agent_version
    } = req.body;

    if (!company_guid || !company_name || !api_key_hash) {
      return res.status(400).json({ error: 'Missing required fields' });
    }

    // Check if agent already exists
    const existingResult = await query(`
      SELECT id FROM clients WHERE company_guid = $1
    `, [company_guid]);

    let clientId;

    if (existingResult.rows.length > 0) {
      // Update existing agent
      clientId = existingResult.rows[0].id;
      await query(`
        UPDATE clients
        SET
          status = 'ACTIVE',
          last_seen_at = CURRENT_TIMESTAMP,
          updated_at = CURRENT_TIMESTAMP,
          tally_version = COALESCE($2, tally_version),
          agent_version = COALESCE($3, agent_version)
        WHERE id = $1
      `, [clientId, tally_version, agent_version]);
    } else {
      // Create new agent
      const result = await query(`
        INSERT INTO clients (
          company_guid,
          company_name,
          api_key_hash,
          tally_version,
          agent_version,
          status,
          last_seen_at
        ) VALUES ($1, $2, $3, $4, $5, 'ACTIVE', CURRENT_TIMESTAMP)
        RETURNING id
      `, [company_guid, company_name, api_key_hash, tally_version, agent_version]);
      clientId = result.rows[0].id;
    }

    res.status(201).json({
      success: true,
      client_id: clientId,
      message: 'Agent registered successfully'
    });
  } catch (error) {
    logger.error('Error registering agent:', error);
    res.status(500).json({ error: 'Failed to register agent' });
  }
});

/**
 * PUT /api/agents/:company_guid/status
 * Update agent status (heartbeat from agent)
 */
router.put('/:company_guid/status', async (req: Request, res: Response) => {
  try {
    const { company_guid } = req.params;
    const { status, agent_version } = req.body;

    await query(`
      UPDATE clients
      SET
        status = $2,
        last_seen_at = CURRENT_TIMESTAMP,
        agent_version = COALESCE($3, agent_version),
        updated_at = CURRENT_TIMESTAMP
      WHERE company_guid = $1
    `, [company_guid, status || 'ACTIVE', agent_version]);

    res.json({ success: true });
  } catch (error) {
    logger.error('Error updating agent status:', error);
    res.status(500).json({ error: 'Failed to update agent status' });
  }
});

export default router;
