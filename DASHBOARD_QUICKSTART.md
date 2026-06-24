# TallyBridge Dashboard - Quick Start Guide

You've got a **complete Node.js + React + PostgreSQL dashboard** ready to use!

## What's Included

✅ **Backend (Express.js)** - REST API + WebSocket server  
✅ **Frontend (React)** - Agent management UI  
✅ **Database (PostgreSQL)** - Persistent data storage  
✅ **Docker** - Local development environment  
✅ **Deployment Ready** - Vercel + AWS configurations  

---

## Option 1: Run with Docker (Recommended for Testing)

### Prerequisites
- Docker & Docker Compose installed

### Start Everything

```bash
cd dashboard

# Start PostgreSQL + Backend
docker-compose up

# In another terminal, start Frontend
cd frontend
npm install
npm run dev

# Open http://localhost:3000
```

**That's it!** Your dashboard is running.

---

## Option 2: Run Without Docker

### Backend Setup

```bash
cd dashboard/backend

# 1. Create environment file
cp .env.example .env

# 2. Edit .env with your PostgreSQL credentials
# DB_HOST=localhost (or your PostgreSQL server)
# DB_USER=postgres
# DB_PASSWORD=your_password
# DB_NAME=tallybridge

# 3. Install dependencies
npm install

# 4. Start backend
npm run dev

# Backend will be at http://localhost:5000
```

### Frontend Setup

```bash
cd dashboard/frontend

# 1. Create environment file
cp .env.example .env

# 2. Install dependencies
npm install

# 3. Start frontend dev server
npm run dev

# Frontend will be at http://localhost:3000
```

---

## What You Can Do Right Now

### 1. **Dashboard Page** (http://localhost:3000)
- View total agents connected
- View active/inactive/error counts
- See list of all agents with status
- Click "View →" to see agent details

### 2. **Agent Detail Page** (http://localhost:3000/agent/:company_guid)
- Company name and GUID
- Tally version and Agent version
- Last seen timestamp
- Sync statistics
  - Total syncs performed
  - Successful vs failed
  - Average sync duration
  - Total records synced
- Links to sync history and commands

### 3. **Sync History Page**
- Table of all syncs for an agent
- Date, type, records count, duration, status
- Success/failure indicators

### 4. **Commands Page**
- Send commands to agents remotely
  - TRIGGER_SYNC: Start immediate sync
  - FETCH_VOUCHER: Get specific voucher
  - FETCH_LEDGER_BALANCE: Get ledger balance
  - HEALTH_CHECK: Agent health
  - CONFIG_SYNC: Update agent config
- See command execution responses

---

## Testing with Mock Data

Right now, **no agents are connected yet** (since the agent WebSocket client isn't built until Phase 3).

To test the dashboard:

### Option A: Use curl to Register a Test Agent

```bash
curl -X POST http://localhost:5000/api/agents \
  -H "Content-Type: application/json" \
  -d '{
    "company_guid": "test-agent-001",
    "company_name": "National Traders",
    "api_key_hash": "hash123",
    "tally_version": "TallyPrime 4.x",
    "agent_version": "0.1.0"
  }'
```

### Option B: Create Test Data in PostgreSQL

```bash
# Connect to PostgreSQL
psql -U postgres -d tallybridge

# Insert test agent
INSERT INTO clients (company_guid, company_name, api_key_hash, tally_version, agent_version, status, last_seen_at)
VALUES ('test-001', 'ABC Traders', 'hash123', 'ERP 9 R6.6', '0.1.0', 'ACTIVE', NOW());

# Insert test sync record
INSERT INTO sync_history (client_id, sync_type, records_synced, duration_ms, status, completed_at)
SELECT id, 'DELTA', 142, 3450, 'SUCCESS', NOW() FROM clients WHERE company_guid = 'test-001';

# Verify
SELECT * FROM clients;
SELECT * FROM sync_history;
```

Then refresh dashboard at http://localhost:3000 - you should see agents and sync history!

---

## Environment Variables

### Backend (.env)
```
NODE_ENV=development
PORT=5000
HOST=0.0.0.0
FRONTEND_URL=http://localhost:3000

# PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=tallybridge

# Logging
LOG_LEVEL=debug
```

### Frontend (.env)
```
VITE_API_URL=http://localhost:5000
```

---

## Next Steps: Integration with Agent

When the TallyBridge Agent is updated with WebSocket support (Phase 3, Week 15):

1. **Agent calls**: `POST /api/agents` to register itself
2. **Dashboard receives**: `GET /api/agents` returns list
3. **Agent sends**: Heartbeat every 25 seconds to `PUT /api/agents/:guid/status`
4. **Dashboard shows**: Real-time agent status
5. **Dashboard sends**: Commands via `POST /api/commands`
6. **Agent executes**: Command and reports result via `PUT /api/commands/:id/response`
7. **Dashboard updates**: Shows command execution status

**No additional code changes needed** - the integration is already structured!

---

## Deployment Paths

### Frontend → Vercel (Easiest)

```bash
cd dashboard/frontend

# 1. Push to GitHub
git push origin master

# 2. Connect repo to Vercel (vercel.com)
# - Click "Import Project"
# - Select your GitHub repo
# - Set environment: VITE_API_URL=https://your-api-domain.com
# - Click Deploy

# That's it! Deployed to https://your-project.vercel.app
```

### Backend → AWS EC2 (t3.small, Free Tier)

```bash
# On your EC2 instance (Ubuntu 22.04):

# 1. Install Node & PostgreSQL
sudo apt update
sudo apt install -y nodejs postgresql postgresql-contrib

# 2. Clone repo
git clone https://github.com/shreyashnadage/tally-sync-agent.git
cd tally-sync-agent/dashboard/backend

# 3. Setup environment
cp .env.example .env
# Edit .env with EC2 PostgreSQL details

# 4. Install & build
npm install
npm run build

# 5. Start with PM2 (process manager)
npm install -g pm2
pm2 start dist/index.js --name tallybridge-api
pm2 startup  # Auto-restart on reboot
pm2 save

# Backend now running on your EC2 public IP:5000
```

### Database → AWS RDS PostgreSQL (Free Tier)

```bash
# 1. Create RDS instance in AWS Console
#    - PostgreSQL 14
#    - t3.micro (free tier eligible)
#    - Region: ap-south-1 (Mumbai)

# 2. Update backend .env with RDS endpoint
DB_HOST=your-rds-endpoint.rds.amazonaws.com
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=strong-password

# 3. Restart backend
pm2 restart tallybridge-api
```

---

## File Structure

```
tally-sync-agent/
├── tallybridge_agent/          ← Python agent (Phase 1: COMPLETE)
│   └── (66 tests passing)
│
├── dashboard/                  ← Node.js dashboard (YOU ARE HERE)
│   ├── backend/               ← Express API
│   │   ├── src/
│   │   │   ├── api/           ← REST endpoints
│   │   │   ├── services/      ← Database & utilities
│   │   │   └── index.ts       ← Express app
│   │   └── package.json
│   │
│   ├── frontend/              ← React UI
│   │   ├── src/
│   │   │   ├── pages/         ← Dashboard, Agent, History, Commands
│   │   │   ├── components/    ← Navbar, Cards, Tables
│   │   │   └── App.tsx
│   │   └── package.json
│   │
│   ├── docker-compose.yml     ← Local development setup
│   └── README.md              ← Full documentation
│
├── DEPLOYMENT_STRATEGY.md      ← Detailed deployment guide
├── ARCHITECTURE_DIAGRAM.md     ← System design
└── DECISION_MATRIX.md          ← Architecture decisions
```

---

## Common Issues & Fixes

### "Can't connect to PostgreSQL"
```bash
# Make sure PostgreSQL is running
docker-compose up postgres

# Or check local PostgreSQL
sudo systemctl status postgresql
```

### "Backend not responding"
```bash
# Check backend is running
curl http://localhost:5000/health

# Should return: { "status": "ok", "timestamp": "..." }
```

### "Frontend shows 'Connection refused'"
```bash
# Check VITE_API_URL in frontend/.env
VITE_API_URL=http://localhost:5000

# Restart frontend
npm run dev
```

### "Database tables don't exist"
```bash
# Delete and restart PostgreSQL
docker-compose down
docker volume rm dashboard_postgres_data
docker-compose up

# Backend will auto-create tables on startup
```

---

## API Testing

### Quick Test: List Agents
```bash
curl http://localhost:5000/api/agents
# Returns: { "total": 0, "agents": [] }
```

### Quick Test: Health Check
```bash
curl http://localhost:5000/api/health
# Returns: { "status": "ok", "timestamp": "..." }
```

### Quick Test: Database
```bash
curl http://localhost:5000/api/health/database
# Returns: { "status": "connected", "database_time": "..." }
```

---

## What Happens When Agents Connect?

### Current (Phase 1-2)
- Agent code is in `tallybridge_agent/` (Python, 66 tests passing)
- Agent doesn't connect to dashboard yet
- Agent syncs data to cloud API (separate FastAPI backend)

### Phase 3 (Week 15)
- Agent code gets WebSocket client
- Agent registers with dashboard: `POST /api/agents`
- Agent sends heartbeat: `PUT /api/agents/:guid/status` every 25s
- **Dashboard becomes live!**

### Phase 5 (Week 23-24)
- Agent EXE + installer created
- Agent distributed to MSMEs
- Dashboard manages fleet of agents

**You're building the control center ahead of time!** ✨

---

## Next: Test It!

1. **Start dashboard** with Docker or manually
2. **Open** http://localhost:3000
3. **Check health**: Click links, verify API works
4. **Test with curl**: Register a fake agent
5. **See it on dashboard**: Agent should appear in list

Then you're ready for Phase 3 when agent WebSocket is complete!

---

## Questions?

- **Backend issues?** Check `dashboard/backend/README.md`
- **Frontend issues?** Check `dashboard/frontend` (Vite docs)
- **Database issues?** PostgreSQL documentation
- **Deployment?** AWS/Vercel documentation

**You've got a professional SaaS platform ready to launch!** 🚀
