import express, { Express, Request, Response, NextFunction } from 'express';
import cors from 'cors';
import { createServer } from 'http';
import { Server as SocketIOServer } from 'socket.io';
import dotenv from 'dotenv';
import pino from 'pino';
import pinoHttp from 'pino-http';

// Routes
import agentsRoutes from './api/agents';
import commandsRoutes from './api/commands';
import syncRoutes from './api/sync';
import healthRoutes from './api/health';

// Database
import { initializeDatabase } from './services/database';

dotenv.config();

const logger = pino();
const app: Express = express();
const httpServer = createServer(app);
const io = new SocketIOServer(httpServer, {
  cors: {
    origin: process.env.FRONTEND_URL || 'http://localhost:3000',
    credentials: true
  }
});

// Middleware
app.use(pinoHttp({ logger }));
app.use(cors({
  origin: process.env.FRONTEND_URL || 'http://localhost:3000',
  credentials: true
}));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Health check
app.get('/health', (req: Request, res: Response) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// API Routes
app.use('/api/agents', agentsRoutes);
app.use('/api/commands', commandsRoutes);
app.use('/api/sync', syncRoutes);
app.use('/api/health', healthRoutes);

// WebSocket Events
io.on('connection', (socket) => {
  logger.info(`Client connected: ${socket.id}`);

  socket.on('disconnect', () => {
    logger.info(`Client disconnected: ${socket.id}`);
  });

  socket.on('agent:heartbeat', (data) => {
    logger.debug(`Heartbeat from agent: ${data.agent_id}`);
    io.emit('agent:heartbeat', data);
  });

  socket.on('agent:status', (data) => {
    logger.debug(`Status update from agent: ${data.agent_id}`);
    io.emit('agent:status', data);
  });
});

// Error handling middleware
app.use((err: any, req: Request, res: Response, next: NextFunction) => {
  logger.error(err);
  res.status(500).json({
    error: 'Internal Server Error',
    message: process.env.NODE_ENV === 'development' ? err.message : undefined
  });
});

// 404 handler
app.use((req: Request, res: Response) => {
  res.status(404).json({ error: 'Not Found' });
});

// Server startup
const PORT = process.env.PORT || 5000;
const HOST = process.env.HOST || '0.0.0.0';

async function startServer() {
  try {
    // Initialize database
    await initializeDatabase();
    logger.info('Database initialized');

    httpServer.listen(PORT, HOST, () => {
      logger.info(`TallyBridge Dashboard Backend running on http://${HOST}:${PORT}`);
      logger.info(`WebSocket server ready for agents`);
    });
  } catch (error) {
    logger.error('Failed to start server:', error);
    process.exit(1);
  }
}

startServer();

export { app, httpServer, io };
