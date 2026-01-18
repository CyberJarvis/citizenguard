# Railway Deployment Checklist

Use this checklist to ensure a smooth deployment to Railway.

## Pre-Deployment

### 1. Local Testing
- [ ] Backend runs locally without errors
- [ ] All environment variables are documented in `.env.example`
- [ ] Database migrations work correctly
- [ ] All API endpoints respond correctly

### 2. Code Preparation
- [ ] Latest code is pushed to GitHub
- [ ] No sensitive data (API keys, passwords) in code
- [ ] `.gitignore` includes `.env`, `venv/`, `__pycache__/`
- [ ] Dockerfile builds successfully locally (optional test)

## Railway Setup

### 3. Create Project
- [ ] Created new Railway project
- [ ] Connected GitHub repository (or ready to deploy)

### 4. Add MongoDB
Choose one:
- [ ] Added Railway MongoDB plugin
  - [ ] Created `MONGODB_URL` variable referencing `${{MongoDB.MONGO_URL}}`
  - [ ] Created `MONGODB_DB_NAME=CoastGuardian`

OR

- [ ] Using MongoDB Atlas
  - [ ] Created free cluster at https://cloud.mongodb.com
  - [ ] Added connection string to `MONGODB_URL`
  - [ ] Set Network Access to allow Railway IPs (0.0.0.0/0 for testing)
  - [ ] Created database user with read/write permissions

### 5. Add Redis
- [ ] Added Railway Redis plugin
- [ ] Created `REDIS_HOST` = `${{Redis.REDIS_HOST}}`
- [ ] Created `REDIS_PORT` = `${{Redis.REDIS_PORT}}`
- [ ] Created `REDIS_PASSWORD` = `${{Redis.REDIS_PASSWORD}}`
- [ ] Set `REDIS_SSL=True`

## Environment Variables

### 6. Core Settings (Required)
Copy these to Railway:
- [ ] `APP_NAME=CoastGuardian`
- [ ] `APP_VERSION=1.0.0`
- [ ] `ENVIRONMENT=production`
- [ ] `DEBUG=False`
- [ ] `API_PREFIX=/api/v1`
- [ ] `HOST=0.0.0.0`

### 7. Security (CRITICAL - Generate New!)
Generate with: `python -c "import secrets; print(secrets.token_urlsafe(32))"`

- [ ] `SECRET_KEY=<generated-key>`
- [ ] `JWT_SECRET_KEY=<generated-key>`
- [ ] `JWT_ALGORITHM=HS256`
- [ ] `JWT_ACCESS_TOKEN_EXPIRE_MINUTES=120`
- [ ] `JWT_REFRESH_TOKEN_EXPIRE_DAYS=7`

### 8. CORS
- [ ] `ALLOWED_ORIGINS=<your-frontend-urls>`
  - Example: `https://myapp.vercel.app,https://www.myapp.vercel.app`
  - Use commas to separate multiple origins

### 9. Frontend URL
- [ ] `FRONTEND_URL=<your-frontend-url>`

### 10. Weather APIs (Required for ML)
Get free keys:
- WeatherAPI: https://www.weatherapi.com/signup.aspx
- OpenWeatherMap: https://openweathermap.org/api

- [ ] `WEATHERAPI_KEY=<your-key>`
- [ ] `OPENWEATHER_API_KEY=<your-key>`

### 11. ML Configuration
- [ ] `ML_UPDATE_INTERVAL_MINUTES=5`
- [ ] `EARTHQUAKE_FETCH_HOURS=24`
- [ ] `EARTHQUAKE_MIN_MAGNITUDE=4.0`
- [ ] `WEATHER_CACHE_TTL_SECONDS=300`

### 12. Feature Flags
- [ ] `VECTORDB_ENABLED=True`
- [ ] `MULTIHAZARD_ENABLED=True`
- [ ] `PREDICTIVE_ALERTS_ENABLED=True`
- [ ] `PUSH_NOTIFICATIONS_ENABLED=False`
- [ ] `SMI_ENABLED=True`
- [ ] `SMI_AUTO_START_FEED=False`

### 13. Rate Limiting
- [ ] `RATE_LIMIT_ENABLED=True`
- [ ] `RATE_LIMIT_WINDOW_SECONDS=3600`
- [ ] `RATE_LIMIT_MAX_REQUESTS_PER_WINDOW=1000`

### 14. Session Configuration
- [ ] `SESSION_COOKIE_NAME=CoastGuardian_session`
- [ ] `SESSION_COOKIE_SECURE=True`
- [ ] `SESSION_COOKIE_HTTPONLY=True`
- [ ] `SESSION_COOKIE_SAMESITE=lax`
- [ ] `SESSION_MAX_AGE=86400`

### 15. Password Policy
- [ ] `PASSWORD_MIN_LENGTH=8`
- [ ] `PASSWORD_REQUIRE_UPPERCASE=True`
- [ ] `PASSWORD_REQUIRE_LOWERCASE=True`
- [ ] `PASSWORD_REQUIRE_DIGIT=True`
- [ ] `PASSWORD_REQUIRE_SPECIAL=True`

### 16. Logging
- [ ] `AUDIT_LOG_ENABLED=True`
- [ ] `LOG_LEVEL=INFO`

### 17. OTP Configuration
- [ ] `OTP_LENGTH=6`
- [ ] `OTP_EXPIRE_MINUTES=5`
- [ ] `OTP_MAX_ATTEMPTS=3`

### 18. Optional Services (Add if needed)

#### Email (SMTP)
- [ ] `SMTP_HOST=smtp.gmail.com`
- [ ] `SMTP_PORT=587`
- [ ] `SMTP_USER=<your-email@gmail.com>`
- [ ] `SMTP_PASSWORD=<gmail-app-password>`
- [ ] `SMTP_FROM_EMAIL=noreply@coastguardian.com`
- [ ] `SMTP_FROM_NAME=CoastGuardian`
- [ ] `SMTP_TLS=True`

#### SMS (Twilio)
- [ ] `TWILIO_ACCOUNT_SID=<your-sid>`
- [ ] `TWILIO_AUTH_TOKEN=<your-token>`
- [ ] `TWILIO_PHONE_NUMBER=<your-number>`

#### Google OAuth
- [ ] `GOOGLE_CLIENT_ID=<your-client-id>`
- [ ] `GOOGLE_CLIENT_SECRET=<your-secret>`
- [ ] `GOOGLE_REDIRECT_URI=https://<backend-url>/api/v1/auth/google/callback`

#### AWS S3 (File Uploads)
- [ ] `AWS_ACCESS_KEY_ID=<your-key>`
- [ ] `AWS_SECRET_ACCESS_KEY=<your-secret>`
- [ ] `AWS_REGION=ap-south-1`
- [ ] `AWS_S3_BUCKET=<your-bucket>`

## Deployment

### 19. Deploy
- [ ] Clicked "Deploy" in Railway dashboard
- [ ] Watching build logs for errors
- [ ] Build completed successfully (15-20 minutes expected)

### 20. Verify Deployment
- [ ] Check logs for: `[OK] All services connected successfully`
- [ ] Check logs for: `[OK] ML Monitoring Service initialized`
- [ ] Visit health endpoint: `https://<your-url>.railway.app/health`
  - Should return: `{"status": "healthy"}`

### 21. Test API
- [ ] Test root endpoint: `https://<your-url>.railway.app/`
  - Should return: `{"name": "CoastGuardian", "status": "running"}`
- [ ] Test API docs (if DEBUG=True): `https://<your-url>.railway.app/docs`
- [ ] Test a few key endpoints (e.g., `/api/v1/auth/health`)

## Post-Deployment

### 22. Frontend Configuration
- [ ] Updated frontend `.env` with Railway backend URL
- [ ] Deployed frontend with new backend URL
- [ ] Tested frontend-to-backend communication
- [ ] No CORS errors in browser console

### 23. Domain Setup (Optional)
- [ ] Generated Railway subdomain or added custom domain
- [ ] Updated `ALLOWED_ORIGINS` with final domain
- [ ] Updated `FRONTEND_URL` if changed
- [ ] Updated `GOOGLE_REDIRECT_URI` if using OAuth

### 24. Security Final Check
- [ ] `DEBUG=False` in production
- [ ] `SESSION_COOKIE_SECURE=True`
- [ ] No API keys in code/logs
- [ ] MongoDB connection uses SSL
- [ ] Redis uses password authentication
- [ ] All secrets are unique (not default values)

### 25. Monitoring Setup
- [ ] Checked Railway metrics dashboard
- [ ] Set up alerts for downtime (if available)
- [ ] Documented backend URL for team

## Troubleshooting

If deployment fails, check:
- [ ] Build logs for specific error messages
- [ ] All required environment variables are set
- [ ] MongoDB connection string is correct
- [ ] No typos in environment variable names

Common errors:
- **Build timeout**: Upgrade to Railway Pro ($5/mo)
- **PyTorch install fails**: Check Dockerfile logs, may need to adjust torch version
- **MongoDB connection fails**: Check Atlas Network Access allows Railway IPs
- **Health check fails**: Check MongoDB is connected, increase timeout in railway.toml

## Cost Management

- [ ] Reviewed Railway pricing
- [ ] Monitored resource usage after 24 hours
- [ ] Optimized if needed (reduce ML features, scale down)

## Backup Plan

- [ ] Documented MongoDB backup strategy
- [ ] Tested rollback procedure in Railway
- [ ] Created emergency contact list for issues

---

**Deployment Date**: __________

**Backend URL**: __________

**MongoDB Provider**: ☐ Railway  ☐ Atlas

**Redis Provider**: ☐ Railway  ☐ External

**Deployed By**: __________

**Notes**:
________________________________________________________________________________
________________________________________________________________________________
________________________________________________________________________________
