# Google Maps API Setup Instructions

## Current Error
```
Google Maps JavaScript API error: ProjectDeniedMapError
```

This error means the Google Maps JavaScript API is not enabled for your API key's project.

---

## Solution: Enable Required APIs

### Step 1: Go to Google Cloud Console
1. Visit: https://console.cloud.google.com/
2. Select your project (or create a new one)

### Step 2: Enable Required APIs
Enable the following APIs for your project:

#### Required APIs:
1. **Maps JavaScript API** (Main requirement)
   - https://console.cloud.google.com/apis/library/maps-backend.googleapis.com

2. **Places API** (Optional - for search autocomplete)
   - https://console.cloud.google.com/apis/library/places-backend.googleapis.com

3. **Geocoding API** (Optional - for address lookup)
   - https://console.cloud.google.com/apis/library/geocoding-backend.googleapis.com

### Step 3: Quick Enable Link
Visit this link and click "Enable" for Maps JavaScript API:
```
https://console.cloud.google.com/apis/library/maps-backend.googleapis.com
```

### Step 4: Verify API Key
1. Go to "Credentials" in Google Cloud Console
2. Find your API key: `AIzaSyBZVA1fI6jGQGK56OWvqAjVM_rslU2pDY8`
3. Click "Edit API key"
4. Under "API restrictions":
   - Select "Restrict key"
   - Check: "Maps JavaScript API"
   - Click "Save"

### Step 5: Wait & Refresh
- API enablement can take 1-5 minutes
- Refresh your app after enabling

---

## Alternative: Create New API Key

If the current key has issues, create a new one:

### 1. Create New API Key
1. Go to: https://console.cloud.google.com/apis/credentials
2. Click "Create Credentials" → "API Key"
3. Copy the new key

### 2. Enable APIs for the Key
- Maps JavaScript API (Required)
- Places API (Optional)
- Geocoding API (Optional)

### 3. Add Restrictions (Recommended)
**HTTP referrers (websites):**
```
http://localhost:3000/*
http://localhost:8000/*
https://yourdomain.com/*
```

**API restrictions:**
- Maps JavaScript API
- Places API
- Geocoding API

### 4. Update .env.local
```env
NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=YOUR_NEW_API_KEY
```

### 5. Restart Dev Server
```bash
cd frontend
npm run dev
```

---

## Billing Information

### Free Tier (No Credit Card Required)
Google Maps provides **$200 free credit per month**, which includes:
- **28,000 map loads** per month
- **40,000 geocoding requests** per month

### For Development
The free tier is more than sufficient for development and small production use.

### Enable Billing (If Needed)
1. Go to: https://console.cloud.google.com/billing
2. Link a billing account
3. Google Maps will use the $200 monthly credit first

---

## Troubleshooting

### Error: "This API project is not authorized to use this API"
**Solution:** Enable Maps JavaScript API (see Step 2 above)

### Error: "API keys with referer restrictions cannot be used"
**Solution:**
- Remove HTTP referrer restrictions during development
- Or add `http://localhost:3000/*` to allowed referrers

### Error: "The provided API key is invalid"
**Solution:**
- Verify the key in Google Cloud Console
- Check `.env.local` has correct key with `NEXT_PUBLIC_` prefix
- Restart dev server after changing .env

### Maps not loading after enabling API
**Solution:**
1. Wait 2-5 minutes for API enablement to propagate
2. Clear browser cache
3. Hard refresh (Ctrl+Shift+R or Cmd+Shift+R)
4. Restart dev server

---

## Current Configuration

**File:** `frontend/.env.local`
```env
NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=AIzaSyBZVA1fI6jGQGK56OWvqAjVM_rslU2pDY8
```

**Status:** ✅ Properly configured with NEXT_PUBLIC_ prefix

**Issue:** ❌ Maps JavaScript API not enabled in Google Cloud Console

---

## Quick Fix Checklist

- [ ] Go to Google Cloud Console
- [ ] Enable "Maps JavaScript API"
- [ ] Wait 2-5 minutes
- [ ] Refresh browser
- [ ] Check console for errors
- [ ] If still failing, create new API key

---

## Need Help?

If you're still having issues:

1. **Check API Status**
   - https://console.cloud.google.com/apis/dashboard
   - Verify "Maps JavaScript API" shows as "Enabled"

2. **Check API Key**
   - https://console.cloud.google.com/apis/credentials
   - Verify key exists and has correct restrictions

3. **Check Browser Console**
   - Open DevTools (F12)
   - Look for detailed error messages
   - Share error message for debugging

---

## Documentation Links

- Google Maps JavaScript API: https://developers.google.com/maps/documentation/javascript
- Error Messages: https://developers.google.com/maps/documentation/javascript/error-messages
- API Key Best Practices: https://developers.google.com/maps/api-key-best-practices
