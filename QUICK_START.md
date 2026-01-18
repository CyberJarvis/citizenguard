# BlueRadar 2.0 - ML Hazard Monitoring - Quick Start Guide

## ✅ Backend is Running!

The backend has been successfully started and is serving hazard monitoring data.

### Backend Status
- **URL:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **Status:** ✅ Running
- **MongoDB:** ✅ Connected
- **ML Service:** ✅ Initialized (14 locations monitored)
- **Mock Data:** ✅ Active (5 critical alerts detected)

### Test the API

```bash
# Health check
curl http://localhost:8000/health

# Monitoring health
curl http://localhost:8000/api/v1/monitoring/health

# Get all monitoring data
curl http://localhost:8000/api/v1/monitoring/current

# Get locations list
curl http://localhost:8000/api/v1/monitoring/locations

# Get summary
curl http://localhost:8000/api/v1/monitoring/summary
```

---

## 🚀 Starting the Frontend

### Step 1: Open new terminal

```bash
cd D:\blueradar-2.0\frontend
```

### Step 2: Start the development server

```bash
npm run dev
```

### Step 3: Access the application

Open your browser and navigate to:
- **Main App:** http://localhost:3000
- **Enhanced Map:** http://localhost:3000/map

---

## 🗺️ Using the Enhanced Map

Once the frontend is running, the map will:

1. **Auto-load data:**
   - ML-detected hazards from 14 locations
   - User-reported hazards
   - Recent earthquakes

2. **Display features:**
   - Color-coded markers (red=critical, orange=high, yellow=warning, blue/green=low/normal)
   - Pulsing animations for critical alerts
   - Interactive popups with detailed hazard information
   - Side panel with alert statistics
   - Filters for hazard types and alert levels

3. **Auto-refresh:**
   - Data refreshes every 5 minutes automatically
   - Manual refresh button available

---

## 🎨 What You'll See on the Map

### Markers

**ML-Detected Hazards (Circles with Numbers):**
- 🔴 Level 5 (CRITICAL) - 40px, pulsing, red
- 🟠 Level 4 (HIGH) - 35px, orange
- 🟡 Level 3 (WARNING) - 30px, yellow
- 🔵 Level 2 (LOW) - 25px, blue
- 🟢 Level 1 (NORMAL) - 25px, green

**User Reports (Colored Pins):**
- Various colors based on hazard type
- Pin shape pointing to location

**Earthquakes (Circles):**
- Sized by magnitude (larger = stronger)
- Color: Yellow (4-6), Orange (6-7), Red (7+)

### Side Panel (Desktop)

Shows real-time statistics:
- Critical alerts count
- High alerts count
- Warning alerts count
- Normal alerts count
- Active hazards by type
- Affected regions list

### Filters

Toggle visibility:
- ML Detections (on/off)
- User Reports (on/off)
- Earthquakes (on/off)
- Hazard types (tsunami, cyclone, high waves, flood)
- Minimum alert level (1-5)

---

## 🔧 Troubleshooting

### Backend not starting?

Make sure MongoDB is running:
```bash
# Check if MongoDB is running
# If using MongoDB Atlas (cloud), it's already running
# If using local MongoDB:
mongod
```

### Frontend can't connect to backend?

1. Check backend is running at http://localhost:8000
2. Check CORS settings (already configured for localhost:3000)
3. Check browser console for errors

### No markers showing on map?

1. Open browser console (F12)
2. Check for API errors
3. Verify backend is returning data: http://localhost:8000/api/v1/monitoring/current
4. Check filters are enabled (click Filters button)

### Map not loading?

1. Clear browser cache
2. Check browser console for errors
3. Ensure Leaflet CSS is loading
4. Try hard refresh (Ctrl+F5)

---

## 📊 Sample Data

The system currently shows **MOCK DATA** for demonstration:

### 14 Monitored Locations:
1. Mumbai, India - Population: 12.4M
2. Chennai, India - Population: 7.1M
3. Kolkata, India - Population: 4.5M
4. Visakhapatnam, India - Population: 2.0M
5. Kochi, India - Population: 2.1M
6. Port Blair, Andaman Islands - Population: 100K
7. Puducherry, India - Population: 244K
8. Goa, India - Population: 1.5M
9. Mangalore, India - Population: 624K
10. Thiruvananthapuram, India - Population: 958K
11. Karachi, Pakistan - Population: 14.9M
12. Dhaka, Bangladesh - Population: 8.9M
13. Colombo, Sri Lanka - Population: 753K
14. Male, Maldives - Population: 133K

### Hazard Types Detected:
- 🌊 Tsunami (with probability %)
- 🌀 Cyclone (with category)
- 🌊 High Waves (with beach flag color)
- 💧 Flood (with flood score)

### Recent Earthquakes:
- 3-7 random earthquakes in the region
- Magnitude 4.0-7.5
- Within last 24 hours

---

## 🔄 How to Integrate Real ML Model

See `MONITORING_SYSTEM_SETUP.md` for detailed instructions.

**Quick overview:**
1. Open `backend/app/services/ml_monitor.py`
2. Find the `_run_ml_model()` function (line ~150)
3. Replace mock data generation with your ML model calls
4. Ensure output format matches the expected structure

**Expected output format:**
```python
{
    "location_id": {
        "tsunami": {
            "alert_level": 1-5,
            "probability": 0.0-1.0,
            ...
        },
        "cyclone": {...},
        "high_waves": {...},
        "flood": {...}
    }
}
```

---

## 🎯 Next Steps

1. ✅ Backend running with mock data
2. ✅ Start frontend: `npm run dev`
3. ✅ Test map at http://localhost:3000/map
4. ✅ Verify all features working
5. 🔄 Replace mock data with real ML model
6. 🔄 Connect to real earthquake API (USGS)
7. 🔄 Deploy to production

---

## 📞 Quick Reference

### Backend Commands
```bash
# Start backend
cd D:\blueradar-2.0\backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or use the full Python path:
"C:\Users\AKASH VISHWAKARMA\AppData\Local\Programs\Python\Python312\python.exe" -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Commands
```bash
# Start frontend
cd D:\blueradar-2.0\frontend
npm run dev

# Build for production
npm run build

# Start production server
npm start
```

### API Endpoints
- Health: http://localhost:8000/health
- API Docs: http://localhost:8000/docs
- Monitoring: http://localhost:8000/api/v1/monitoring/current
- Locations: http://localhost:8000/api/v1/monitoring/locations
- Earthquakes: http://localhost:8000/api/v1/monitoring/earthquakes/recent

---

## ✨ Features Included

### Backend
✅ 8 REST API endpoints
✅ Real-time hazard detection service
✅ Background auto-refresh (5 minutes)
✅ 14 monitored coastal locations
✅ 4 hazard types (tsunami, cyclone, waves, flood)
✅ 5 alert levels (normal to critical)
✅ Earthquake data integration
✅ Health monitoring
✅ Error handling
✅ CORS configured
✅ OpenAPI documentation

### Frontend
✅ Interactive Leaflet map
✅ Color-coded markers by alert level
✅ ML detection layer
✅ User reports layer
✅ Earthquake markers
✅ Pulsing animations for critical alerts
✅ Interactive popups
✅ Side panel with statistics
✅ Advanced filters
✅ Search functionality
✅ Auto-refresh (5 min)
✅ Manual refresh button
✅ Toast notifications
✅ Geolocation
✅ Legend
✅ Responsive design

---

**🎉 You're ready to use the ML Hazard Monitoring System!**

Happy monitoring! 🌊🗺️
