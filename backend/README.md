# CoastGuardian Backend

**Ocean Hazard Reporting Platform for INCOIS - SIH 2025**

Production-ready authentication module with FastAPI, MongoDB, Redis, JWT, OTP verification, and Google OAuth2.

---

## Features

### Authentication Methods

- **Email/Password**: Traditional signup and login
- **Phone/OTP**: SMS-based authentication (Twilio)
- **Email/OTP**: Email-based authentication
- **Google OAuth2**: Social login integration

### Security Features

- **JWT Tokens**: Access + Refresh token architecture
- **Password Hashing**: bcrypt with 12 rounds
- **OTP Verification**: Redis-based with expiry and rate limiting
- **Rate Limiting**: Configurable per-endpoint limits
- **CORS Protection**: Configured allowed origins
- **Security Headers**: CSP, HSTS, XSS protection
- **Audit Logging**: All auth events logged to MongoDB
- **Token Revocation**: Secure logout with token blacklisting
- **Input Validation**: Pydantic schemas with strict validation

### Role-Based Access Control (RBAC)

- **Citizen**: Regular users
- **Analyst**: Verification and analytics access
- **Admin**: Full system access

---

## Technology Stack

- **Framework**: FastAPI 0.109+
- **Language**: Python 3.11+
- **Database**: MongoDB (Motor async driver)
- **Cache**: Redis (async)
- **Authentication**: JWT (python-jose)
- **Password Hashing**: bcrypt (passlib)
- **Email**: SMTP (aiosmtplib)
- **SMS**: Twilio
- **OAuth**: Authlib + httpx
- **Validation**: Pydantic 2.0

---

## Project Structure

```
backend/
app/
 __init__.py
 config.py                 # Environment configuration
database.py               # MongoDB & Redis connections
models/
 __init__.py
 user.py               # User, AuditLog, RefreshToken models
schemas/
 __init__.py
auth.py               # Request/Response schemas
api/
v1/
__init__.py
auth.py           # Authentication endpoints
services/
__init__.py
otp.py                # OTP generation/verification
email.py              # Email service
sms.py                # SMS service (Twilio)
 oauth.py              # Google OAuth2
utils/
__init__.py
password.py           # Password hashing
jwt.py                # JWT utilities
security.py           # Security helpers
audit.py              # Audit logging
middleware/
__init__.py
rate_limit.py         # Rate limiting
security.py           # Security middleware + RBAC
.env.example                  # Environment variables template
main.py                       # Application entry point
requirements.txt              # Dependencies
pyproject.toml                # Project configuration
README.md                     # This file
```

---

## Setup Instructions

### 1. Prerequisites

- Python 3.11 or higher
- MongoDB 7.x (local or Atlas)
- Redis 7.x
- Twilio account (for SMS OTP)
- Google OAuth credentials (for Google login)

### 2. Installation

```bash
# Clone repository
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration

```bash
# Copy environment template
copy .env.example .env  # Windows
# cp .env.example .env  # Linux/Mac
```

Edit `.env` and configure the following:

#### Required Settings

```env
# Security (CHANGE THESE!)
SECRET_KEY=your-secret-key-min-32-characters-change-this
JWT_SECRET_KEY=your-jwt-secret-min-32-characters-change-this

# Database
MONGODB_URL=mongodb://localhost:27017
REDIS_HOST=localhost
REDIS_PORT=6379

# Email (Gmail example)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=noreply@CoastGuardian.in
```

#### Optional Settings

```env
# SMS (Twilio)
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
TWILIO_PHONE_NUMBER=+1234567890

# Google OAuth
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback

# Frontend
FRONTEND_URL=http://localhost:3000
```

### 4. Generate Secret Keys

```bash
# Generate secure secret keys
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Use the output for `SECRET_KEY` and `JWT_SECRET_KEY`.

### 5. Start Services

```bash
# Start MongoDB (if running locally)
mongod

# Start Redis (if running locally)
redis-server
```

### 6. Run Application

```bash
# Development mode (with hot reload)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Production mode
python main.py
```

The API will be available at `http://localhost:8000`

---

## API Documentation

### Interactive Docs

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Authentication Endpoints

#### 1. **Signup** - `POST /api/v1/auth/signup`

Create a new user account.

**Request:**

```json
{
  "email": "user@example.com",
  "phone": "+919876543210",
  "password": "SecureP@ss123",
  "name": "John Doe"
}
```

**Response:**

```json
{
  "user_id": "USR-20250119123456ABCD",
  "email": "user@example.com",
  "phone": "+919876543210",
  "name": "John Doe",
  "role": "citizen",
  "credibility_score": 50,
  "email_verified": false,
  "phone_verified": false,
  "is_active": true,
  "created_at": "2025-01-19T10:30:00Z"
}
```

#### 2. **Login (Password)** - `POST /api/v1/auth/login`

Login with email/password.

**Request:**

```json
{
  "email": "user@example.com",
  "password": "SecureP@ss123",
  "login_type": "password"
}
```

**Response:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 7200
}
```

#### 3. **Login (OTP)** - `POST /api/v1/auth/login`

Send OTP to email/phone.

**Request:**

```json
{
  "email": "user@example.com",
  "login_type": "otp"
}
```

**Response:**

```json
{
  "message": "OTP sent successfully",
  "expires_in": 300,
  "sent_to": "u***@example.com"
}
```

#### 4. **Verify OTP** - `POST /api/v1/auth/verify-otp`

Verify OTP and get tokens.

**Request:**

```json
{
  "email": "user@example.com",
  "otp": "123456"
}
```

**Response:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 7200
}
```

#### 5. **Refresh Token** - `POST /api/v1/auth/refresh`

Get new access token using refresh token.

**Request:**

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 7200
}
```

#### 6. **Logout** - `POST /api/v1/auth/logout`

Revoke refresh token.

**Headers:**

```
Authorization: Bearer <access_token>
```

**Request:**

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response:**

```json
{
  "message": "Logged out successfully"
}
```

#### 7. **Google OAuth Login** - `GET /api/v1/auth/google`

Initiate Google OAuth flow. Redirects to Google consent screen.

#### 8. **Google OAuth Callback** - `GET /api/v1/auth/google/callback`

OAuth callback endpoint (handled automatically). Redirects to frontend with tokens.

#### 9. **Get Current User** - `GET /api/v1/auth/me`

Get authenticated user profile.

**Headers:**

```
Authorization: Bearer <access_token>
```

**Response:**

```json
{
  "user_id": "USR-20250119123456ABCD",
  "email": "user@example.com",
  "name": "John Doe",
  "role": "citizen",
  "credibility_score": 75,
  "email_verified": true,
  "is_active": true,
  "created_at": "2025-01-19T10:30:00Z",
  "last_login": "2025-01-19T15:45:00Z"
}
```

#### 10. **Change Password** - `POST /api/v1/auth/change-password`

Change user password.

**Headers:**

```
Authorization: Bearer <access_token>
```

**Request:**

```json
{
  "old_password": "OldP@ss123",
  "new_password": "NewSecureP@ss123"
}
```

**Response:**

```json
{
  "message": "Password changed successfully. Please login again."
}
```

---

## Security Best Practices

### Implemented

**Password Policy**

- Minimum 8 characters
- Requires uppercase, lowercase, digit, special character
- Bcrypt hashing with 12 rounds

**JWT Security**

- Short-lived access tokens (2 hours)
- Long-lived refresh tokens (7 days)
- Token revocation on logout
- Secure token storage in MongoDB

  **OTP Security**

- 6-digit cryptographically secure OTP
- 5-minute expiry
- Maximum 3 attempts
- Rate limiting (3 OTP/5 minutes)

**Rate Limiting**

- 100 requests/hour per IP (global)
- 5 login attempts/15 minutes
- Configurable per-endpoint limits

  **CORS Configuration**

- Whitelist allowed origins
- Credentials support
- Secure headers

  **Security Headers**

- Content-Security-Policy
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- X-XSS-Protection
- HSTS (production only)

  **Audit Logging**

- All auth events logged
- IP address tracking
- User agent tracking
- Success/failure tracking

### Recommendations for Production

1. **Environment Variables**

   - Use AWS Secrets Manager / HashiCorp Vault
   - Never commit `.env` to version control

2. **HTTPS Only**

   - Enable TLS 1.3
   - Set `SESSION_COOKIE_SECURE=True`

3. **Database Security**

   - Enable MongoDB authentication
   - Use Redis password
   - Enable connection encryption

4. **Monitoring**

   - Set up Prometheus + Grafana
   - Enable ELK stack for logs
   - Configure alerts for auth failures

5. **DDoS Protection**
   - Use Cloudflare or AWS Shield
   - Implement IP blocking for repeated failures

---

## Testing

### Manual Testing with cURL

**Signup:**

```bash
curl -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestP@ss123",
    "name": "Test User"
  }'
```

**Login:**

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestP@ss123",
    "login_type": "password"
  }'
```

**Get Current User:**

```bash
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <access_token>"
```

### Using Postman

1. Import the API collection (available in Swagger UI)
2. Set environment variables for tokens
3. Test all endpoints sequentially

---

## Deployment

### Docker Deployment

**Dockerfile:**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Build and Run:**

```bash
docker build -t CoastGuardian-backend .
docker run -p 8000:8000 --env-file .env CoastGuardian-backend
```

### Production Checklist

- [ ] Set `ENVIRONMENT=production` in `.env`
- [ ] Set `DEBUG=False`
- [ ] Generate strong `SECRET_KEY` and `JWT_SECRET_KEY`
- [ ] Configure MongoDB Atlas or production MongoDB
- [ ] Configure Redis (ElastiCache or Redis Cloud)
- [ ] Set up SMTP for emails (SendGrid, AWS SES)
- [ ] Configure Twilio for SMS
- [ ] Set up Google OAuth credentials
- [ ] Enable HTTPS/TLS
- [ ] Configure CORS allowed origins
- [ ] Set up monitoring and logging
- [ ] Configure automated backups
- [ ] Set up CI/CD pipeline

---

## Troubleshooting

### Common Issues

**1. MongoDB Connection Failed**

```bash
# Check if MongoDB is running
mongosh

# Check connection string in .env
MONGODB_URL=mongodb://localhost:27017
```

**2. Redis Connection Failed**

```bash
# Check if Redis is running
redis-cli ping

# Check Redis config in .env
REDIS_HOST=localhost
REDIS_PORT=6379
```

**3. OTP Not Sending**

```bash
# Check SMTP credentials
# For Gmail, use App Password (not regular password)
# Enable "Less secure app access" or use OAuth2
```

**4. JWT Token Errors**

```bash
# Ensure JWT_SECRET_KEY is at least 32 characters
# Check token expiry settings
```

---

## Contributing

1. Create feature branch
2. Follow code style (Black formatter)
3. Add tests
4. Update documentation
5. Submit pull request

---

## License

MIT License - See LICENSE file for details

---

## Support

For issues and questions:

- GitHub Issues: [repository-url]/issues
- Email: support@CoastGuardian.in
- Documentation: [docs-url]

---

## Changelog

### v1.0.0 (2025-01-19)

- Initial release
- Complete authentication module
- Email/Phone/Password/OTP/OAuth support
- Production-ready security features
- Comprehensive API documentation

---

**Built with for SIH 2025 - INCOIS Ocean Hazard Reporting Platform**
