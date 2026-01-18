# Running CoastGuardian Without Redis

## Current Configuration

✅ **The application now runs WITHOUT Redis installed!**

Redis is **optional** for basic functionality. Here's what works and what doesn't:

---

## ✅ What Works WITHOUT Redis

### Full Functionality:

- ✅ **Email/Password Signup** - Create new accounts
- ✅ **Email/Password Login** - Authenticate with password
- ✅ **JWT Tokens** - Access and refresh tokens
- ✅ **Token Refresh** - Renew access tokens
- ✅ **Logout** - Revoke tokens (stored in MongoDB)
- ✅ **Get Current User** - Fetch user profile
- ✅ **Change Password** - Update password
- ✅ **MongoDB Storage** - All data persisted
- ✅ **Audit Logging** - Security events tracked
- ✅ **Security Headers** - CSP, HSTS, etc.
- ✅ **Input Validation** - Pydantic schemas
- ✅ **RBAC** - Role-based access control
- ✅ **Google OAuth** - Social login (partially)

---

## ❌ What DOESN'T Work WITHOUT Redis

### Features Requiring Redis:

- ❌ **OTP Login** (Email/SMS) - Needs Redis for OTP storage
- ❌ **Rate Limiting** - Disabled when Redis unavailable
- ❌ **Session Caching** - Falls back to MongoDB

---

## 🚀 Current Setup (No Redis)

### In `.env`:

```env
RATE_LIMIT_ENABLED=False   # Disabled (requires Redis)
```

### What Happens:

1. **Startup**: MongoDB connects ✅, Redis fails gracefully ⚠️
2. **Authentication**: Email/Password works perfectly ✅
3. **OTP**: Not available (no Redis) ❌
4. **Rate Limiting**: Disabled (no Redis) ⚠️

---

## 🔧 To Enable Full Features (Install Redis)

### Option 1: Docker (Easiest)

```bash
docker run -d -p 6379:6379 --name redis redis:7-alpine
```

### Option 2: Windows Install

1. Download: https://github.com/microsoftarchive/redis/releases
2. Install and run `redis-server.exe`

### Option 3: Linux/Mac

```bash
# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis

# macOS
brew install redis
brew services start redis
```

### Then enable rate limiting:

```env
RATE_LIMIT_ENABLED=True
```

---

## 🧪 Testing Without Redis

### Test Signup:

```bash
curl -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestP@ss123",
    "name": "Test User"
  }'
```

### Test Login:

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestP@ss123",
    "login_type": "password"
  }'
```

### Access API Docs:

http://localhost:8000/docs

---

## ⚠️ Production Recommendation

**For production, you SHOULD use Redis for:**

- Rate limiting (DDoS protection)
- OTP functionality (email/SMS login)
- Caching (performance)
- Session management

But for **development and testing**, the app works fine without it!

---

## 📊 Feature Matrix

| Feature             | Without Redis    | With Redis |
| ------------------- | ---------------- | ---------- |
| Email/Password Auth | ✅ Works         | ✅ Works   |
| JWT Tokens          | ✅ Works         | ✅ Works   |
| OTP Login           | ❌ Not Available | ✅ Works   |
| Rate Limiting       | ❌ Disabled      | ✅ Works   |
| Audit Logging       | ✅ Works         | ✅ Works   |
| Google OAuth        | ⚠️ Partial       | ✅ Works   |
| RBAC                | ✅ Works         | ✅ Works   |
| Security Headers    | ✅ Works         | ✅ Works   |

---

## 🎯 Quick Start (No Redis)

```bash
# 1. Start the server
python main.py

# 2. Open API docs
# http://localhost:8000/docs

# 3. Test signup/login using Swagger UI
# All email/password flows work perfectly!
```

**Note**: Email SMTP is configured and working. OTP just needs Redis to be enabled.

---

**✅ Bottom Line**: The app is fully functional for **password-based authentication** without Redis. Only OTP and rate limiting features require Redis.
