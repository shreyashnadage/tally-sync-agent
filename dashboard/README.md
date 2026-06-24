# TallyBridge Dashboard

Professional control panel for managing TallyBridge agents deployed across multiple MSME clients.

## Architecture

```
TallyBridge Dashboard
├── Backend (Express.js + TypeScript)
│   └── REST API + WebSocket Server
├── Frontend (React + TypeScript)
│   └── Responsive UI for agent management
└── Database (PostgreSQL)
    └── Agent health, sync history, commands
```

## Quick Start

### Prerequisites
- Node.js 18+ (backend)
- Node.js 16+ (frontend)
- Docker & Docker Compose (for local dev database)
- PostgreSQL 14+ (if running without Docker)

### Local Development (With Docker)

```bash
# 1. Start PostgreSQL + Backend
cd dashboard
docker-compose up

# 2. In another terminal, start Frontend
cd frontend
npm install
npm run dev

# 3. Open http://localhost:3000
```

### Local Development (Without Docker)

#### Backend
```bash
cd backend
npm install
cp .env.example .env
# Edit .env with your PostgreSQL credentials
npm run dev
# Backend runs on http://localhost:5000
```

#### Frontend
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
# Frontend runs on http://localhost:3000
```

## Project Structure

### Backend (`backend/`)
```
src/
├── api/
│   ├── agents.ts       # Agent endpoints (list, register, status)
│   ├── commands.ts     # Command endpoints (send, get status)
│   ├── sync.ts         # Sync history endpoints
│   └── health.ts       # Health check endpoints
├── services/
│   └── database.ts     # PostgreSQL connection & initialization
├── models/             # (Future: TypeORM models)
├── middleware/         # (Future: auth, logging)
└── index.ts            # Express app + WebSocket setup
```

### Frontend (`frontend/`)
```
src/
├── pages/
│   ├── Dashboard.tsx       # Overview of all agents
│   ├── AgentDetail.tsx     # Single agent details
│   ├── SyncHistory.tsx     # Sync history timeline
│   └── Commands.tsx        # Send commands to agent
├── components/
│   └── Navbar.tsx          # Navigation bar
├── styles/
│   └── index.css           # Tailwind + custom styles
└── App.tsx                 # Router setup
```

## API Endpoints

### Agents
```
GET    /api/agents                    # List all agents
GET    /api/agents/:company_guid      # Get agent details
POST   /api/agents                    # Register new agent
PUT    /api/agents/:company_guid/status  # Update agent status (heartbeat)
```

### Commands
```
POST   /api/commands                  # Send command to agent
GET    /api/commands/:command_id      # Get command status
PUT    /api/commands/:command_id/response  # Agent reports command result
```

### Sync
```
GET    /api/sync/history/:company_guid   # Get sync history
POST   /api/sync/record                  # Record completed sync
GET    /api/sync/stats/:company_guid     # Get sync statistics
```

### Health
```
GET    /api/health                       # Dashboard health
GET    /api/health/agents                # Overall agents health
GET    /api/health/database              # Database connectivity
```

## WebSocket Events

### Client Connected
```
io.on('connection', socket => {
  // Agent or frontend client connected
})
```

### Agent Status Updates
```
socket.on('agent:heartbeat', data => {
  // { agent_id, status, queue_depth, last_sync_at }
  io.emit('agent:heartbeat', data)
})

socket.on('agent:status', data => {
  // { agent_id, status, error_message, etc }
  io.emit('agent:status', data)
})
```

## Database Schema

### clients
```sql
- id (UUID, PK)
- company_name (VARCHAR)
- company_guid (VARCHAR, UNIQUE)
- api_key_hash (VARCHAR)
- tally_version (VARCHAR)
- agent_version (VARCHAR)
- status (ACTIVE/INACTIVE/ERROR)
- last_seen_at (TIMESTAMP)
- created_at, updated_at
```

### sync_history
```sql
- id (UUID, PK)
- client_id (FK → clients)
- sync_type (DELTA/INITIAL)
- records_synced (INTEGER)
- duration_ms (INTEGER)
- status (SUCCESS/FAILED)
- error_message (TEXT)
- started_at, completed_at (TIMESTAMP)
```

### inbound_commands
```sql
- id (UUID, PK)
- client_id (FK → clients)
- command_id (VARCHAR, UNIQUE)
- command_type (TRIGGER_SYNC/FETCH_VOUCHER/etc)
- payload (JSONB)
- status (PENDING/EXECUTED/FAILED)
- response_json (JSONB)
- received_at, executed_at
```

### audit_logs
```sql
- id (UUID, PK)
- client_id (FK → clients)
- event_type (VARCHAR)
- event_severity (INFO/WARNING/ERROR)
- event_data (JSONB)
- created_at (TIMESTAMP)
```

## Environment Variables

### Backend (.env)
```
NODE_ENV=development
PORT=5000
HOST=0.0.0.0
FRONTEND_URL=http://localhost:3000
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=tallybridge
JWT_SECRET=your-secret-key
LOG_LEVEL=info
```

### Frontend (.env)
```
VITE_API_URL=http://localhost:5000
VITE_APP_NAME=TallyBridge
VITE_ENV=development
```

## Deployment

### Vercel (Frontend)
```bash
# Push to GitHub, connect repo to Vercel
# Set environment variables in Vercel dashboard:
# - VITE_API_URL=https://api.yourdomain.com

# Deploy
vercel
```

### AWS EC2 (Backend)
```bash
# Create EC2 instance (t3.small, Ubuntu 22.04)
# SSH into instance

# Install Node & PostgreSQL
sudo apt update && sudo apt install -y nodejs postgresql postgresql-contrib

# Clone repo
git clone https://github.com/shreyashnadage/tally-sync-agent.git
cd tally-sync-agent/dashboard/backend

# Install & run
npm ci
npm run build
NODE_ENV=production npm start

# Or use PM2 for process management
npm install -g pm2
pm2 start dist/index.js --name tallybridge-api
pm2 startup
pm2 save
```

## Features Roadmap

### Phase 1 (Current)
- ✅ Agent registration & status tracking
- ✅ Sync history recording
- ✅ Command queue system
- ✅ Real-time agent overview

### Phase 2 (Weeks 15-19)
- WebSocket integration (real-time updates)
- Command execution on agents
- Live sync progress monitoring
- Analytics dashboard

### Phase 3 (Weeks 20-28)
- User authentication & multi-tenant support
- Advanced filtering & search
- Sync failure alerts & auto-recovery
- Integration with analytics engine

## Testing

### Backend Unit Tests
```bash
cd backend
npm test
```

### Backend Integration Tests
```bash
cd backend
npm run test:integration
```

### Frontend Component Tests
```bash
cd frontend
npm test
```

## Development Guidelines

### Code Style
- Use TypeScript for type safety
- Follow ESLint configuration
- Format with Prettier
- No trailing commas (JSON compatibility)

### Commit Messages
```
feat: Add new feature
fix: Fix a bug
docs: Update documentation
refactor: Code refactoring
test: Add tests
chore: Build/dependency updates
```

### Pull Request Process
1. Create feature branch from `develop`
2. Make changes with tests
3. Push to GitHub
4. Create PR with description
5. Get review approval
6. Merge to `develop`
7. Deploy to staging
8. Merge `develop` → `main` for production

## Security Considerations

- ✅ HMAC-SHA256 signatures on API requests (from agent)
- ✅ CORS restricted to known origins
- ✅ Database credentials in environment variables
- ⏳ JWT authentication (Phase 2)
- ⏳ Rate limiting on API endpoints (Phase 2)
- ⏳ Audit logging of all commands (Phase 2)

## Troubleshooting

### Database Connection Fails
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check connection string in .env
# Default: localhost:5432, user: postgres
```

### API Not Responding
```bash
# Check backend is running
curl http://localhost:5000/health

# Check logs
npm run dev  # Verbose logging
```

### Frontend Can't Connect to API
```bash
# Check VITE_API_URL in .env
# Should match backend port (default: 5000)
# In Docker: use 'backend' as hostname
```

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## License

Proprietary - TallyBridge Project

## Support

For issues, questions, or suggestions:
- GitHub Issues: https://github.com/shreyashnadage/tally-sync-agent/issues
- Email: support@tallybridge.local

## Status

**Phase:** 0.1.0 - MVP (Agent registration + basic management)  
**Production Ready:** No (Alpha testing)  
**Next Milestone:** Real-time WebSocket integration (Phase 2)
