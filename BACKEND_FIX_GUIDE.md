# Backend Not Starting - Complete Fix Guide

## Problem
Your backend server isn't running due to PyOpenSSL/cryptography version conflicts in your Anaconda environment. **This is why notifications don't appear.**

## Root Cause
```
AttributeError: module 'lib' has no attribute 'X509_V_FLAG_NOTIFY_POLICY'
```

This happens when:
- PyOpenSSL < 23.2.0 (your version)
- cryptography >= 42.0.0 (your version)
- Using Anaconda environment (conflict source)

## ✅ SOLUTION 1: Clean Virtual Environment (RECOMMENDED)

1. **Open Command Prompt AS ADMINISTRATOR**

2. **Navigate to backend**:
   ```bash
   cd D:\blueradar-2.0\backend
   ```

3. **Create fresh virtual environment** (NOT Anaconda):
   ```bash
   python -m venv venv
   ```

4. **Activate virtual environment**:
   ```bash
   venv\Scripts\activate
   ```

5. **Install dependencies**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

6. **Upgrade problem packages**:
   ```bash
   pip install --upgrade pyopenssl>=23.2.0 cryptography>=42.0.0
   ```

7. **Start backend**:
   ```bash
   python main.py
   ```

8. **Verify it's running**: You should see:
   ```
   ✓ MongoDB connected
   ✓ ML Monitoring Service initialized
   ✓ Notification database indexes created
   INFO: Uvicorn running on http://localhost:8000
   ```

## ✅ SOLUTION 2: Fix Anaconda Environment

1. **Open Anaconda Prompt AS ADMINISTRATOR**

2. **Navigate to backend**:
   ```bash
   cd D:\blueradar-2.0\backend
   ```

3. **Update conda**:
   ```bash
   conda update conda
   ```

4. **Install correct versions**:
   ```bash
   conda install -c conda-forge pyopenssl=23.2.0
   conda install -c conda-forge cryptography
   ```

5. **Start backend**:
   ```bash
   python main.py
   ```

## ✅ SOLUTION 3: Use Docker (Best for Production)

If you continue having issues, use Docker:

```bash
cd D:\blueradar-2.0

# Build and run with docker-compose
docker-compose up -d
```

## 🔍 Verification Steps

### 1. Check Backend is Running

Open browser and go to:
```
http://localhost:8000/docs
```

You should see FastAPI Swagger documentation.

### 2. Test Notifications API

In browser console (F12), run:
```javascript
fetch('http://localhost:8000/api/v1/notifications/stats', {
  headers: {
    'Authorization': 'Bearer YOUR_ACCESS_TOKEN_HERE'
  }
})
.then(r => r.json())
.then(console.log)
```

### 3. Test Alert Creation

As authority user:
1. Go to `/authority/alerts/create`
2. Create an alert for a region (e.g., "Tamil Nadu")
3. Check browser console for errors
4. Check backend terminal for logs

You should see:
```
INFO: Alert created: ALT-20251124-XXXXXXXX by authority_user_id
INFO: Created XX notifications for alert ALT-20251124-XXXXXXXX
```

### 4. Check Notifications Appear

As citizen user:
1. Click notification bell in header
2. Should show unread notifications
3. Check `/notifications` page

## 🐛 Debugging Steps

### Check Browser Console

1. Press F12 in browser
2. Go to Console tab
3. Look for errors when:
   - Page loads
   - Clicking notification bell
   - Opening notifications page

Common errors:
- `Failed to fetch` → Backend not running
- `401 Unauthorized` → Authentication issue
- `Network error` → Wrong API URL

### Check Network Tab

1. Press F12 → Network tab
2. Click notification bell
3. Look for requests to:
   - `/api/v1/notifications/stats` → Should return 200
   - `/api/v1/notifications` → Should return 200

If 404/500 → Backend not running or router not registered

### Check Backend Logs

When backend IS running, you'll see:
```
INFO: Started server process
INFO: Waiting for application startup.
INFO: Application startup complete.
INFO: Uvicorn running on http://localhost:8000
```

## 📝 Manual Database Check

To verify notifications in database manually:

1. **Open MongoDB Compass** or **mongosh**

2. **Connect to**: `mongodb://localhost:27017`

3. **Select database**: `coastguardian`

4. **Check collections**:

   ```javascript
   // Check users (should have location data)
   db.users.find({role: "citizen"}).limit(5)

   // Check alerts
   db.alerts.find({}).sort({created_at: -1}).limit(5)

   // Check notifications
   db.notifications.find({}).sort({created_at: -1}).limit(10)
   ```

5. **What to look for**:
   - Users should have `location.region` or `location.state`
   - Alerts should have `regions` array
   - Notifications should have `user_id` matching citizens in those regions

## 🚨 Common Issues After Backend Starts

### Issue 1: Notifications Created But Not Showing

**Cause**: User doesn't have location set

**Fix**: Update user profile with location:
```javascript
// In browser console as logged-in citizen
fetch('http://localhost:8000/api/v1/profile/me', {
  method: 'PUT',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer YOUR_TOKEN'
  },
  body: JSON.stringify({
    location: {
      region: "Tamil Nadu",
      state: "Tamil Nadu",
      latitude: 13.0827,
      longitude: 80.2707
    }
  })
})
```

### Issue 2: Alert Created But No Notifications

**Cause**: Alert region doesn't match any user's region

**Fix**:
1. Check alert regions match user locations EXACTLY (case-sensitive)
2. Or update user locations to match

### Issue 3: Frontend Not Fetching

**Cause**: CORS or authentication error

**Fix**: Check browser console for specific error

## ✅ Success Checklist

- [ ] Backend starts without errors
- [ ] Can access http://localhost:8000/docs
- [ ] Can see API endpoints in Swagger
- [ ] MongoDB is connected
- [ ] Frontend is running on http://localhost:3000
- [ ] Can login as citizen
- [ ] Can login as authority
- [ ] Authority can create alerts
- [ ] Notifications appear in database
- [ ] Notification bell shows unread count
- [ ] Clicking bell shows notifications
- [ ] /notifications page works

## 🎯 Next Steps After Fix

1. **Start backend** (use Solution 1 above)
2. **Start frontend**: `cd frontend && npm run dev`
3. **Login as authority** → Create test alert
4. **Login as citizen** → Check notification bell
5. **If still issues** → Share:
   - Backend terminal output
   - Browser console errors
   - MongoDB data (users/alerts/notifications collections)

## 📞 Need Help?

If you're still stuck, provide:
1. Screenshot of backend terminal when starting
2. Screenshot of browser console errors
3. Screenshot of MongoDB data (users, alerts, notifications)
4. Your Python version: `python --version`
5. Your environment (Anaconda/venv/system Python)
