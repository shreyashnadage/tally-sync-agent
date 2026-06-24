# TallyBridge Architecture: Complete System Diagram

## System Overview

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          TallyBridge Complete System                          │
└──────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────┐          ┌──────────────────────────────────┐
│     MSME Desktop (Client)        │          │    Your Cloud Platform           │
│                                 │          │   (Your Own Infrastructure)      │
│  ┌───────────────────────────┐  │          │                                  │
│  │  TallyBridge Agent EXE    │  │          │  ┌─────────────────────────┐    │
│  │  (Windows Service)        │  │          │  │  FastAPI Backend        │    │
│  │                           │  │          │  │  (api.yourdomain.com)   │    │
│  │  ┌──────────────────────┐ │  │          │  │                         │    │
│  │  │ Tally Prime/ERP9     │ │  │          │  │ - Agent endpoints       │    │
│  │  │ (port 9000)          │ │  │          │  │ - WebSocket server      │    │
│  │  └──────────┬───────────┘ │  │          │  │ - Command queue         │    │
│  │             │ XML API     │  │          │  │ - Sync history DB       │    │
│  │             │             │  │          │  └──────────┬──────────────┘    │
│  │  ┌──────────▼──────────┐  │  │          │             │ WSS (WebSocket)   │
│  │  │ XML Parser          │  │  │          │             │                   │
│  │  │ - Multi-encoding    │  │  │          │  ┌──────────▼──────────────┐   │
│  │  │ - Fault tolerance   │  │  │          │  │ PostgreSQL Database     │   │
│  │  │ - NFC normalize     │  │  │          │  │                         │   │
│  │  └──────────┬──────────┘  │  │          │  │ - clients               │   │
│  │             │             │  │          │  │ - sync_history          │   │
│  │  ┌──────────▼──────────┐  │  │          │  │ - agent_health          │   │
│  │  │ SQLCipher SQLite    │  │  │          │  │ - inbound_commands      │   │
│  │  │ (Encrypted Local DB)│  │  │          │  └─────────────────────────┘   │
│  │  │                     │  │  │          │                                  │
│  │  │ Tables:             │  │  │          │  ┌─────────────────────────┐    │
│  │  │ - config            │  │  │          │  │ Node.js Dashboard       │    │
│  │  │ - sync_state        │  │  │          │  │ (dashboard.yourdomain)  │    │
│  │  │ - outbound_queue    │  │  │          │  │                         │    │
│  │  │ - inbound_commands  │  │  │          │  │ Frontend: React + TS    │    │
│  │  │ - audit_log         │  │  │          │  │ Backend: Express + TS   │    │
│  │  │ - company_info      │  │  │          │  │                         │    │
│  │  │ - migration_history │  │  │          │  │ Pages:                  │    │
│  │  └──────────┬──────────┘  │  │          │  │ - Agent Overview        │    │
│  │             │             │  │          │  │ - Agent Details         │    │
│  │  ┌──────────▼──────────┐  │  │          │  │ - Sync History          │    │
│  │  │ WebSocket Client    │  │  │          │  │ - Send Commands         │    │
│  │  │ (Phase 3: Week 15)  │  │  │          │  │ - Analytics             │    │
│  │  │                     │  │  │          │  └────────┬────────────────┘    │
│  │  │ Connects to cloud   │  │  │          │           │                     │
│  │  │ Sends: heartbeat    │  │  │          │  WebSocket/HTTP connection      │
│  │  │         status      │◄─┼──┼──WSS───────────────────────────────────┤   │
│  │  │         sync data   │  │  │          │           │                     │
│  │  │ Receives: commands  │  │  │          │           │                     │
│  │  └─────────────────────┘  │  │          │           │                     │
│  │                           │  │          │  (Real-time command execution)   │
│  │  ┌─────────────────────┐  │  │          │                                  │
│  │  │ Tray Icon (Status)  │  │  │          │  ┌─────────────────────────┐    │
│  │  │ - Green: Active     │  │  │          │  │ Redis Streams           │    │
│  │  │ - Yellow: Syncing   │  │  │          │  │ (Command Queue)         │    │
│  │  │ - Red: Error        │  │  │          │  └─────────────────────────┘    │
│  │  └─────────────────────┘  │  │          │                                  │
│  └───────────────────────────┘  │          └──────────────────────────────────┘
│                                 │
│  Installed via:                 │
│  Setup.exe (EV signed)          │
│  + AV whitelisting              │
│                                 │
└─────────────────────────────────┘
```

---

## Communication Flows

### Flow 1: Scheduled Sync (Every 4 hours)

```
Agent Desktop                    Cloud API                   Database
    │                               │                            │
    ├─► (Check sync window)         │                            │
    │   (Check schedule)            │                            │
    │                               │                            │
    ├─► Read company GUID           │                            │
    ├─► Query Tally XML API         │                            │
    ├─► Parse response (multi-enc)  │                            │
    ├─► Calculate ALTERID changes   │                            │
    │                               │                            │
    ├───────── WebSocket ─────────►│                            │
    │   HEARTBEAT + sync data       │                            │
    │                               ├───── INSERT/UPSERT ───────►│
    │                               │   (vouchers, ledgers)      │
    │                               │                            │
    │◄──────── WSS ACK ─────────────┤                            │
    │   (status: DELIVERED)         │                            │
    │                               │                            │
    └─ Update local sync_state      └─ Update PostgreSQL         │
       (next sync time)                (last_sync_at)            │
```

### Flow 2: Remote Command (Dashboard → Agent)

```
Dashboard (Your Team)        Cloud API         Redis         Agent Desktop
    │                          │               Queue               │
    ├─ Click "Trigger Sync"    │                │                  │
    │                          │                │                  │
    ├─ POST /commands/send ───►│                │                  │
    │   { command_type:        │                │                  │
    │     "TRIGGER_SYNC",      │                │                  │
    │     agent_id: "..." }    │                │                  │
    │                          ├─ PUSH to ────►│                  │
    │                          │ client stream  │                  │
    │                          │                │                  │
    │                          │                │◄─ Agent polls ───│
    │                          │                │  (every 30s)     │
    │                          │                │                  │
    │                          │                │                  │◄─ POP command
    │                          │                │                  │
    │                          │                │                  ├─ Validate HMAC
    │                          │                │                  ├─ Execute sync
    │                          │                │                  │
    │◄────── GET status ───────┤                │  RESPONSE ──────►│
    │ { status: "SYNCING"      │◄────────────────────────────────┤
    │   queue_depth: 0 }       │                                   │
    │                          │                                   │
    │ (shows live progress)    │                                   │
```

### Flow 3: Error & Recovery

```
Agent Desktop              Cloud API           Dashboard
    │                          │                  │
    ├─ Tally offline           │                  │
    │  (port 9000 no response) │                  │
    │                          │                  │
    ├──────► HEARTBEAT ───────►│                  │
    │        status: "TALLY_OFFLINE"              │
    │                          ├──► Alert ───────►│
    │                          │  (Tally down)    │
    │                          │                  │ ◄─ Support alerted
    │                          │                  │    Check MSME
    │                          │                  │
    │ (Keeps trying every 30s) │                  │
    │                          │                  │
    └─ Tally comes online      │                  │
       Port 9000 responds       │                  │
    │                          │                  │
    ├──────► HEARTBEAT ───────►│                  │
    │        status: "ACTIVE"  │                  │
    │        recovered: true   ├──► Clear ───────►│
    │                          │    Alert         │
    │                          │                  │
    └─ Normal sync resumes     │                  │
```

---

## Data Flow: Complete Sync Cycle

```
Day 1: 4:00 AM (Sync scheduled)
┌────────────────────────────────────────────────────────────────┐

Agent reads from Tally:
  1. MAX(ALTERID) from last sync_state
  2. Query: "All records where ALTERID > {max} AND date >= {lookback}"
  3. XML response includes: 50 new sales vouchers + 3 ledger updates

Agent enriches data:
  4. Parse XML (handle encoding, normalize unicode)
  5. Generate surrogate keys for ERP 9 records
  6. Validate amounts, party names, ledger references
  7. Store in local outbound_queue (encrypted)

Agent sends to cloud:
  8. Package into HTTPS POST with HMAC signature
  9. Cloud receives → INSERT INTO vouchers, ledgers
  10. Cloud response: { status: "DELIVERED", received_count: 53 }

Agent updates state:
  11. Update sync_state: max_alterid = 12547, last_sync_at = now()
  12. Write audit_log: { event: "SYNC_COMPLETE", record_count: 53, duration: "3m22s" }
  13. Clear outbound_queue (mark as DELIVERED)

Dashboard updates:
  14. PostgreSQL row updated: last_sync_at = now()
  15. Dashboard shows: "Last sync: just now (53 records in 3m22s)"

If error occurs (e.g., network timeout):
  14. outbound_queue row stays PENDING
  15. Retry loop tries every 60 seconds
  16. After 24 hours: mark STALE_PENDING, alert support
  17. When network returns: auto-resume from checkpoint (zero data loss)

└────────────────────────────────────────────────────────────────┘
```

---

## Deployment Architecture

### Option A: SaaS (Recommended for scaling)

```
Your Cloud Infrastructure (AWS)
┌────────────────────────────────────────┐
│                                        │
│  Region: ap-south-1 (Mumbai, India)   │
│                                        │
│  ┌──────────────────────────────────┐ │
│  │  EC2 Instance                    │ │
│  │  - FastAPI (Agent API)           │ │
│  │  - Express.js (Dashboard API)    │ │
│  │  - WebSocket Server              │ │
│  │  t3.medium (2vCPU, 4GB RAM)      │ │
│  └──────────────────────────────────┘ │
│                                        │
│  ┌──────────────────────────────────┐ │
│  │  RDS PostgreSQL                  │ │
│  │  - clients                       │ │
│  │  - sync_history                  │ │
│  │  - audit_logs                    │ │
│  │  t3.small (1vCPU, 2GB)           │ │
│  └──────────────────────────────────┘ │
│                                        │
│  ┌──────────────────────────────────┐ │
│  │  ElastiCache (Redis)             │ │
│  │  - Command queue                 │ │
│  │  - Cache                         │ │
│  │  cache.t3.micro                  │ │
│  └──────────────────────────────────┘ │
│                                        │
│  ┌──────────────────────────────────┐ │
│  │  S3 Bucket                       │ │
│  │  - Agent installers (Setup.exe)  │ │
│  │  - Logs + backups                │ │
│  └──────────────────────────────────┘ │
│                                        │
│  ┌──────────────────────────────────┐ │
│  │  GlitchTip (Error monitoring)    │ │
│  │  - Agent telemetry               │ │
│  │  - Stack traces (PII-free)       │ │
│  └──────────────────────────────────┘ │
│                                        │
└────────────────────────────────────────┘

Frontend Deployment:
- Vercel (Next.js) or Netlify (React)
- CDN: CloudFront
- Domain: dashboard.yourdomain.com
```

### Option B: Self-Hosted (If enterprise requirement)

```
Your On-Premise Server (for large enterprises)
┌────────────────────────────────┐
│  Docker Compose                │
│                                │
│  ┌──────────────────────────┐  │
│  │  FastAPI Container       │  │
│  └──────────────────────────┘  │
│  ┌──────────────────────────┐  │
│  │  PostgreSQL Container    │  │
│  └──────────────────────────┘  │
│  ┌──────────────────────────┐  │
│  │  Redis Container         │  │
│  └──────────────────────────┘  │
│  ┌──────────────────────────┐  │
│  │  GlitchTip Container     │  │
│  └──────────────────────────┘  │
│                                │
│  docker-compose.yml auto-starts│
│  all containers on reboot      │
└────────────────────────────────┘
```

---

## Timeline: From Now to Client Beta

```
┌─────────────────────────────────────────────────────────────┐
│ IMMEDIATE (Next 2 weeks)                                    │
├─────────────────────────────────────────────────────────────┤
│ □ Create dashboard/ sub-repo                               │
│ □ Express.js + React skeleton                              │
│ □ PostgreSQL schema (clients, sync_history, audit)         │
│ □ Basic CRUD endpoints                                     │
│ □ Stub WebSocket connection (for testing)                  │
│ Goal: Dashboard skeleton working, can list agents          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ PHASE 3 (Weeks 15-19 per BRD)                             │
├─────────────────────────────────────────────────────────────┤
│ □ Implement agent WebSocket client                         │
│ □ Real WebSocket communication (cloud ↔ agent)            │
│ □ Command execution (TRIGGER_SYNC, FETCH_VOUCHER, etc.)   │
│ □ Real-time updates in dashboard                          │
│ Goal: Live remote management working                       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ PHASE 5 (Weeks 23-24)                                      │
├─────────────────────────────────────────────────────────────┤
│ □ PyInstaller build (tallybridge_agent.exe)               │
│ □ Inno Setup installer (Setup.exe)                        │
│ □ EV code signing                                         │
│ □ AV whitelisting submission                              │
│ Goal: Distributable, signed EXE ready                      │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ WEEKS 25-27: BETA TESTING                                  │
├─────────────────────────────────────────────────────────────┤
│ □ Recruit 5 MSME pilot companies                          │
│ □ Each MSME: clean Windows install, Setup.exe run         │
│ □ Monitor via dashboard                                    │
│ □ Trigger syncs, check data accuracy                      │
│ □ Gather feedback on UX                                    │
│ Goal: Production-ready, 5 companies validating             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ WEEK 28: GA RELEASE                                         │
├─────────────────────────────────────────────────────────────┤
│ □ Staged rollout: 10% new clients                         │
│ □ Scale to 50% after 48 hours (no P0 bugs)               │
│ □ Scale to 100% after 7 days                              │
│ Goal: Live production, all systems operational             │
└─────────────────────────────────────────────────────────────┘
```

---

## Cost Estimate (Monthly, ap-south-1)

```
Infrastructure:
  EC2 (t3.medium)          ₹1,500/month
  RDS PostgreSQL           ₹1,200/month
  ElastiCache Redis        ₹800/month
  S3 + CloudFront          ₹500/month
  GlitchTip (self-hosted)  ₹400/month
  ─────────────────────────────────
  Subtotal                 ₹4,400/month

  (Scales easily: t3.small for first 500 agents, upgrade to t3.large at 5000+)

Code Signing:
  EV Certificate (annual)  ₹20,000/year (₹1,667/month)

Domain & Email:
  Domain + DNS             ₹2,000/year

Total Estimated: ₹6,000-7,000/month + EV cert + domain
(Very affordable for MSMEs segment profitability)
```

---

## Success Criteria (Week 28)

✅ Agent EXE running on 5 MSME desktops  
✅ All agents showing ACTIVE in dashboard  
✅ Remote sync triggers working (cloud → agent)  
✅ Sync data accurate (50 random vouchers verified per company)  
✅ Zero data loss on network failures  
✅ Dashboard responsive with live updates  
✅ AV whitelisted on 4+ vendors  
✅ Support team can manage agents remotely  
✅ MSME can't see dashboard (by design)  
✅ All logs encrypted, no financial data in telemetry  

**Then: Ready for larger rollout!**
