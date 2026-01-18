# BlueRadar Troubleshooting Prompt for Claude

**Copy this entire prompt and paste it to Claude (Claude Code or Claude.ai)**

---

Hi Claude, I'm having issues with the BlueRadar Social Media Intelligence System. Here's the complete context:

## 🎯 What This System Does

BlueRadar is a real-time social media monitoring system for marine disasters. It:

1. **Generates fake social media posts** in 9 Indian languages (English, Hindi, Tamil, Telugu, Kannada, Malayalam, Bengali, Gujarati, Marathi)
2. **Simulates disasters** (tsunami, cyclone, flooding, oil spill, earthquake) at 100+ Indian coastal locations
3. **Creates unique usernames** dynamically (1000s of combinations)
4. **Displays posts one-by-one** on a real-time dashboard with animations
5. **Detects and alerts** on high-priority disaster posts
6. **Stores data** in MongoDB Atlas database

## 🏗️ System Architecture

```
BlueRadar (Port 8001)
├── FastAPI Backend (api/main.py)
├── MongoDB Atlas (Cloud Database)
├── Enhanced Feed Generator (api/enhanced_feed.py)
├── Real-time Dashboard (enhanced_dashboard.html)
└── WebSocket Alerts System
```

## 📍 Current System State

**Repository:** https://github.com/prelekar0/CoastGuardians-social-media-intelligence

**Working Components:**
- ✅ Enhanced multi-language feed with 9 languages
- ✅ Dynamic username generation (1000s of combinations)
- ✅ 100+ coastal locations across India
- ✅ One-by-one post display with animations
- ✅ Real-time alerts system
- ✅ Location consistency (post text matches metadata)
- ✅ Database cleanup endpoint

**Port:** 8001
**Database:** MongoDB Atlas
**Connection String:** See .env file

## 🐛 Common Issues & Solutions

### Issue 1: MongoDB Connection Errors (SSL Handshake Failed)

**Error Message:**
```
SSL handshake failed: [SSL: TLSV1_ALERT_INTERNAL_ERROR] tlsv1 alert internal error
❌ Error getting health metrics: SSL handshake failed
```

**Root Cause:** IP address not whitelisted in MongoDB Atlas

**Solution:**
1. Go to MongoDB Atlas: https://cloud.mongodb.com/
2. Login to your account
3. Click on your cluster
4. Go to "Network Access" (left sidebar)
5. Click "ADD IP ADDRESS"
6. Select "ALLOW ACCESS FROM ANYWHERE" or add `0.0.0.0/0`
7. Click "Confirm"
8. Wait 1-2 minutes
9. Restart system: `./stop.sh && ./run.sh`

### Issue 2: System Not Starting

**Check:**
```bash
# Check if port 8001 is already in use
lsof -i :8001

# Kill existing processes
pkill -f "uvicorn api.main:app"

# Start fresh
./run.sh
```

### Issue 3: Dashboard Not Loading

**Solution:**
```bash
# Open dashboard manually
open http://localhost:8001/dashboard

# Or check if server is running
curl http://localhost:8001/health
```

### Issue 4: No Posts Appearing

**Cause:** Feed not started

**Solution:**
```bash
# Start enhanced feed
curl -X POST http://localhost:8001/feed/start/enhanced \
  -H "Content-Type: application/json" \
  -d '{"post_interval": 8, "disaster_probability": 0.3}'

# Check feed status
curl http://localhost:8001/feed/status
```

### Issue 5: Posts Not in Multiple Languages

**Check Configuration:**
```bash
# Verify feed is using all languages
curl http://localhost:8001/feed/status

# Should show: languages_supported: [9 languages]
```

### Issue 6: Location Mismatch

**Status:** ✅ FIXED in commit e5431e2

The bug where post text showed one location (e.g., "Jamnagar") but metadata showed different location (e.g., "Harnai") has been fixed.

**File Fixed:** `api/enhanced_feed.py:412`

### Issue 7: Slow Startup

**Status:** ✅ FIXED - MongoDB timeout reduced from 30s to 5s

**File Fixed:** `api/database.py:37-39`

### Issue 8: Dashboard Counters Not Working

**Status:** ✅ FIXED - Counters now accumulate properly

**File Fixed:** `enhanced_dashboard.html` - Added Set tracking for displayed posts

### Issue 9: Multiple Posts Appearing at Once

**Status:** ✅ FIXED - Posts now appear one-by-one with animations

**File Fixed:** `enhanced_dashboard.html` - Added one-by-one display logic

## 🔧 Environment Setup Issues

### Missing Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Key packages needed:
# - fastapi
# - uvicorn
# - pymongo
# - python-dotenv
# - pydantic
```

### .env File Configuration

Your `.env` should look like this:

```bash
# MongoDB Configuration (REQUIRED)
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/?appName=yourapp
MONGODB_DATABASE=coastaguardian_socailmedia_db

# API Configuration
API_HOST=0.0.0.0
API_PORT=8001
DEBUG=True

# Optional: Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
```

### Python Version

**Required:** Python 3.11+

```bash
# Check Python version
python --version

# Should be 3.11 or higher
```

## 🚀 How to Start the System

### Method 1: Using run.sh (Recommended)

```bash
# Make executable
chmod +x run.sh stop.sh

# Start system
./run.sh

# System will:
# 1. Kill existing processes on port 8001
# 2. Start FastAPI server
# 3. Open dashboard automatically
# 4. Start enhanced feed
```

### Method 2: Manual Start

```bash
# Activate virtual environment
source venv/bin/activate

# Start server
python -m uvicorn api.main:app --host 0.0.0.0 --port 8001

# In another terminal, start feed
curl -X POST http://localhost:8001/feed/start/enhanced \
  -H "Content-Type: application/json" \
  -d '{"post_interval": 8, "disaster_probability": 0.3}'
```

### Method 3: With Auto-reload (Development)

```bash
uvicorn api.main:app --reload --port 8001
```

## 📊 Testing Commands

```bash
# 1. Health Check
curl http://localhost:8001/health

# Expected: {"status": "healthy", ...}

# 2. Check Feed Status
curl http://localhost:8001/feed/status

# Expected: {"feed_running": true, ...}

# 3. Get Recent Posts
curl http://localhost:8001/feed/enhanced?limit=10

# Expected: {"posts": [...], "count": 10}

# 4. Get Active Alerts
curl http://localhost:8001/alerts/active

# Expected: {"alerts": [...], "count": X}

# 5. Start Enhanced Feed
curl -X POST http://localhost:8001/feed/start/enhanced \
  -H "Content-Type: application/json" \
  -d '{"post_interval": 5, "disaster_probability": 0.4}'

# Expected: {"status": "started", ...}
```

## 🗂️ Key Files & What They Do

### api/main.py
- FastAPI application entry point
- All API endpoints defined here
- Handles HTTP requests

### api/enhanced_feed.py
- Multi-language post generator
- Dynamic username creation
- 100+ coastal locations
- 20-30+ post templates per language
- Alert detection logic

### api/database.py
- MongoDB Atlas connection
- Database operations (insert, query, update)
- Connection pooling with 5s timeouts

### enhanced_dashboard.html
- Real-time monitoring UI
- WebSocket connection to backend
- One-by-one post display
- Live counters and animations

### api/models.py
- Pydantic data models
- Request/response schemas

### run.sh
- System startup script
- Kills existing processes
- Starts server on port 8001
- Opens dashboard

### stop.sh
- Stops all BlueRadar processes
- Cleans up port 8001

## 🌐 API Endpoints

### Core Endpoints

- `GET /dashboard` - Open dashboard
- `GET /health` - Health check
- `POST /feed/start/enhanced` - Start feed
- `POST /feed/stop` - Stop feed
- `GET /feed/status` - Feed status
- `GET /feed/enhanced` - Get posts
- `GET /alerts/active` - Active alerts
- `POST /database/cleanup` - Clean database

### Full API Documentation

- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc

## 🔍 Debugging Steps

### Step 1: Check Logs

```bash
# View real-time logs
tail -f /tmp/blueradar.log  # If logging enabled

# Or check terminal output
```

### Step 2: Check Process

```bash
# Check if server is running
ps aux | grep uvicorn

# Check port
lsof -i :8001
```

### Step 3: Test MongoDB Connection

```bash
# Test connection from Python
python -c "from pymongo import MongoClient; import os; from dotenv import load_dotenv; load_dotenv(); client = MongoClient(os.getenv('MONGODB_URI')); print('Connected:', client.server_info())"
```

### Step 4: Check Network

```bash
# Test if MongoDB Atlas is reachable
ping ac-u5a8mha-shard-00-00.wwljow9.mongodb.net

# Check DNS resolution
nslookup ac-u5a8mha-shard-00-00.wwljow9.mongodb.net
```

## 📝 What to Tell Claude

**Copy and paste this when asking Claude for help:**

---

"Hi Claude, I'm running the BlueRadar Social Media Intelligence System and encountering issues.

**System Details:**
- Port: 8001
- Python Version: [your version]
- OS: [macOS/Linux/Windows]
- MongoDB: MongoDB Atlas (cloud)

**Error Message:**
[Paste your exact error message here]

**What I've Tried:**
[List what you've already attempted]

**Expected Behavior:**
[What should happen]

**Actual Behavior:**
[What actually happens]

**Logs:**
[Paste relevant error logs]

Please help me diagnose and fix this issue."

---

## 🎯 Expected System Behavior

When working correctly:

1. **System starts in ~5 seconds**
2. **Dashboard opens automatically**
3. **Posts appear one at a time** every 8 seconds
4. **9 different languages** rotate
5. **100+ different locations** appear
6. **Unique usernames** for each post
7. **30% disaster posts** (configurable)
8. **Counters accumulate** correctly
9. **Alerts shown** for high-priority disasters
10. **Smooth animations** when posts appear

## 🆘 Emergency Reset

If nothing works:

```bash
# 1. Stop everything
./stop.sh
pkill -f python
pkill -f uvicorn

# 2. Clean database
curl -X POST http://localhost:8001/database/cleanup

# 3. Remove cache
rm -rf __pycache__
rm -rf api/__pycache__

# 4. Reinstall dependencies
pip install --upgrade -r requirements.txt

# 5. Restart
./run.sh
```

## 📞 Additional Help

If issues persist, provide Claude with:

1. **Full error logs** from terminal
2. **Output of** `curl http://localhost:8001/health`
3. **MongoDB connection string** (hide password)
4. **Python version** (`python --version`)
5. **pip list** output for installed packages
6. **Contents of .env file** (hide sensitive data)

---

**Claude, please help me diagnose and fix the issues with this system based on the above context.**
