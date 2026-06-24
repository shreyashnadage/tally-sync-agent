import { Router, Request, Response } from 'express';
import { query } from '../services/database';
import { v4 as uuidv4 } from 'uuid';
import pino from 'pino';

const logger = pino();
const router = Router();

/**
 * POST /api/commands
 * Send a command to an agent
 */
router.post('/', async (req: Request, res: Response) => {
  try {
    const {
      company_guid,
      command_type,
      payload
    } = req.body;

    if (!company_guid || !command_type) {
      return res.status(400).json({ error: 'Missing required fields' });
    }

    // Get client ID from company_guid
    const clientResult = await query(`
      SELECT id FROM clients WHERE company_guid = $1
    `, [company_guid]);

    if (clientResult.rows.length === 0) {
      return res.status(404).json({ error: 'Agent not found' });
    }

    const client_id = clientResult.rows[0].id;
    const command_id = uuidv4();

    // Store command in database
    await query(`
      INSERT INTO inbound_commands (
        client_id,
        command_id,
        command_type,
        payload,
        status,
        received_at
      ) VALUES ($1, $2, $3, $4, 'PENDING', CURRENT_TIMESTAMP)
    `, [client_id, command_id, command_type, JSON.stringify(payload || {})]);

    res.status(201).json({
      success: true,
      command_id,
      command_type,
      status: 'PENDING',
      message: 'Command queued for agent execution'
    });

    // TODO: Emit via WebSocket to notify agent
    logger.info(`Command queued: ${command_type} for agent ${company_guid}`);
  } catch (error) {
    logger.error('Error creating command:', error);
    res.status(500).json({ error: 'Failed to create command' });
  }
});

/**
 * GET /api/commands/:command_id
 * Get command status
 */
router.get('/:command_id', async (req: Request, res: Response) => {
  try {
    const { command_id } = req.params;

    const result = await query(`
      SELECT
        id,
        command_id,
        command_type,
        payload,
        status,
        response_json,
        received_at,
        executed_at
      FROM inbound_commands
      WHERE command_id = $1
    `, [command_id]);

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Command not found' });
    }

    res.json(result.rows[0]);
  } catch (error) {
    logger.error('Error fetching command:', error);
    res.status(500).json({ error: 'Failed to fetch command' });
  }
});

/**
 * PUT /api/commands/:command_id/response
 * Update command response (called by agent after execution)
 */
router.put('/:command_id/response', async (req: Request, res: Response) => {
  try {
    const { command_id } = req.params;
    const { status, response } = req.body;

    await query(`
      UPDATE inbound_commands
      SET
        status = $2,
        response_json = $3,
        executed_at = CURRENT_TIMESTAMP
      WHERE command_id = $1
    `, [command_id, status, JSON.stringify(response || {})]);

    res.json({ success: true });
  } catch (error) {
    logger.error('Error updating command response:', error);
    res.status(500).json({ error: 'Failed to update command response' });
  }
});

/**
 * Supported command types (for reference)
 * - TRIGGER_SYNC: Start sync immediately
 * - FETCH_VOUCHER: Get specific voucher from Tally
 * - FETCH_LEDGER_BALANCE: Get real-time ledger balance
 * - HEALTH_CHECK: Get agent health status
 * - CONFIG_SYNC: Fetch updated config from cloud
 */

export default router;
