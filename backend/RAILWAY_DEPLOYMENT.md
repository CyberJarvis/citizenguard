# Railway Deployment Guide for CoastGuardian Backend

## Prerequisites
- Railway account (https://railway.app)
- MongoDB Atlas account (or Railway MongoDB plugin)
- Redis instance (Railway Redis plugin or external)

## Step 1: Create a New Railway Project

1. Go to https://railway.app
2. Click "New Project"
3. Choose "Deploy from GitHub repo" or "Empty Project"

## Step 2: Add Required Services

### MongoDB Setup (Option A: Railway Plugin)
1. Click "+ New" → "Database" → "Add MongoDB"
2. Railway will automatically create `MONGO_URL` variable
3. You'll need to create these variables manually:
   - `MONGODB_URL` = `${{MongoDB.MONGO_URL}}` (reference the auto-generated one)
   - `MONGODB_DB_NAME` = `CoastGuardian`

### MongoDB Setup (Option B: MongoDB Atlas)
1. Go to https://cloud.mongodb.com
2. Create a new cluster (free tier available)
3. Get your connection string
4. Add these variables in Railway:
   - `MONGODB_URL` = `mongodb+srv://<username>:<password>@<cluster>.mongodb.net/`
   - `MONGODB_DB_NAME` = `CoastGuardian`

### Redis Setup (Railway Plugin)
1. Click "+ New" → "Database" → "Add Redis"
2. Railway will automatically create `REDIS_URL` variable
3. You'll need to create these variables manually:
   - `REDIS_HOST` = `${{Redis.REDIS_HOST}}`
   - `REDIS_PORT` = `${{Redis.REDIS_PORT}}`
   - `REDIS_PASSWORD` = `${{Redis.REDIS_PASSWORD}}`

## Step 3: Required Environment Variables

Copy these environment variables to your Railway project settings:

### Core Application Settings
```
APP_NAME=CoastGuardian
APP_VERSION=1.0.0
ENVIRONMENT=production
DEBUG=False
API_PREFIX=/api/v1
HOST=0.0.0.0
```

### Security (IMPORTANT - Generate New Keys!)
Generate secret keys using:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Then set:
```
SECRET_KEY=<your-generated-secret-key>
JWT_SECRET_KEY=<your-generated-jwt-secret-key>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=120
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
```

### CORS Settings
```
ALLOWED_ORIGINS=https://your-frontend-domain.com,https://www.your-frontend-domain.com
```
**Note**: Replace with your actual frontend URL(s). Separate multiple origins with commas.

### Database Configuration
```
MONGODB_URL=<see Step 2 above>
MONGODB_DB_NAME=CoastGuardian
MONGODB_MIN_POOL_SIZE=10
MONGODB_MAX_POOL_SIZE=50
```

### Redis Configuration
```
REDIS_HOST=<see Step 2 above>
REDIS_PORT=<see Step 2 above>
REDIS_PASSWORD=<see Step 2 above>
REDIS_DB=0
REDIS_SSL=True
```

### Rate Limiting
```
RATE_LIMIT_ENABLED=True
RATE_LIMIT_WINDOW_SECONDS=3600
RATE_LIMIT_MAX_REQUESTS_PER_WINDOW=1000
RATE_LIMIT_LOGIN_MAX_ATTEMPTS=5
RATE_LIMIT_LOGIN_WINDOW_SECONDS=900
```

### Email Configuration (SMTP - Optional but recommended)
For Gmail:
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=noreply@coastguardian.com
SMTP_FROM_NAME=CoastGuardian
SMTP_TLS=True
```

**To get Gmail App Password:**
1. Go to Google Account → Security
2. Enable 2-Factor Authentication
3. Go to App Passwords
4. Generate a password for "Mail"

### SMS Configuration (Twilio - Optional)
```
TWILIO_ACCOUNT_SID=your-twilio-account-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_PHONE_NUMBER=+1234567890
```

### Weather APIs (Required for ML features)
```
WEATHERAPI_KEY=your-weatherapi-key
OPENWEATHER_API_KEY=your-openweather-key
```

**Get Free API Keys:**
- WeatherAPI: https://www.weatherapi.com/signup.aspx
- OpenWeatherMap: https://openweathermap.org/api

### ML Configuration
```
ML_UPDATE_INTERVAL_MINUTES=5
EARTHQUAKE_FETCH_HOURS=24
EARTHQUAKE_MIN_MAGNITUDE=4.0
WEATHER_CACHE_TTL_SECONDS=300
```

### Social Media Intelligence (SMI)
```
SMI_ENABLED=True
SMI_BASE_URL=http://localhost:8001
SMI_TIMEOUT_SECONDS=30
SMI_ALERT_SYNC_INTERVAL_SECONDS=30
SMI_CRITICAL_ALERT_THRESHOLD=7.0
SMI_AUTO_START_FEED=False
SMI_DEFAULT_POST_INTERVAL=8
SMI_DEFAULT_DISASTER_PROBABILITY=0.3
```

### Feature Flags
```
VECTORDB_ENABLED=True
MULTIHAZARD_ENABLED=True
PREDICTIVE_ALERTS_ENABLED=True
PUSH_NOTIFICATIONS_ENABLED=False
```

### Frontend URL
```
FRONTEND_URL=https://your-frontend-domain.com
```

### Session Configuration
```
SESSION_COOKIE_NAME=CoastGuardian_session
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=lax
SESSION_MAX_AGE=86400
```

### Password Policy
```
PASSWORD_MIN_LENGTH=8
PASSWORD_REQUIRE_UPPERCASE=True
PASSWORD_REQUIRE_LOWERCASE=True
PASSWORD_REQUIRE_DIGIT=True
PASSWORD_REQUIRE_SPECIAL=True
```

### Logging
```
AUDIT_LOG_ENABLED=True
LOG_LEVEL=INFO
```

### Google OAuth (Optional)
```
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=https://your-backend-domain.com/api/v1/auth/google/callback
```

### OTP Configuration
```
OTP_LENGTH=6
OTP_EXPIRE_MINUTES=5
OTP_MAX_ATTEMPTS=3
```

### AWS S3 (For file uploads - Optional)
```
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=ap-south-1
AWS_S3_BUCKET=your-bucket-name
```

## Step 4: Deploy

### Option A: Deploy from GitHub
1. Connect your GitHub repository to Railway
2. Railway will automatically detect the `Dockerfile`
3. Click "Deploy"
4. Wait for the build to complete (15-20 minutes due to ML dependencies)

### Option B: Deploy using Railway CLI
```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Link to project
railway link

# Deploy
railway up
```

## Step 5: Verify Deployment

1. Check the deployment logs in Railway dashboard
2. Look for these success messages:
   ```
   [OK] All services connected successfully
   [OK] ML Monitoring Service initialized
   [OK] Database migrations completed
   ```

3. Test the health endpoint:
   ```bash
   curl https://your-backend-domain.railway.app/health
   ```

   Expected response:
   ```json
   {
     "status": "healthy",
     "services": {
       "mongodb": "healthy",
       "redis": "healthy"
     },
     "version": "1.0.0"
   }
   ```

## Step 6: Custom Domain (Optional)

1. Go to your Railway project
2. Click on "Settings"
3. Scroll to "Domains"
4. Click "Generate Domain" for a free Railway subdomain
5. Or add your custom domain

## Common Issues & Solutions

### Issue 1: Build Timeout
**Solution**: Railway has a build timeout. The ML dependencies (PyTorch, FAISS) are large.
- The optimized Dockerfile should complete in ~15 minutes
- If it still times out, consider upgrading to Railway Pro ($5/month)

### Issue 2: PyTorch Installation Fails
**Error**: `Could not find a version that satisfies torch==2.0.0+cpu`

**Solution**: The Dockerfile now installs PyTorch with explicit `--extra-index-url`. If it still fails:
1. Check Railway build logs for the exact error
2. Try changing to a stable PyTorch version without +cpu suffix:
   ```
   torch==2.0.0
   torchaudio==2.0.0
   ```

### Issue 3: MongoDB Connection Failed
**Error**: `[ERROR] Failed to start application`

**Solution**:
1. Check `MONGODB_URL` is set correctly
2. Ensure MongoDB Atlas allows connections from anywhere (0.0.0.0/0) in Network Access
3. Check username/password don't contain special characters (URL encode if they do)

### Issue 4: Redis Connection Warning
**Warning**: `[WARN] Redis connection failed (continuing without cache)`

**Solution**: This is a soft failure - the app will work without Redis, but:
1. Rate limiting will be disabled
2. Session management will be limited
3. To fix: Add Railway Redis plugin and configure `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`

### Issue 5: Health Check Failing
**Error**: Deployment shows "Unhealthy"

**Solution**:
1. Check logs for startup errors
2. Ensure `/health` endpoint is accessible
3. Increase `healthcheckTimeout` in `railway.toml` if needed
4. Check MongoDB connection is working

### Issue 6: CORS Errors from Frontend
**Error**: `Access to fetch at 'https://backend.railway.app' from origin 'https://frontend.vercel.app' has been blocked by CORS`

**Solution**:
1. Add your frontend URL to `ALLOWED_ORIGINS`:
   ```
   ALLOWED_ORIGINS=https://frontend.vercel.app,https://www.frontend.vercel.app
   ```
2. Restart the deployment

## Monitoring

### View Logs
```bash
# Using Railway CLI
railway logs

# Or view in Railway dashboard
```

### Check Service Status
Visit: `https://your-backend-domain.railway.app/health`

### Monitor Performance
- Railway provides CPU, Memory, and Network metrics in the dashboard
- Set up alerts for service downtime

## Scaling

### Vertical Scaling (More Resources)
1. Upgrade to Railway Pro or Team plan
2. More CPU/Memory allocated automatically

### Horizontal Scaling (More Instances)
Edit `railway.toml`:
```toml
[deploy]
numReplicas = 2  # Increase for load balancing
```

**Note**: Requires Railway Pro plan

## Cost Estimation

### Free Tier
- $5 free credit/month
- Shared CPU/Memory
- Should be sufficient for development/testing

### Pro Plan ($5/month)
- $5 credit + pay for usage
- Better performance
- Longer build timeouts
- Custom domains

### Estimated Monthly Cost for Production
- Railway Pro: $5/month base
- Backend service: ~$10-15/month (depending on traffic)
- MongoDB Atlas (Free tier): $0
- Redis (Railway): ~$5/month
- **Total**: ~$20-25/month

## Security Checklist

- [ ] Changed `SECRET_KEY` and `JWT_SECRET_KEY` from defaults
- [ ] Set `DEBUG=False` in production
- [ ] Configured `ALLOWED_ORIGINS` to only include your frontend
- [ ] Set `SESSION_COOKIE_SECURE=True`
- [ ] MongoDB connection uses SSL/TLS
- [ ] Redis connection uses password authentication
- [ ] API keys are kept secret (not committed to git)
- [ ] MongoDB Atlas network access is restricted (if possible)

## Rollback

If deployment fails:

### Using Railway Dashboard
1. Go to "Deployments" tab
2. Find the last working deployment
3. Click "Redeploy"

### Using Railway CLI
```bash
railway rollback
```

## Support

- Railway Docs: https://docs.railway.app
- Railway Discord: https://discord.gg/railway
- MongoDB Atlas Support: https://support.mongodb.com

## Next Steps

After successful deployment:
1. Test all API endpoints
2. Configure the frontend to use the Railway backend URL
3. Set up monitoring and alerts
4. Configure backup strategies for MongoDB
5. Set up CI/CD pipeline (optional)

---

**Last Updated**: December 2025
**Tested with**: Railway, MongoDB Atlas Free Tier, Python 3.10
