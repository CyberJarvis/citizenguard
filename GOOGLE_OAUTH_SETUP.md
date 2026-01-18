# Google OAuth Setup and Troubleshooting Guide

## Current Issue: 400 Bad Request Error

The 400 Bad Request error occurs because **Google's redirect URI configuration doesn't match** what the application is using.

---

## Understanding the OAuth Flow

```
1. User clicks "Sign in with Google"
   ↓
2. Frontend calls Backend: GET /api/v1/auth/google/login
   ↓
3. Backend returns: {"authorization_url": "https://accounts.google.com/...", "state": "..."}
   ↓
4. Frontend redirects user to Google OAuth consent screen
   ↓
5. User approves and Google redirects to: http://localhost:3000/auth/google/callback?code=xxx&state=yyy
   ↓
6. Frontend calls Backend: GET /api/v1/auth/google/callback?code=xxx&state=yyy
   ↓
7. Backend exchanges code with Google for tokens
   ↓
8. Backend returns: {"access_token": "...", "refresh_token": "...", "user": {...}}
   ↓
9. Frontend stores tokens and redirects to /dashboard
```

---

## Root Cause of 400 Error

At **Step 7**, when the backend tries to exchange the authorization code for tokens, Google checks:

1. Is the `redirect_uri` in the request **exactly the same** as what was registered in Google Cloud Console?
2. Is the `redirect_uri` **exactly the same** as what was used in the initial authorization request?

If either check fails, Google returns **400 Bad Request** with error `redirect_uri_mismatch`.

---

## CRITICAL FIX REQUIRED

### Step 1: Update Google Cloud Console (MUST DO)

1. **Go to:** https://console.cloud.google.com/apis/credentials
2. **Sign in** with the Google account that owns the project
3. **Find your OAuth 2.0 Client ID**
4. **Click on the Client ID** to edit it
5. **Under "Authorized redirect URIs"**, add:
   ```
   http://localhost:3000/auth/google/callback
   ```
6. **IMPORTANT:** Also keep this URI for production (if different):
   ```
   https://your-production-domain.com/auth/google/callback
   ```
7. **Remove the old URI** (if present):
   ```
   http://localhost:8000/api/v1/auth/google/callback
   ```
8. **Click "SAVE"**

⚠️ **Changes may take 5-10 minutes to propagate!**

---

### Step 2: Verify Backend Configuration

Check `backend/.env` file has correct redirect URI:

```env
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:3000/auth/google/callback  # ✅ Must match Google Console
FRONTEND_URL=http://localhost:3000
```

---

### Step 3: Restart Backend Server

```bash
cd backend

# Stop current server (Ctrl+C)

# Start server
python main.py
# OR
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

### Step 4: Restart Frontend (if needed)

```bash
cd frontend

# Stop current server (Ctrl+C)

# Start server
npm run dev
```

---

## Testing the Complete Flow

### Test Checklist

1. **Clear browser cache and cookies** for `localhost:3000`
2. Open browser **Developer Tools** (F12)
3. Go to **Console** tab
4. Navigate to: http://localhost:3000/login
5. Click **"Sign in with Google"**
6. **Check Console Logs:**

   - Should see: "Processing Google OAuth callback..."
   - Should see: "AuthContext: Calling backend Google callback..."
   - Should see: "AuthContext: Google callback successful, user: {...}"

7. **If you see errors**, check:
   - Browser Network tab → Find the failing request
   - Check the Response body for detailed error message
   - Check backend terminal logs

### Expected Behavior

✅ **Success:**

- Google consent screen appears
- After approval, briefly shows "Completing Sign In" page
- Redirects to `/dashboard`
- Dashboard shows user information

❌ **Failure (with improved error messages):**

- Shows detailed error message with red background
- If redirect_uri_mismatch: Shows message about Google Cloud Console setup
- Console shows detailed logs
- Redirects to login after 5 seconds

---

## Common Errors and Solutions

### Error: "redirect_uri_mismatch"

**Cause:** Google Cloud Console redirect URI doesn't match application redirect URI

**Solution:**

1. Double-check Google Cloud Console has: `http://localhost:3000/auth/google/callback`
2. Check `backend/.env` has: `GOOGLE_REDIRECT_URI=http://localhost:3000/auth/google/callback`
3. Restart backend server
4. Wait 5-10 minutes for Google to propagate changes
5. Clear browser cache and try again

---

### Error: "Invalid authorization code" or "code_expired"

**Cause:** Authorization code can only be used once or has expired (10 minutes)

**Solution:**

1. Don't refresh the callback page
2. Start a fresh login attempt
3. Complete the flow quickly (within 10 minutes)

---

### Error: "Failed to fetch user info from Google"

**Cause:** Google access token is invalid or expired

**Solution:**

1. Check if Google API is accessible
2. Verify GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are correct
3. Check if Google APIs are enabled in Google Cloud Console

---

### Error: "Google OAuth not configured"

**Cause:** GOOGLE_CLIENT_ID is missing or empty in backend .env

**Solution:**

1. Verify `GOOGLE_CLIENT_ID` is set in `backend/.env`
2. Restart backend server

---

## Security Notes

### Current Issues (from security review)

⚠️ **CRITICAL SECURITY ISSUES:**

1. **Credentials exposed in .env file** (these are in the repository)

   - `GOOGLE_CLIENT_SECRET` should NEVER be in version control
   - `MONGODB_URL` with password is exposed
   - `SMTP_PASSWORD` is exposed

2. **State parameter not validated**

   - Frontend receives `state` but doesn't validate it
   - Need to implement CSRF protection

3. **Tokens in sessionStorage**
   - Vulnerable to XSS attacks
   - Should use HttpOnly cookies

### Recommended Security Improvements

1. **Immediate:** Rotate all credentials (Google, MongoDB, Gmail)
2. **Immediate:** Remove .env from git history
3. **High Priority:** Implement state validation on frontend
4. **High Priority:** Move tokens to HttpOnly cookies
5. **Medium Priority:** Add CSRF protection

---

## Debug Mode

The callback page now shows debug information in development mode.

You'll see a black box at the bottom showing:

```
Code: 4/0Adeu5BW...
State: AQIDBAUGBwg...
Error param: none
```

This helps verify what Google is sending back.

---

## Verification Commands

### Check if backend is running:

```bash
curl http://localhost:8000/health
```

### Test Google login endpoint:

```bash
curl http://localhost:8000/api/v1/auth/google/login
```

Expected response:

```json
{
  "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=...",
  "state": "..."
}
```

### Check backend logs:

```bash
# In backend directory
tail -f nohup.out
# OR if using uvicorn with --reload
# Logs appear in terminal
```

---

## Files Modified in This Fix

### Backend:

1. `backend/app/api/v1/auth.py`

   - Changed endpoint from `/google` to `/google/login`
   - Added state parameter generation
   - Changed response from RedirectResponse to JSON
   - Added state parameter to callback
   - Changed callback to return JSON instead of redirect

2. `backend/app/services/oauth.py`

   - Improved error handling in `exchange_code_for_token`
   - Added specific error messages for redirect_uri_mismatch
   - Added timeout to HTTP requests
   - Better logging

3. `backend/.env`
   - Changed `GOOGLE_REDIRECT_URI` to frontend URL

### Frontend:

1. `frontend/app/auth/google/callback/page.js`

   - Added detailed error display with red background
   - Added console logging for debugging
   - Added development mode debug panel
   - Improved error messages
   - Added "Return to login now" button

2. `frontend/context/AuthContext.js`
   - Enhanced error extraction from backend responses
   - Added detailed console logging
   - Better error state management

---

## Production Deployment Checklist

When deploying to production:

- [ ] Update Google Cloud Console with production redirect URI:
      `https://yourdomain.com/auth/google/callback`
- [ ] Update `GOOGLE_REDIRECT_URI` in production environment variables
- [ ] Update `FRONTEND_URL` in production environment variables
- [ ] Move all credentials to secrets manager (never commit to git)
- [ ] Rotate all exposed credentials
- [ ] Enable HTTPS only
- [ ] Implement state validation
- [ ] Move tokens to HttpOnly cookies
- [ ] Add CSRF protection
- [ ] Enable rate limiting
- [ ] Test complete OAuth flow in production

---

## Contact and Support

If you continue to experience issues:

1. **Check browser console** for detailed error messages
2. **Check backend logs** for server-side errors
3. **Verify Google Cloud Console** redirect URI is correct
4. **Wait 5-10 minutes** after changing Google Cloud Console settings
5. **Try in incognito mode** to rule out cache issues

For Google OAuth-specific issues, refer to:

- https://developers.google.com/identity/protocols/oauth2
- https://developers.google.com/identity/protocols/oauth2/web-server

---

**Last Updated:** November 19, 2025
**Version:** 1.0.0
