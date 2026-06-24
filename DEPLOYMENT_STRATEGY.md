# TallyBridge Agent: Deployment & Remote Management Strategy

## Overview

This document outlines three interconnected systems:
1. **Agent Packaging** — How to create & distribute the EXE to MSMEs
2. **Remote Communication** — How to manage agents remotely via WebSocket
3. **Node.js Dashboard** — GUI for monitoring & controlling agents

---

## Part 1: EXE Creation & Distribution Strategy

### 1.1 Current State (Phase 1)
- ✅ Core agent logic complete (66 tests passing)
- ✅ Database schema ready (SQLCipher encrypted)
- ✅ XML parsing, company locking, preflight checks done
- ❌ No EXE/installer yet
- ❌ WebSocket communication not implemented (Phase 3)

### 1.2 Path to Installable EXE (Phase 5: Weeks 23-24 per BRD)

**High-Level Flow:**
```
Python Code
    ↓
PyInstaller (--onefile)
    ↓
tallybridge_agent.exe (~50MB)
    ↓
Inno Setup Installer
    ↓
Setup.exe (~30MB) + Digital Signature
    ↓
AV Whitelisting (Microsoft, Quick Heal, K7, Kaspersky)
    ↓
Distribution to MSMEs
```

### 1.3 Step-by-Step Implementation

#### Step 1: PyInstaller Configuration
Create `build_config.py` in project root:
```python
# PyInstaller spec file will be generated with:
# - --onefile: Single EXE
# - --windowed: No console window
# - --uac-admin: Require admin (for service installation)
# - --icon: Add app icon
# - --add-data: Include config templates, SQL migrations
```

#### Step 2: Inno Setup Configuration
Create `installer/tallybridge.iss`:
- Silent mode support (`/SILENT`, `/VERYSILENT`)
- Pre-flight AV warning screen
- Windows service registration with delayed start
- Uninstall cleanup (offer to retain local data)
- Min OS check: Windows 7 SP1 64-bit

#### Step 3: Code Signing
- **EV Certificate**: Required for AV trust
  - Sectigo or DigiCert (~$200-300/year)
  - Signing flow: `signtool.exe sign /f cert.pfx /p password /t http://timestamp.server Setup.exe`
  
#### Step 4: AV Whitelisting
```
Microsoft MMPC:        Security Intelligence Portal
Quick Heal:            samples@quickheal.com + partner portal
K7 Security:           samples@k7computing.com
Seqrite (eScan):       Business whitelisting form
Kaspersky India:       Kaspersky Whitelisting Program
```

**Timeline:** Submit hashes Week 23, get responses by Week 28

---

## Part 2: Remote Communication Architecture

### 2.1 Communication Flow

```
MSME Desktop                    Cloud Platform
┌─────────────────┐            ┌──────────────────┐
│ TallyBridge     │            │ FastAPI Server   │
│ Agent (EXE)     │◄──WSS───►│ + WebSocket      │
│                 │            │ (ap-south-1)     │
│                 │            │                  │
│ Local SQLite:   │            │ PostgreSQL:      │
│ - config        │            │ - clients        │
│ - sync_state    │            │ - sync_history   │
│ - commands      │────HTTP────► - live_status    │
│ - audit_log     │            │                  │
└─────────────────┘            └──────────────────┘
                                       ▲
                                       │ WebSocket
                                       │ (bidirectional)
                                       │
                                ┌──────────────────┐
                                │ Node.js Dashboard│
                                │ (React + Express)│
                                │                  │
                                │ - Monitor agents │
                                │ - Trigger syncs  │
                                │ - View errors    │
                                │ - Manage clients │
                                └──────────────────┘
```

### 2.2 Agent-to-Cloud Communication (Per BRD Part 2.4-2.5)

**WebSocket Envelope (Both Directions):**
```json
{
  "message_id": "uuid-v4",
  "message_type": "COMMAND | RESPONSE | HEARTBEAT | STATUS_UPDATE | ACK",
  "command_type": "TRIGGER_SYNC | FETCH_VOUCHER | HEALTH_CHECK",
  "payload": {},
  "timestamp_utc": "2025-04-01T14:32:00Z",
  "agent_version": "1.2.0",
  "company_guid_hash": "sha256-of-guid",
  "hmac_signature": "hex-encoded-hmac-sha256"
}
```

**Heartbeat (Every 25 seconds):**
```
Agent → Cloud: { message_type: "HEARTBEAT", payload: { 
    status: "ACTIVE", 
    queue_depth: 3, 
    last_sync_at: "..." 
}}

Cloud → Agent: { message_type: "ACK", payload: { 
    server_time_utc: "..." 
}}
```

**Commands (Cloud → Agent):**
```
TRIGGER_SYNC         # Start sync immediately
FETCH_VOUCHER        # Get specific voucher from Tally
FETCH_LEDGER_BALANCE # Real-time closing balance
HEALTH_CHECK         # Agent status + Tally connectivity
CONFIG_SYNC          # Fetch updated config (lookback_days, etc.)
```

### 2.3 Implementation Timeline

| Phase | Week | Task | Status |
|-------|------|------|--------|
| PHASE 3 | 15 | WebSocket client (`transport/websocket_client.py`) | ❌ |
| PHASE 3 | 15 | HTTP fallback (`transport/http_fallback.py`) | ❌ |
| PHASE 3 | 16 | Inbound command processor | ❌ |
| PHASE 4 | 20 | Cloud API endpoints (FastAPI) | ❌ |
| PHASE 5 | 23-24 | EXE packaging + code signing | ❌ |

**Key Points:**
- WebSocket is NOT critical for Phase 1 MVP (Delta sync can work with periodic polling)
- Initial rollout can use HTTP long-poll (slower but simpler)
- WebSocket added in Phase 3 for real-time commands

---

## Part 3: Node.js Dashboard GUI Architecture

### 3.1 Why Node.js + React?

| Aspect | Python Desktop | Node.js SaaS |
|--------|---|---|
| **Scope** | Single MSME client | Cloud platform for all clients |
| **Use Case** | Local config + status | Multi-tenant management |
| **Users** | MSME accountant | Your support team + CA firms |
| **Deployment** | Distributed (each desktop) | Centralized (one cloud server) |
| **Tech Stack** | tkinter (outdated) | React + Express (modern) |

### 3.2 Proposed Repository Structure

```
tally-sync-agent/
├── tallybridge_agent/              # Existing Python agent
│   ├── tallybridge_agent/
│   ├── tests/
│   ├── requirements.txt
│   └── setup.py
│
├── dashboard/                       # NEW: Node.js Dashboard
│   ├── backend/
│   │   ├── src/
│   │   │   ├── api/
│   │   │   │   ├── agents.ts       # Agent management endpoints
│   │   │   │   ├── commands.ts     # Send commands to agents
│   │   │   │   ├── sync.ts         # Sync history + status
│   │   │   │   └── health.ts       # Agent health dashboard
│   │   │   ├── services/
│   │   │   │   ├── websocket.ts    # WebSocket connection manager
│   │   │   │   ├── database.ts     # PostgreSQL queries
│   │   │   │   └── auth.ts         # User authentication
│   │   │   └── index.ts            # Express app
│   │   ├── package.json
│   │   └── tsconfig.json
│   │
│   ├── frontend/
│   │   ├── src/
│   │   │   ├── pages/
│   │   │   │   ├── Dashboard.tsx    # Overview of all agents
│   │   │   │   ├── AgentDetail.tsx  # Single agent detail
│   │   │   │   ├── SyncHistory.tsx  # Sync logs
│   │   │   │   └── Commands.tsx     # Send commands to agents
│   │   │   ├── components/
│   │   │   │   ├── AgentCard.tsx
│   │   │   │   ├── SyncStatus.tsx
│   │   │   │   └── RealtimeChart.tsx
│   │   │   ├── hooks/
│   │   │   │   └── useWebSocket.ts  # WebSocket hook
│   │   │   └── App.tsx
│   │   ├── package.json
│   │   └── tsconfig.json
│   │
│   ├── docker-compose.yml           # Local dev: backend + PostgreSQL
│   ├── README.md
│   └── .gitignore
│
├── agent-installer/                 # Packaging (Phase 5)
│   ├── build_config.py
│   ├── tallybridge.iss
│   └── icon.ico
│
├── DEPLOYMENT_STRATEGY.md           # This file
├── README.md
└── .gitignore
```

### 3.3 Dashboard Features & Pages

#### **Dashboard Page** (Real-time overview)
```
┌─────────────────────────────────────────┐
│ TallyBridge Control Panel              │
├─────────────────────────────────────────┤
│                                         │
│  Active Agents: 24                      │
│  Last 24h Syncs: 1,247 vouchers        │
│  Failed Syncs: 2                        │
│                                         │
│  ┌─────────────────┬──────────────┐    │
│  │ Agent (Company) │ Status       │    │
│  ├─────────────────┼──────────────┤    │
│  │ National Trad.  │ [●] ACTIVE   │◄───┼──TRIGGER SYNC
│  │ Last sync: 5min │ Queue: 0     │    │
│  ├─────────────────┼──────────────┤    │
│  │ ABC Traders     │ [●] ACTIVE   │    │
│  │ Last sync: 2h   │ Queue: 3     │    │
│  ├─────────────────┼──────────────┤    │
│  │ XYZ Corp        │ [⚠] STALE    │    │
│  │ Last sync: 36h  │ Queue: 0     │    │
│  └─────────────────┴──────────────┘    │
└─────────────────────────────────────────┘
```

#### **Agent Detail Page**
```
Agent: National Traders
GUID: 550e8400-e29b-41d4-a716-446655440000
Status: ACTIVE (connected 2h 15min)
Tally Version: TallyPrime 4.x

Last Sync: 5 minutes ago
  - Synced: 147 vouchers
  - Duration: 3min 22sec
  - Status: ✓ SUCCESS

Next Sync: ~25 minutes (scheduled)

Actions:
[Trigger Sync Now] [Fetch Voucher] [View Logs] [Configure]
```

#### **Sync History Page**
```
Agent: National Traders

Date        | Duration | Records | Status  | Details
------------|----------|---------|---------|----------
Jun 24 16:00| 3m 22s   | 147     | ✓ OK    | 5min ago
Jun 24 15:30| 3m 18s   | 142     | ✓ OK    |
Jun 24 15:00| 3m 25s   | 138     | ✓ OK    |
Jun 24 14:30| 2m 45s   | 0       | ⚠ WARN  | No new records
Jun 24 14:00| 3m 31s   | 156     | ✓ OK    |
Jun 23 22:00| 4m 02s   | 0       | ⚠ WARN  | Tally offline
Jun 23 21:30| ERROR    | -       | ✗ FAIL  | GUID migration required
```

#### **Commands Page**
```
Send Command to Agent:

Agent: [National Traders ▼]

Command Type:
  ◯ TRIGGER_SYNC        (Start sync immediately)
  ◯ FETCH_VOUCHER       (Get specific voucher)
  ◯ FETCH_LEDGER_BALANCE(Get balance for ledger)
  ◯ HEALTH_CHECK        (Get full agent status)
  ◯ CONFIG_SYNC         (Fetch updated config)

Command Details:
  Voucher GUID: [input] (for FETCH_VOUCHER)

[Send Command]

Response:
{
  "status": "PENDING",
  "sent_at": "2025-06-24T16:00:00Z",
  "execution_time": "0.5s",
  "result": {...}
}
```

### 3.4 Technology Stack

**Backend:**
- Express.js (minimal, lightweight)
- TypeScript (type safety)
- Socket.io (WebSocket with fallbacks)
- PostgreSQL (client list, sync history, logs)
- JWT (authentication)

**Frontend:**
- React 18 (components)
- TypeScript
- TailwindCSS (styling)
- Recharts (real-time graphs)
- Socket.io-client (real-time updates)

**Deployment:**
- Docker (backend + PostgreSQL)
- Vercel/Netlify (frontend)
- AWS RDS (PostgreSQL)

---

## Part 4: Complete Integration Flow

### 4.1 Installation Day (MSME)

```
1. You send: Setup.exe (signed + AV whitelisted)
2. MSME runs installer
3. Agent installs as Windows service
4. Service auto-starts on boot
5. On first run:
   - Shows onboarding wizard
   - Asks for cloud API key
   - Detects local Tally
   - Locks company + creates fingerprint
   - Stores encrypted config in SQLite
6. Service connects to cloud (WebSocket/HTTP long-poll)
7. Dashboard shows agent as ACTIVE
8. First sync begins automatically
```

### 4.2 Daily Operation

```
Agent (MSME Desktop)          Cloud Dashboard
    │                              │
    ├─ Heartbeat (every 25s) ─────►│
    │                              │
    │◄─ ACK + new config ──────────┤
    │                              │
    ├─ Scheduled sync (every 4h) ─►│
    │  - Sends: new vouchers       │
    │◄─ Returns: ✓ OK              │
    │                              │
    └─ (Keeps local SQLite synced) │ (Updates dashboard)
```

### 4.3 Remote Management Scenario

```
Scenario: "We need today's sales data for a specific company"

Timeline:
  4:00 PM  Your support team opens dashboard
  4:01 PM  Selects "National Traders"
  4:02 PM  Clicks "Trigger Sync Now"
  4:03 PM  Agent (on MSME desktop) receives command
  4:04 PM  Agent syncs, dashboard shows progress
  4:05 PM  Data appears in cloud
  4:06 PM  You export report or feed to analytics engine

Zero involvement from MSME accountant.
```

---

## Part 5: Implementation Roadmap

### Phase 1: Immediate (Next 2 weeks)
- [ ] Create `dashboard/` sub-repo structure
- [ ] Set up Express.js + React skeleton
- [ ] Create PostgreSQL schema for clients + sync history
- [ ] Implement basic CRUD endpoints
- [ ] Deploy skeleton to staging

### Phase 2: Agent Communication (Weeks 15-19 per BRD)
- [ ] Implement WebSocket client in agent (`transport/websocket_client.py`)
- [ ] Implement HTTP long-poll fallback
- [ ] Connect dashboard to agent WebSocket
- [ ] Test real-time command execution

### Phase 3: Packaging (Weeks 23-24 per BRD)
- [ ] PyInstaller build pipeline
- [ ] Inno Setup installer
- [ ] EV code signing
- [ ] AV whitelisting submission
- [ ] Distribution infrastructure

### Phase 4: Testing & Launch
- [ ] Beta with 5 MSME companies
- [ ] Monitor agent telemetry
- [ ] Staged rollout (10% → 50% → 100%)

---

## Part 6: Security Considerations

### 6.1 Agent ↔ Cloud Communication
- ✅ HMAC-SHA256 signature on every request
- ✅ WSS (TLS encrypted WebSocket)
- ✅ JWT tokens for API authentication
- ✅ Rate limiting per client

### 6.2 Dashboard ↔ Agent
- ✅ Dashboard sends commands via cloud only (never direct access)
- ✅ Agent validates command signature before execution
- ✅ Audit log records all commands + responses
- ✅ Commands expire after 5 minutes if not executed

### 6.3 Data Protection
- ✅ SQLCipher (local SQLite encrypted)
- ✅ No financial data sent in telemetry (only hashes + counts)
- ✅ PII stripping from error logs
- ✅ Data residency in ap-south-1 (India)

---

## Part 7: FAQs

**Q: Why Node.js instead of Python Flask?**
A: Dashboard is a SaaS platform serving multiple clients. Node.js + React is industry standard for modern dashboards. Python agent stays separate (single responsibility).

**Q: Can MSME accountants see the dashboard?**
A: No. Dashboard is for YOUR support team only. MSMEs see:
  - Local tray icon (status)
  - Config wizard (first run)
  - Logs (if they ask support)

**Q: What if client's internet goes down?**
A: Agent keeps syncing locally (SQLCipher encrypted). Queue builds up. When internet returns, queued data syncs automatically.

**Q: How do we ensure EXE is trusted?**
A: Three layers:
  1. EV Code Signing (proves it's from you)
  2. AV Whitelisting (Microsoft, Quick Heal, K7, etc.)
  3. Smart screen reputation (builds after thousands of installs)

**Q: Can we update agent remotely?**
A: Yes. OTA updater is Phase 3 Week 17-18. Check cloud for new version, download, verify SHA256, restart service.

---

## Summary

| Component | Purpose | Tech | Timeline |
|-----------|---------|------|----------|
| **Agent EXE** | Sync data on MSME desktop | Python → PyInstaller | Phase 5 (Week 23-24) |
| **WebSocket API** | Cloud ↔ Agent communication | FastAPI + WebSockets | Phase 3 (Week 15-19) |
| **Dashboard** | Monitor & control agents | React + Express | Immediately (separate sub-repo) |
| **Code Signing** | Build trust | EV Cert | Phase 5 (Week 23) |
| **AV Whitelisting** | Avoid false positives | Manual submission | Phase 5 (Week 23-28) |

**Ready to start with dashboard sub-repo?**
