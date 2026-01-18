# CoastGuardian Backend - Quick Start Guide

## 🚀 5-Minute Setup

### Step 1: Install Redis (Required)

**Windows:**

```bash
# Download and install Redis from:
# https://github.com/microsoftarchive/redis/releases
# OR use Docker:
docker run -d -p 6379:6379 redis:7-alpine
```

**Linux/Mac:**

```bash
# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis

# macOS
brew install redis
brew services start redis
```

### Step 2: Configure Email (Optional but Recommended)

For Gmail:

1. Enable 2-Factor Authentication in your Google Account
2. Generate App Password: https://myaccount.google.com/apppasswords
3. Update `.env`:

```env
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-16-char-app-password
```

### Step 3: Configure SMS (Optional)

For Twilio:

1. Sign up at https://www.twilio.com/try-twilio
2. Get your credentials from the Console
3. Update `.env`:

```env
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_PHONE_NUMBER=+1234567890
```

### Step 4: Run the Application

```bash
# Make sure you're in the backend directory
cd backend

# Run the server
python main.py
```

The server will start at **http://localhost:8000**

### Step 5: Test the API

Open your browser:

- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 🧪 Quick Test

### Test Signup (cURL)

```bash
curl -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestP@ss123",
    "name": "Test User"
  }'
```

### Test Login (cURL)

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestP@ss123",
    "login_type": "password"
  }'
```

### Test with Swagger UI

1. Go to http://localhost:8000/docs
2. Click on "POST /api/v1/auth/signup"
3. Click "Try it out"
4. Fill in the request body
5. Click "Execute"

## ✅ What Works Right Now

### Fully Functional Features:

- ✅ **Email/Password Signup & Login**
- ✅ **JWT Access + Refresh Tokens**
- ✅ **Password Change**
- ✅ **Token Refresh & Logout**
- ✅ **Rate Limiting** (global + per-endpoint)
- ✅ **Security Headers** (CSP, HSTS, XSS protection)
- ✅ **Audit Logging** (all auth events)
- ✅ **Role-Based Access Control** (Citizen/Analyst/Admin)
- ✅ **Input Validation** (strict Pydantic schemas)

### Requires Configuration:

- ⚙️ **Email OTP** (needs SMTP credentials)
- ⚙️ **SMS OTP** (needs Twilio credentials)
- ⚙️ **Google OAuth** (needs Google Cloud credentials)

## 🔐 Security Features Active

| Feature          | Status    | Details                            |
| ---------------- | --------- | ---------------------------------- |
| Password Hashing | ✅ Active | bcrypt with 12 rounds              |
| JWT Tokens       | ✅ Active | 2-hour access, 7-day refresh       |
| Rate Limiting    | ✅ Active | 100 req/hour global, 5 login/15min |
| CORS Protection  | ✅ Active | localhost:3000, localhost:8000     |
| Security Headers | ✅ Active | CSP, XSS, HSTS, Frame-Options      |
| Audit Logging    | ✅ Active | All auth events to MongoDB         |
| Token Revocation | ✅ Active | Secure logout with blacklisting    |
| Input Validation | ✅ Active | Pydantic schemas with sanitization |

## 📊 Database Collections

The application automatically creates these MongoDB collections:

1. **users** - User accounts with roles and credentials
2. **refresh_tokens** - JWT refresh tokens with TTL
3. **audit_logs** - Security event logs with IP tracking

All collections have proper indexes for performance.

## 🛠️ Troubleshooting

### "MongoDB connection failed"

✓ MongoDB Atlas URL is already configured in `.env`
✓ Check internet connection for Atlas access

### "Redis connection failed"

```bash
# Check if Redis is running
redis-cli ping
# Should return: PONG

# If not running, start it:
# Windows: redis-server
# Linux: sudo systemctl start redis
# macOS: brew services start redis
```

### "OTP not sending"

- Email OTP: Configure SMTP settings in `.env`
- SMS OTP: Add Twilio credentials in `.env`

### "Rate limit exceeded"

Wait 15 minutes or disable rate limiting:

```env
RATE_LIMIT_ENABLED=False
```

## 🎯 Next Steps

1. **Configure Email/SMS** for full OTP functionality
2. **Set up Google OAuth** for social login
3. **Test all endpoints** using Swagger UI
4. **Review security settings** for production
5. **Set up monitoring** (Prometheus + Grafana)
6. **Deploy to production** (Docker/Kubernetes)

## 📚 Documentation

- **Full README**: `README.md`
- **API Docs**: http://localhost:8000/docs
- **Architecture**: `../technical_architecure.md`

## 🆘 Need Help?

- Check logs: Look for error messages in console
- API Documentation: http://localhost:8000/docs
- Environment Issues: Review `.env` configuration
- Database Issues: Check MongoDB Atlas connection

---

**Ready for Production? See `README.md` for deployment checklist!**
