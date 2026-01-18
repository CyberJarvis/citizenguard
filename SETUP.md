# BlueRadar 2.0 (CoastGuardian) - Setup Guide

Complete setup instructions for new contributors and deployment.

---

## Prerequisites

### Required Software

1. **Python**: Version **3.11** or **3.12** (recommended)

   - ⚠️ **Python 3.13 NOT supported** (bcrypt compatibility issues)
   - Download: https://www.python.org/downloads/

2. **Node.js**: Version **18.x** or **20.x**

   - Download: https://nodejs.org/

3. **MongoDB**: Version **6.0** or higher

   - Download: https://www.mongodb.com/try/download/community

4. **Redis**: Version **7.0** or higher
   - Windows: https://github.com/tporadowski/redis/releases
   - macOS: `brew install redis`
   - Linux: `sudo apt-get install redis-server`

---

## Backend Setup

### 1. Navigate to Backend Directory

```bash
cd backend
```

### 2. Create Virtual Environment

**Windows:**

```bash
python -m venv .venv
.venv\Scripts\activate
```

**macOS/Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Upgrade pip

```bash
python -m pip install --upgrade pip
```

### 4. Install Dependencies

⚠️ **IMPORTANT**: If you're on Python 3.13, you MUST downgrade to Python 3.11 or 3.12 first!

```bash
pip install -r requirements.txt
```

**If you encounter bcrypt errors:**

```bash
pip uninstall bcrypt passlib
pip install bcrypt==4.0.1
pip install passlib[bcrypt]==1.7.4
```

### 5. Environment Configuration

Create `.env` file in the `backend` directory:

```env
# Application
APP_NAME=CoastGuardian
APP_VERSION=1.0.0
ENVIRONMENT=development

# Server
HOST=0.0.0.0
PORT=8000
RELOAD=True

# Database
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=coastguardian_db

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# JWT
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Security
SECRET_KEY=your-super-secret-key-change-this-in-production
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001

# Email (Gmail SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-specific-password
SMTP_FROM=noreply@coastguardian.com

# SMS (Twilio)
TWILIO_ACCOUNT_SID=your-twilio-account-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_PHONE_NUMBER=+1234567890

# OAuth2 (Google)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:3000/auth/google/callback

# File Upload
MAX_UPLOAD_SIZE=10485760
ALLOWED_EXTENSIONS=.jpg,.jpeg,.png,.gif,.mp4,.mov,.avi
```

### 6. Start Services

**Start MongoDB:**

```bash
# Windows
net start MongoDB

# macOS
brew services start mongodb-community

# Linux
sudo systemctl start mongod
```

**Start Redis:**

```bash
# Windows
redis-server

# macOS
brew services start redis

# Linux
sudo systemctl start redis-server
```

### 7. Run Backend Server

```bash
# Development mode with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or use the startup script
python -m app.main
```

Backend will be available at: `http://localhost:8000`
API Documentation: `http://localhost:8000/docs`

---

## Frontend Setup

### 1. Navigate to Frontend Directory

```bash
cd frontend
```

### 2. Install Dependencies

```bash
npm install
```

**If you encounter dependency conflicts:**

```bash
npm install --legacy-peer-deps
```

### 3. Environment Configuration

Create `.env.local` file in the `frontend` directory:

```env
# API
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws

# Google OAuth
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your-google-client-id

# Maps (Optional - for map features)
NEXT_PUBLIC_MAPBOX_TOKEN=your-mapbox-token

# Weather API (Optional)
NEXT_PUBLIC_WEATHER_API_KEY=your-weather-api-key

# Application
NEXT_PUBLIC_APP_NAME=CoastGuardian
NEXT_PUBLIC_APP_VERSION=1.0.0
```

### 4. Run Development Server

```bash
npm run dev
```

Frontend will be available at: `http://localhost:3000`

---

## Common Issues & Solutions

### Issue 1: Python 3.13 bcrypt Error

```
AttributeError: module 'bcrypt' has no attribute '__about__'
ValueError: password cannot be longer than 72 bytes
```

**Solution:**

1. Downgrade to Python 3.11 or 3.12
2. Reinstall dependencies:
   ```bash
   pip uninstall bcrypt passlib
   pip install bcrypt==4.0.1
   pip install passlib[bcrypt]==1.7.4
   ```

### Issue 2: MongoDB Connection Error

```
ServerSelectionTimeoutError: localhost:27017
```

**Solution:**

1. Ensure MongoDB is running
2. Check MongoDB status:

   ```bash
   # Windows
   sc query MongoDB

   # macOS/Linux
   systemctl status mongod
   ```

### Issue 3: Redis Connection Error

```
ConnectionError: Error connecting to Redis
```

**Solution:**

1. Ensure Redis is running
2. Test Redis connection:
   ```bash
   redis-cli ping
   # Should return: PONG
   ```

### Issue 4: Port Already in Use

```
Error: EADDRINUSE: address already in use :::8000
```

**Solution:**

```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# macOS/Linux
lsof -ti:8000 | xargs kill -9
```

### Issue 5: Frontend Build Errors

```
Module not found: Can't resolve 'next/navigation'
```

**Solution:**

```bash
# Delete node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

### Issue 6: Login Returns 401 Unauthorized

This happens if you created users before fixing the password hashing issue.

**Solution:**
You need to re-register users or manually reset passwords after the bcrypt fix is applied. The new password hashing will work correctly.

---

## Development Workflow

### Running Both Services Simultaneously

**Terminal 1 (Backend):**

```bash
cd backend
.venv/Scripts/activate  # Windows
source .venv/bin/activate  # macOS/Linux
uvicorn app.main:app --reload
```

**Terminal 2 (Frontend):**

```bash
cd frontend
npm run dev
```

### Testing the Application

1. Open browser: `http://localhost:3000`
2. Register a new account (citizen/authority)
3. Verify email with OTP (check console logs in backend)
4. Login and explore features

---

## Production Deployment

### Backend Deployment

1. Update `.env` with production values
2. Set `ENVIRONMENT=production`
3. Use strong secret keys
4. Configure proper database URLs
5. Run with Gunicorn:
   ```bash
   gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
   ```

### Frontend Deployment

1. Build production bundle:

   ```bash
   npm run build
   ```

2. Start production server:

   ```bash
   npm start
   ```

3. Or deploy to Vercel/Netlify/AWS

---

## Database Initialization

The application automatically creates indexes and collections on first run. No manual database setup required!

---

## API Documentation

Once the backend is running, visit:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## Support

If you encounter issues:

1. Check this guide for common solutions
2. Ensure all prerequisites are correctly installed
3. Verify environment variables are set
4. Check service logs for detailed error messages

---

## System Requirements

**Minimum:**

- Python 3.11+
- Node.js 18+
- 4GB RAM
- MongoDB 6.0+
- Redis 7.0+

**Recommended:**

- Python 3.12
- Node.js 20
- 8GB RAM
- SSD storage
- Stable internet connection

---

**Last Updated**: November 24, 2025
**Version**: 1.0.0
