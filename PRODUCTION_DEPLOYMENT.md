# TallyBridge Dashboard - Production Deployment Guide

**Complete step-by-step deployment to AWS + Vercel**

Estimated time: **1-2 hours** for first-time setup

---

## Part 1: Create AWS Account (5-10 minutes)

### Step 1.1: Sign Up for AWS
1. Go to https://aws.amazon.com
2. Click "Create an AWS Account"
3. Enter:
   - Email address (use your Gmail or company email)
   - Password (strong password!)
   - AWS account name (e.g., "tallybridge-prod")
4. Verify email
5. Enter credit card (free tier = no charges if you stay within limits)
6. Verify phone number

### Step 1.2: Login to AWS Console
1. Go to https://console.aws.amazon.com
2. Sign in with your email and password
3. **Region:** Select **Asia Pacific (Mumbai) ap-south-1** (top right dropdown)
   - This keeps data in India per compliance requirements
   - All your services will be here

**Congratulations! AWS account is ready.** ✅

---

## Part 2: Create PostgreSQL Database on RDS (10 minutes)

### Step 2.1: Open RDS Console
1. In AWS Console, search for "RDS" (top search bar)
2. Click on "RDS"
3. Click "Create database"

### Step 2.2: Configure Database
Set these options:

```
Engine options:
  - Engine type: PostgreSQL
  - Version: PostgreSQL 14.7 (or latest 14.x)

Template:
  - Select "Free tier"

Settings:
  - DB instance identifier: tallybridge-postgres
  - Master username: postgres
  - Master password: <Create strong password, save it!>
  - Confirm password: <Repeat same password>

Instance configuration:
  - DB instance class: db.t3.micro (free tier)

Storage:
  - Storage type: General Purpose (gp3)
  - Allocated storage: 20 GB (free tier limit)
  - Storage autoscaling: DISABLED

Connectivity:
  - VPC: default
  - Public accessibility: YES (so your EC2 can connect)
  - Security group: Create new

Database authentication:
  - Database authentication: Password authentication

Initial database configuration:
  - Initial database name: tallybridge
  - DB parameter group: default.postgres14
  - Backup retention: 7 days
  - Encryption: NOT enabled (for free tier)
```

### Step 2.3: Create Database
1. Click "Create database"
2. **Wait 5-10 minutes** for creation (you'll see a progress circle)
3. Once available, click on the database name "tallybridge-postgres"
4. **Copy these details** and save in a safe place:
   - **Endpoint**: `tallybridge-postgres.xxxxx.ap-south-1.rds.amazonaws.com`
   - **Port**: 5432
   - **Username**: postgres
   - **Password**: <your password>
   - **Database**: tallybridge

**Your database is live!** ✅

---

## Part 3: Create EC2 Instance for Backend (15 minutes)

### Step 3.1: Open EC2 Console
1. Search for "EC2" in AWS Console
2. Click "EC2"
3. Click "Launch instances" (orange button)

### Step 3.2: Configure Instance

**Name and tags:**
```
Name: tallybridge-api
```

**Application and OS Images:**
- Select: **Ubuntu**
- Version: **Ubuntu Server 22.04 LTS free tier eligible**

**Instance type:**
```
t3.small (NOT t3.micro)
Reason: t3.micro would be too slow for Node.js
Free tier covers t3.small
```

**Key pair (login):**
```
Create new key pair:
  - Name: tallybridge-key
  - Type: RSA
  - Format: .pem (if you're on Mac/Linux) or .ppk (if you're on Windows/PuTTY)

IMPORTANT: Click "Create key pair" 
A file will download (e.g., tallybridge-key.pem)
SAVE THIS FILE in a safe location - you need it to SSH into the server!
```

**Network settings:**
```
Security group name: tallybridge-api-sg
Rules:
  - HTTP (port 80) - allow from anywhere
  - HTTPS (port 443) - allow from anywhere  
  - SSH (port 22) - allow from your IP (or anywhere for now)
  - Custom TCP 5000 - allow from anywhere (for API)
```

**Storage:**
```
Root volume size: 30 GB (free tier eligible)
```

### Step 3.3: Launch Instance
1. Review all settings
2. Click "Launch instance"
3. Wait 2-3 minutes for instance to start
4. You'll see: **Instance successfully launched!**
5. Click "View instances"

### Step 3.4: Get Your Server IP
1. Wait for instance state to show "running" (green)
2. Look for **Public IPv4 address** (e.g., `43.205.xxx.xxx`)
3. **Copy and save this IP** - you'll need it

**Your server is running!** ✅

---

## Part 4: Deploy Backend to EC2 (30-40 minutes)

### Step 4.1: Connect to Your Server

**On Windows:**
1. Download PuTTY: https://www.putty.org/
2. Install PuTTY
3. Open PuTTYgen
4. Load your key file (tallybridge-key.pem)
5. Save as private key (.ppk)
6. Open PuTTY
7. Host: `ec2-user@<your-public-ip>`
8. In "SSH > Auth", select your .ppk file
9. Click "Open"

**On Mac/Linux:**
```bash
# In Terminal
chmod 400 ~/path/to/tallybridge-key.pem
ssh -i ~/path/to/tallybridge-key.pem ubuntu@<your-public-ip>

# Example:
ssh -i ~/tallybridge-key.pem ubuntu@43.205.123.45
```

### Step 4.2: Update Server
```bash
# Once connected to your server:

sudo apt update
sudo apt upgrade -y

# Install Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Verify installation
node --version  # Should show v20.x.x
npm --version   # Should show 10.x.x
```

### Step 4.3: Clone Your Repository
```bash
# Install git
sudo apt install -y git

# Clone the dashboard backend
git clone https://github.com/shreyashnadage/tally-sync-agent.git
cd tally-sync-agent/dashboard/backend

# Check files
ls -la
```

### Step 4.4: Setup Environment Variables
```bash
# Create .env file
nano .env

# Paste this (replace with your RDS details):
```
```
NODE_ENV=production
PORT=5000
HOST=0.0.0.0
FRONTEND_URL=https://your-vercel-domain.vercel.app
DB_HOST=tallybridge-postgres.xxxxx.ap-south-1.rds.amazonaws.com
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your-rds-password
DB_NAME=tallybridge
JWT_SECRET=generate-random-secret-key-here
LOG_LEVEL=info
```

**To save:** Press `Ctrl+X`, then `Y`, then `Enter`

### Step 4.5: Install & Build
```bash
# Install dependencies
npm install

# Build the application
npm run build

# Check if dist folder was created
ls -la dist/
```

### Step 4.6: Install PM2 (Process Manager)
```bash
# Install PM2 globally
sudo npm install -g pm2

# Start the application
pm2 start dist/index.js --name tallybridge-api

# Check it's running
pm2 logs tallybridge-api

# Should see: "TallyBridge Dashboard Backend running on..."

# Make PM2 start on server reboot
pm2 startup
pm2 save
```

### Step 4.7: Test Your API
```bash
# From your local computer:

# Get your EC2 public IP (e.g., 43.205.123.45)
curl http://43.205.123.45:5000/health

# Should return:
# {"status":"ok","timestamp":"2024-06-24T..."}
```

**Your backend is live!** ✅

---

## Part 5: Deploy Frontend to Vercel (5 minutes)

### Step 5.1: Create Vercel Account
1. Go to https://vercel.com
2. Click "Sign Up"
3. Click "Continue with GitHub"
4. Authorize Vercel to access your GitHub
5. Done!

### Step 5.2: Configure Frontend for Production

On your local computer:

```bash
cd dashboard/frontend

# Create production .env
cp .env.example .env

# Edit .env to point to your backend:
nano .env
```

**Replace content with:**
```
VITE_API_URL=http://43.205.123.45:5000
```

Save and commit:
```bash
git add .env
git commit -m "Add production API URL"
git push origin master
```

### Step 5.3: Deploy to Vercel
```bash
# Install Vercel CLI
npm i -g vercel

# Login to Vercel
vercel login

# Deploy
cd dashboard/frontend
vercel

# When asked:
# - "Set up and deploy? Y"
# - "Which scope? Your Name"
# - "Link to existing project? N"
# - "Project name: tallybridge-dashboard"
# - "Framework: Vite"
# - "Root directory: ./"
# - "Build command: npm run build"
# - "Output directory: dist"
```

### Step 5.4: Update Backend URL
Once Vercel gives you a URL (e.g., `https://tallybridge-dashboard.vercel.app`):

1. SSH into your EC2 server:
```bash
ssh -i ~/tallybridge-key.pem ubuntu@43.205.123.45
```

2. Update the backend:
```bash
cd ~/tally-sync-agent/dashboard/backend
nano .env

# Change:
FRONTEND_URL=https://tallybridge-dashboard.vercel.app

# Save and restart
pm2 restart tallybridge-api
```

**Your frontend is live!** ✅

---

## Part 6: Test Production Deployment (5 minutes)

### Test 1: Check Dashboard
```
Open: https://tallybridge-dashboard.vercel.app
Should see: Dashboard page with "No agents connected yet"
```

### Test 2: Register Test Agent
```bash
curl -X POST http://43.205.123.45:5000/api/agents \
  -H "Content-Type: application/json" \
  -d '{
    "company_guid": "prod-test-001",
    "company_name": "National Traders",
    "api_key_hash": "hash123",
    "tally_version": "TallyPrime 4.x",
    "agent_version": "0.1.0"
  }'

# Should return:
# {"success":true,"client_id":"xxx-xxx","message":"Agent registered successfully"}
```

### Test 3: View on Dashboard
1. Refresh https://tallybridge-dashboard.vercel.app
2. You should see "National Traders" in the agents list
3. Click "View →" to see agent details

### Test 4: Send a Command
1. Click on agent
2. Click "Send Command"
3. Select "TRIGGER_SYNC"
4. Click "Send Command"
5. Should see success response

**Your production system is working!** ✅

---

## Part 7: Setup Domain (Optional, 10 minutes)

If you have a domain (e.g., yourdomain.com):

### For Frontend (Vercel):
1. In Vercel dashboard, go to Settings > Domains
2. Add domain: `dashboard.yourdomain.com`
3. Vercel gives you DNS instructions
4. Go to your domain registrar (GoDaddy, Namecheap, etc.)
5. Add the CNAME record Vercel gave you
6. Wait 5-10 minutes for DNS to propagate

### For Backend (EC2):
1. Go to your domain registrar
2. Create an A record:
   - Name: `api.yourdomain.com`
   - Value: `43.205.123.45` (your EC2 public IP)
3. Wait 5-10 minutes for DNS to propagate

Now you can access:
- Frontend: `https://dashboard.yourdomain.com`
- Backend: `http://api.yourdomain.com:5000`

---

## Part 8: Production Checklist

- [ ] AWS account created ✅
- [ ] RDS PostgreSQL running ✅
- [ ] EC2 instance running ✅
- [ ] Backend deployed and running ✅
- [ ] Frontend deployed on Vercel ✅
- [ ] Can access dashboard at Vercel URL ✅
- [ ] Can register test agents ✅
- [ ] Can send commands ✅
- [ ] Logs show no errors ✅

**You're in production!** 🎉

---

## Monitoring & Maintenance

### Check Backend Logs
```bash
# SSH into server
ssh -i ~/tallybridge-key.pem ubuntu@43.205.123.45

# View logs
pm2 logs tallybridge-api

# Restart if needed
pm2 restart tallybridge-api
```

### Monitor RDS Database
1. AWS Console → RDS → Databases
2. Click "tallybridge-postgres"
3. See CPU, storage, connections

### Monitor Vercel Frontend
1. Vercel dashboard → Select your project
2. See deployment status, logs, analytics

---

## Costs (Monthly)

```
EC2 t3.small:    ~₹400 (free tier eligible, pay after 1 year)
RDS PostgreSQL:  ~₹500 (free tier eligible, pay after 1 year)
Vercel:          FREE (up to 100GB bandwidth)
────────────────────────
Total first year: FREE
Year 2+:         ~₹900/month (very affordable)
```

**Free tier covers one year, starting from account creation.**

---

## Troubleshooting

### Backend won't start
```bash
# SSH into server
pm2 logs tallybridge-api

# Check for errors
# Common issues:
# - Wrong RDS password
# - RDS not accepting connections
# - Node.js not installed
```

### Frontend can't connect to API
1. Check VITE_API_URL in Vercel settings
2. Make sure backend EC2 IP is public
3. Check security group allows port 5000

### RDS connection refused
1. Verify security group allows port 5432
2. Verify username/password are correct
3. Check database is in "available" state

---

## Next Steps

### When Agent Phase 3 is Done
Agent will connect to dashboard automatically via WebSocket:
- Agent registers: `POST /api/agents`
- Agent sends heartbeat: Every 25 seconds
- Dashboard shows live agents
- Commands execute instantly

No additional configuration needed!

### Before MSMEs Use It
- [ ] Test with 5 internal agents
- [ ] Verify data sync accuracy
- [ ] Check error handling
- [ ] Load test (simulate 100 agents)
- [ ] Security audit
- [ ] Compliance review

---

## Support

If you get stuck:
1. Check logs: `pm2 logs tallybridge-api`
2. Check AWS console for error messages
3. Verify all environment variables are correct
4. Restart services: `pm2 restart tallybridge-api`

You've got a **production-grade SaaS platform** live! 🚀

**Congratulations!**
