# TallyBridge Production Deployment Checklist

## 📋 Complete Step-by-Step Deployment

Follow these steps in order. Estimated time: **1-2 hours**

---

## ✅ Phase 1: AWS Account Setup (10 minutes)

- [ ] **Step 1:** Go to https://aws.amazon.com
- [ ] **Step 2:** Click "Create an AWS Account"
- [ ] **Step 3:** Fill in:
  - Email address
  - Strong password
  - Account name: `tallybridge-prod`
- [ ] **Step 4:** Verify email address
- [ ] **Step 5:** Enter credit card (free tier = no charges for first year)
- [ ] **Step 6:** Verify phone number
- [ ] **Step 7:** Login to AWS Console: https://console.aws.amazon.com
- [ ] **Step 8:** Change region to **Asia Pacific (Mumbai) ap-south-1** (top right)

**Result:** AWS account ready ✅

---

## ✅ Phase 2: Create PostgreSQL Database (10 minutes)

- [ ] **Step 1:** In AWS Console, search for "RDS"
- [ ] **Step 2:** Click "RDS"
- [ ] **Step 3:** Click "Create database"
- [ ] **Step 4:** Select "Free tier" template
- [ ] **Step 5:** Configure:
  - DB instance identifier: `tallybridge-postgres`
  - Master username: `postgres`
  - Master password: `<Create strong password>`
  - DB instance class: `db.t3.micro`
  - Initial database name: `tallybridge`
  - Public accessibility: `YES`
- [ ] **Step 6:** Click "Create database"
- [ ] **Step 7:** Wait 5-10 minutes for creation
- [ ] **Step 8:** Once created, copy and save:
  - **Endpoint:** (e.g., `tallybridge-postgres.xxxxx.ap-south-1.rds.amazonaws.com`)
  - **Username:** `postgres`
  - **Password:** (your password)
  - **Database:** `tallybridge`

**Result:** PostgreSQL database live ✅

---

## ✅ Phase 3: Create EC2 Server (15 minutes)

- [ ] **Step 1:** In AWS Console, search for "EC2"
- [ ] **Step 2:** Click "EC2"
- [ ] **Step 3:** Click "Launch instances"
- [ ] **Step 4:** Configure:
  - Name: `tallybridge-api`
  - OS: **Ubuntu Server 22.04 LTS**
  - Instance type: **t3.small**
- [ ] **Step 5:** Create key pair:
  - Name: `tallybridge-key`
  - Type: `RSA`
  - Format: `.pem` (Mac/Linux) or `.ppk` (Windows)
  - **SAVE THE FILE!** (you'll need it to login)
- [ ] **Step 6:** Security group:
  - Allow HTTP (port 80)
  - Allow HTTPS (port 443)
  - Allow SSH (port 22)
  - Allow Custom TCP 5000
- [ ] **Step 7:** Storage: 30 GB
- [ ] **Step 8:** Click "Launch instance"
- [ ] **Step 9:** Wait 2-3 minutes for instance to start
- [ ] **Step 10:** Copy and save your **Public IPv4 address** (e.g., `43.205.xxx.xxx`)

**Result:** EC2 server running ✅

---

## ✅ Phase 4: Deploy Backend to EC2 (35 minutes)

### Part A: Connect to Server (5 minutes)

**If you're on Mac/Linux:**
```bash
chmod 400 ~/path/to/tallybridge-key.pem
ssh -i ~/path/to/tallybridge-key.pem ubuntu@<your-public-ip>
```

**If you're on Windows:**
- Download PuTTY
- Convert key with PuTTYgen
- Connect using PuTTY

- [ ] **Connected to server** ✅

### Part B: Install Software (5 minutes)

Once connected to your server, run:

```bash
sudo apt update
sudo apt upgrade -y
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs git
node --version  # Verify
```

- [ ] **Node.js installed** ✅

### Part C: Clone Repository (5 minutes)

```bash
git clone https://github.com/shreyashnadage/tally-sync-agent.git
cd tally-sync-agent/dashboard/backend
ls -la
```

- [ ] **Repository cloned** ✅

### Part D: Setup Environment (5 minutes)

```bash
nano .env
```

Paste this (replace with YOUR RDS details):
```
NODE_ENV=production
PORT=5000
HOST=0.0.0.0
FRONTEND_URL=https://tallybridge-dashboard.vercel.app
DB_HOST=tallybridge-postgres.xxxxx.ap-south-1.rds.amazonaws.com
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your-rds-password
DB_NAME=tallybridge
JWT_SECRET=generate-any-random-string-here
LOG_LEVEL=info
```

Save: `Ctrl+X` → `Y` → `Enter`

- [ ] **.env created** ✅

### Part E: Install & Build (15 minutes)

```bash
npm install
npm run build
```

Wait for completion.

- [ ] **Build successful** ✅

### Part F: Start with PM2 (2 minutes)

```bash
sudo npm install -g pm2
pm2 start dist/index.js --name tallybridge-api
pm2 logs tallybridge-api
```

Should see: `TallyBridge Dashboard Backend running on http://0.0.0.0:5000`

```bash
pm2 startup
pm2 save
```

- [ ] **Backend running** ✅

### Part G: Test Backend (1 minute)

From your local computer:
```bash
curl http://<your-ec2-ip>:5000/health
```

Should return: `{"status":"ok","timestamp":"..."}`

- [ ] **Backend tested** ✅

**Result:** Backend live at `http://<your-ec2-ip>:5000` ✅

---

## ✅ Phase 5: Deploy Frontend to Vercel (10 minutes)

### Part A: Prepare Frontend

On your local computer:

```bash
cd dashboard/frontend
cp .env.example .env
nano .env
```

Change:
```
VITE_API_URL=http://<your-ec2-ip>:5000
```

Save and commit:
```bash
git add .env
git commit -m "Add production API URL"
git push origin master
```

- [ ] **Environment updated** ✅

### Part B: Create Vercel Account

- [ ] **Step 1:** Go to https://vercel.com
- [ ] **Step 2:** Click "Sign Up"
- [ ] **Step 3:** "Continue with GitHub"
- [ ] **Step 4:** Authorize Vercel

**Result:** Vercel account ready ✅

### Part C: Deploy to Vercel

```bash
npm i -g vercel
vercel login
vercel
```

When asked:
- Set up and deploy? **Y**
- Scope: **Your Name**
- Link to existing project? **N**
- Project name: **tallybridge-dashboard**
- Framework: **Vite**
- Output directory: **dist**

Wait for deployment to complete.

- [ ] **Frontend deployed** ✅

### Part D: Get Vercel URL

Vercel will show you a URL like:
```
https://tallybridge-dashboard.vercel.app
```

Copy this URL.

- [ ] **Vercel URL: _________________** (save this)

---

## ✅ Phase 6: Update Backend CORS

SSH back into your EC2 server:

```bash
cd ~/tally-sync-agent/dashboard/backend
nano .env
```

Change:
```
FRONTEND_URL=https://tallybridge-dashboard.vercel.app
```

Save and restart:
```bash
pm2 restart tallybridge-api
pm2 logs tallybridge-api
```

- [ ] **CORS updated** ✅

---

## ✅ Phase 7: Test Production (5 minutes)

### Test 1: Dashboard Loads

- [ ] Open: `https://tallybridge-dashboard.vercel.app`
- [ ] Should see: Dashboard page with stats
- [ ] Should see: Empty agents list

### Test 2: Register Agent

From your local computer:
```bash
curl -X POST http://<your-ec2-ip>:5000/api/agents \
  -H "Content-Type: application/json" \
  -d '{
    "company_guid": "test-001",
    "company_name": "National Traders",
    "api_key_hash": "hash123",
    "tally_version": "TallyPrime 4.x",
    "agent_version": "0.1.0"
  }'
```

Should return success.

- [ ] **Agent registered** ✅

### Test 3: See on Dashboard

- [ ] Refresh dashboard
- [ ] Should see "National Traders" in list
- [ ] Click "View →"
- [ ] Should see agent details

### Test 4: Send Command

- [ ] Click on agent
- [ ] Click "Send Command"
- [ ] Select "TRIGGER_SYNC"
- [ ] Click "Send Command"
- [ ] Should see success response

- [ ] **All tests passed** ✅

---

## ✅ Production URLs

Save these:

```
Frontend Dashboard: https://tallybridge-dashboard.vercel.app
Backend API:       http://<your-ec2-ip>:5000
Database:          tallybridge-postgres.xxxxx.ap-south-1.rds.amazonaws.com

EC2 SSH:           ssh -i ~/tallybridge-key.pem ubuntu@<your-ec2-ip>
AWS Console:       https://console.aws.amazon.com
Vercel Dashboard:  https://vercel.com/dashboard
```

---

## ✅ Post-Deployment

### Daily Monitoring

- [ ] Check backend logs:
  ```bash
  ssh -i ~/tallybridge-key.pem ubuntu@<your-ec2-ip>
  pm2 logs tallybridge-api
  ```

- [ ] Check AWS RDS status (AWS Console → RDS)
- [ ] Check Vercel deployments (Vercel Dashboard)

### Before Agents Go Live

- [ ] Test with 5 internal agents
- [ ] Verify sync data accuracy
- [ ] Load test (100 agents)
- [ ] Security audit
- [ ] Compliance review

---

## ✅ Costs Summary

```
First Year:    FREE (AWS free tier)
Year 2+:       ~₹900/month (t3.small + RDS)
```

---

## 🎉 Congratulations!

You now have a **production-grade SaaS platform**:
- ✅ Frontend on Vercel (global CDN)
- ✅ Backend on AWS EC2 (auto-restart)
- ✅ Database on AWS RDS (automated backups)
- ✅ Monitoring & logging ready
- ✅ Ready for real agents

**Next:** When Phase 3 agent WebSocket is done, agents will connect automatically!

---

## Need Help?

1. Check logs: `pm2 logs tallybridge-api`
2. Check AWS console for errors
3. Verify all environment variables
4. Restart if needed: `pm2 restart tallybridge-api`

**You're ready to go live!** 🚀
