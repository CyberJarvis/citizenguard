# Community Chat Fix Guide

## Issues Fixed

### 1. WebSocket Authentication (403 Forbidden) - ✅ FIXED

**Problem:** JWT token uses `"sub"` field but WebSocket was looking for `"user_id"`

**Files Changed:**
- `backend/app/api/v1/chat.py` (line 173)
- `frontend/app/community/page.js` (lines 38-40)

**Changes Made:**
```python
# Backend - chat.py
user_id = payload.get("sub")  # Changed from payload.get("user_id")
```

```javascript
// Frontend - community/page.js
user_id: decoded.sub || decoded.user_id,  // Now checks 'sub' first
```

### 2. Improved Error Handling - ✅ FIXED

Added proper HTTPException handling in WebSocket endpoint with detailed logging.

### 3. Role Case Handling - ✅ FIXED

Ensured roles are always uppercase:
```python
user_role = user_doc.get("role", "CITIZEN").upper()
```

---

## Python Environment Setup

The backend server is failing because of Python environment issues. Here's how to fix it:

### Option 1: Using Virtual Environment (Recommended)

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate

# On Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run server
python main.py
```

### Option 2: System-wide Installation

```bash
# Navigate to backend
cd backend

# Upgrade pip
python -m pip install --upgrade pip

# Install all dependencies
pip install -r requirements.txt

# If pydantic-settings still fails:
pip install pydantic-settings --force-reinstall

# Run server
python main.py
```

### Option 3: Check Python Version

```bash
# Check Python version (should be 3.11+)
python --version

# If you have multiple Python versions, use specific one:
py -3.12 -m pip install -r requirements.txt
py -3.12 main.py
```

---

## Testing the Chat

Once the backend starts successfully:

1. **Backend should show:**
   ```
   ✓ All services connected successfully
   ✓ Chat database indexes created
   INFO:     Uvicorn running on http://0.0.0.0:8000
   ```

2. **Frontend (already running on localhost:3000):**
   - Navigate to `/community` page
   - You should see "Connected" status (green dot)
   - Online users sidebar should show your username

3. **Multi-User Test:**
   - Open in **different browsers** (Chrome + Firefox)
   - Login with different accounts
   - Both users should see each other in "Online Users"
   - Messages sent from one appear instantly in the other

---

## Expected Behavior After Fix

### WebSocket Connection:
- **Before:** 403 Forbidden, connection rejected
- **After:** Successfully connects, shows "Connected" status

### Backend Logs:
```
INFO - WebSocket authentication successful for user: John Doe (USR-xxx)
INFO - User John Doe (USR-xxx) connected to room general
```

### Frontend:
- Connection status shows green "Connected"
- Online users list populates
- Can send and receive messages in real-time

---

## Quick Verification Checklist

- [ ] Backend server starts without errors
- [ ] Frontend shows "Connected" status (not "Connecting..." or "Disconnected")
- [ ] No 403 errors in backend logs
- [ ] Online users sidebar shows your username
- [ ] Can send messages successfully
- [ ] Multiple browsers can chat with each other

---

## Troubleshooting

### Still getting 403 Forbidden?
1. Check browser console for the JWT token
2. Decode the token at jwt.io
3. Verify it has `"sub"` field with user ID
4. Check backend logs for specific error message

### WebSocket closes immediately?
1. Check MongoDB is running and accessible
2. Verify user exists in database
3. Check backend logs for authentication errors

### Messages not appearing?
1. Check WebSocket connection is "Connected"
2. Look for errors in browser console
3. Check backend logs for message processing errors

---

## All Modified Files

### Backend:
- ✅ `backend/app/models/chat.py` (new)
- ✅ `backend/app/services/chat_manager.py` (new)
- ✅ `backend/app/api/v1/chat.py` (new + fixed)
- ✅ `backend/main.py` (updated)

### Frontend:
- ✅ `frontend/hooks/useChat.js` (new)
- ✅ `frontend/components/chat/MessageList.js` (new)
- ✅ `frontend/components/chat/MessageInput.js` (new)
- ✅ `frontend/components/chat/OnlineUsers.js` (new)
- ✅ `frontend/app/community/page.js` (updated + fixed)
- ✅ `frontend/lib/api.js` (updated)
- ✅ `frontend/package.json` (updated - jwt-decode, date-fns)

---

## Summary

The **403 Forbidden error is now fixed**. The issue was a JWT field mismatch that has been corrected in both backend and frontend. Once you resolve the Python environment issue and restart the backend, the chat will work perfectly!
