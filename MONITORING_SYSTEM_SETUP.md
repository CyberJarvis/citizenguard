# ML-Powered Hazard Monitoring System - Setup Guide

## Overview

This system adds **real-time ML-powered hazard detection** to the BlueRadar 2.0 platform, displaying predicted hazards from 14 monitored coastal locations across South Asia alongside user-reported hazards.

### What's Been Implemented

✅ **Backend API** (FastAPI)
- `/api/v1/monitoring/current` - Get all current hazard data
- `/api/v1/monitoring/locations` - List monitored locations
- `/api/v1/monitoring/location/{id}` - Detailed location data
- `/api/v1/monitoring/earthquakes/recent` - Recent earthquakes
- `/api/v1/monitoring/alerts/active` - Active alerts (warning+)
- `/api/v1/monitoring/summary` - Summary statistics
- `/api/v1/monitoring/health` - System health check

✅ **ML Monitor Service** (Mock Data - Ready for Integration)
- 14 monitored locations (Mumbai, Chennai, Port Blair, etc.)
- 4 hazard types: Tsunami, Cyclone, High Waves, Flood
- Alert levels 1-5 (Normal to Critical)
- Earthquake data integration
- Auto-refresh every 5 minutes

✅ **Enhanced Map Page** (React + Leaflet)
- Color-coded markers by alert level
- Interactive popups with hazard details
- Side panel with alert statistics
- Advanced filters (hazard types, alert levels)
- Earthquake markers
- Auto-refresh (5 minutes)
- Pulsing animations for critical alerts
- Real-time notifications
- User-reported hazards + ML-detected hazards

---

## File Structure

### Backend Files Created

```
backend/
├── app/
│   ├── models/
│   │   └── monitoring.py          # Monitoring data models (304 lines)
│   ├── api/
│   │   └── v1/
│   │       └── monitoring.py      # API endpoints (202 lines)
│   └── services/
│       └── ml_monitor.py          # ML monitoring service (550+ lines)
└── main.py                        # Updated to include monitoring router
```

### Frontend Files

```
frontend/
├── app/
│   └── map/
│       ├── page.js                # Enhanced map (replaces old version)
│       ├── enhanced-page.js       # Source file for new map
│       └── page-backup.js         # Backup of original map
└── lib/
    └── api.js                     # Updated with monitoring API functions
```

---

## Installation & Setup

### 1. Backend Setup

#### Install Dependencies

```bash
cd backend

# Create and activate virtual environment (if not already done)
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate

# Install all requirements
pip install -r requirements.txt
```

**Required packages for monitoring system:**
- `fastapi>=0.109.0`
- `motor>=3.3.2` (MongoDB async driver)
- `pydantic>=2.5.3` (Data validation)
- All other dependencies from `requirements.txt`

#### Configuration

Ensure your `.env` file includes:

```env
# MongoDB (Required)
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=CoastGuardian

# API Configuration
API_PREFIX=/api/v1

# Optional: Redis for caching
REDIS_HOST=localhost
REDIS_PORT=6379
```

#### Start Backend

```bash
cd backend

# Option 1: Using uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Option 2: Using Python
python main.py
```

The backend will:
1. Connect to MongoDB
2. Initialize ML Monitor Service
3. Run initial hazard detection
4. Start auto-refresh every 5 minutes
5. Serve API at `http://localhost:8000`

#### Test Backend

```bash
# Health check
curl http://localhost:8000/health

# Monitoring health
curl http://localhost:8000/api/v1/monitoring/health

# Get monitoring data
curl http://localhost:8000/api/v1/monitoring/current

# Get locations
curl http://localhost:8000/api/v1/monitoring/locations

# API Documentation
open http://localhost:8000/docs
```

### 2. Frontend Setup

#### Install Dependencies

```bash
cd frontend

# Install packages (if not already done)
npm install

# The monitoring system uses existing dependencies:
# - leaflet@1.9.4
# - react-leaflet@5.0.0
# - axios@1.13.2
# - react-hot-toast@2.6.0
```

#### Start Frontend

```bash
cd frontend

npm run dev
```

Frontend runs at: `http://localhost:3000`

#### Access Enhanced Map

Navigate to: `http://localhost:3000/map`

The map will automatically:
1. Fetch ML-detected hazards
2. Fetch user-reported hazards
3. Fetch recent earthquakes
4. Auto-refresh every 5 minutes
5. Display alert statistics in side panel

---

## Features Explained

### 1. Color-Coded Markers

| Alert Level | Color | Status | Visual |
|-------------|-------|--------|--------|
| 5 | Red (#DC2626) | CRITICAL | 40px, pulsing |
| 4 | Orange (#F97316) | HIGH | 35px |
| 3 | Yellow (#FCD34D) | WARNING | 30px |
| 2 | Blue (#60A5FA) | LOW | 25px |
| 1 | Green (#10B981) | NORMAL | 25px |

### 2. Hazard Types

**ML-Detected Hazards:**
- 🌊 Tsunami (with probability %)
- 🌀 Cyclone (with category)
- 🌊 High Waves (with beach flag)
- 💧 Flood (with flood score)

**User-Reported Hazards:**
- All existing hazard types from citizen reports

### 3. Monitored Locations

The system monitors 14 coastal locations:

1. **Mumbai, India** - Population: 12.4M
2. **Chennai, India** - Population: 7.1M
3. **Kolkata, India** - Population: 4.5M
4. **Visakhapatnam, India** - Population: 2.0M
5. **Kochi, India** - Population: 2.1M
6. **Port Blair, India** - Population: 100K
7. **Puducherry, India** - Population: 244K
8. **Goa, India** - Population: 1.5M
9. **Mangalore, India** - Population: 624K
10. **Thiruvananthapuram, India** - Population: 958K
11. **Karachi, Pakistan** - Population: 14.9M
12. **Dhaka, Bangladesh** - Population: 8.9M
13. **Colombo, Sri Lanka** - Population: 753K
14. **Male, Maldives** - Population: 133K

### 4. Side Panel Statistics

The side panel shows:
- **Alert Summary**: Count by level (Critical, High, Warning, Normal)
- **Active Hazards**: Count by type (Tsunami, Cyclone, etc.)
- **Affected Regions**: Top 5 locations with highest alerts

### 5. Filters

Users can filter by:
- **Layers**: ML Detections, User Reports, Earthquakes
- **Hazard Types**: Tsunami, Cyclone, High Waves, Flood
- **Alert Level**: Minimum level to display (1-5)

### 6. Auto-Refresh

- **Interval**: 5 minutes
- **Indicator**: Refresh button shows spinning animation
- **Manual Refresh**: Click refresh button anytime
- **Update Time**: Displayed in side panel

### 7. Notifications

- **Critical Alerts**: Toast notification when Level 5 detected
- **Duration**: 10 seconds
- **Sound**: Can be added (optional)
- **Browser**: Can request notification permission

---

## Integrating Real ML Model

The current implementation uses **mock data** for demonstration. To integrate your actual ML model:

### Step 1: Locate ML Model Integration Point

File: `backend/app/services/ml_monitor.py`

Function: `_run_ml_model()` (Lines 150-272)

```python
async def _run_ml_model(self) -> Dict:
    """
    Run ML model for hazard detection.

    TODO: Replace this with actual ML model integration.
    Currently returns mock data for demonstration.
    """
    # YOUR ML MODEL CODE HERE
```

### Step 2: Replace Mock Data

**Current Mock Implementation:**
```python
# Generate random hazards
tsunami_prob = random.random() * 0.3
if tsunami_prob > 0.1:
    hazards["tsunami"] = {
        "alert_level": alert_level,
        "probability": round(tsunami_prob, 2),
        ...
    }
```

**Replace with Real ML Model:**
```python
# Import your ML model
from your_ml_package import HazardPredictor

# Initialize model (do this in __init__)
self.ml_model = HazardPredictor()

# In _run_ml_model():
async def _run_ml_model(self) -> Dict:
    hazards_by_location = {}

    for loc_id, loc_config in self.locations_config.items():
        # Get real-time data
        weather_data = await fetch_weather(loc_config["coordinates"])
        seismic_data = await fetch_seismic_data(loc_config["coordinates"])

        # Run ML prediction
        predictions = self.ml_model.predict(
            location=loc_config,
            weather=weather_data,
            seismic=seismic_data
        )

        # Format predictions to match schema
        hazards = {}

        if predictions["tsunami_probability"] > 0.1:
            hazards["tsunami"] = {
                "alert_level": self._probability_to_alert_level(predictions["tsunami_probability"]),
                "probability": predictions["tsunami_probability"],
                "estimated_arrival_minutes": predictions.get("tsunami_eta"),
                "wave_height_meters": predictions.get("wave_height")
            }

        # Repeat for cyclone, high_waves, flood...

        hazards_by_location[loc_id] = hazards

    return hazards_by_location
```

### Step 3: Integrate Earthquake API

File: `backend/app/services/ml_monitor.py`

Function: `_fetch_earthquake_data()` (Lines 274-334)

**Replace mock data with USGS API:**

```python
async def _fetch_earthquake_data(self) -> List[EarthquakeData]:
    """Fetch real earthquake data from USGS"""
    import httpx

    # USGS Earthquake API
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    params = {
        "format": "geojson",
        "starttime": (datetime.utcnow() - timedelta(days=1)).isoformat(),
        "minmagnitude": 4.0,
        "minlatitude": 0,
        "maxlatitude": 25,
        "minlongitude": 65,
        "maxlongitude": 95
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        data = response.json()

    earthquakes = []
    for feature in data["features"]:
        props = feature["properties"]
        coords = feature["geometry"]["coordinates"]

        earthquakes.append(
            EarthquakeData(
                earthquake_id=feature["id"],
                magnitude=props["mag"],
                depth_km=coords[2],
                coordinates=Coordinates(lat=coords[1], lon=coords[0]),
                location_description=props["place"],
                timestamp=datetime.fromtimestamp(props["time"] / 1000),
                distance_from_coast_km=None  # Calculate if needed
            )
        )

    return earthquakes
```

---

## API Endpoints Reference

### GET `/api/v1/monitoring/current`

Returns complete monitoring data.

**Response:**
```json
{
  "locations": {
    "mumbai": {
      "location_id": "mumbai",
      "name": "Mumbai",
      "country": "India",
      "coordinates": {"lat": 19.076, "lon": 72.8777},
      "population": 12442373,
      "current_hazards": {
        "tsunami": {
          "alert_level": 5,
          "probability": 0.85,
          "estimated_arrival_minutes": 45,
          "wave_height_meters": 3.5
        },
        "cyclone": {
          "alert_level": 3,
          "category": "STORM",
          "wind_speed_kmh": 85.5,
          "distance_km": 120.3,
          "direction": "NE"
        }
      },
      "max_alert": 5,
      "status": "CRITICAL",
      "recommendations": [
        "⚠️ EVACUATE coastal areas immediately",
        "Move to higher ground (>30m elevation)",
        "🌊 Tsunami threat - move inland immediately"
      ],
      "last_updated": "2025-11-21T18:30:00Z"
    }
  },
  "summary": {
    "total_locations": 14,
    "critical_alerts": 2,
    "high_alerts": 3,
    "warning_alerts": 2,
    "low_alerts": 3,
    "normal_alerts": 4,
    "active_tsunamis": 2,
    "active_cyclones": 3,
    "active_high_waves": 8,
    "active_floods": 1,
    "last_updated": "2025-11-21T18:30:00Z"
  },
  "recent_earthquakes": [
    {
      "earthquake_id": "eq_abc123",
      "magnitude": 6.2,
      "depth_km": 45.5,
      "coordinates": {"lat": 15.5, "lon": 75.2},
      "location_description": "200km from coast",
      "timestamp": "2025-11-21T15:20:00Z",
      "distance_from_coast_km": 200.0
    }
  ]
}
```

### GET `/api/v1/monitoring/locations`

Returns list of monitored locations (basic info).

**Response:**
```json
[
  {
    "location_id": "mumbai",
    "name": "Mumbai",
    "country": "India",
    "coordinates": {"lat": 19.076, "lon": 72.8777},
    "population": 12442373
  }
]
```

### GET `/api/v1/monitoring/location/{location_id}`

Returns detailed data for specific location.

### GET `/api/v1/monitoring/earthquakes/recent`

**Query Parameters:**
- `hours` (default: 24) - Look back hours
- `min_magnitude` (default: 4.0) - Minimum magnitude

### GET `/api/v1/monitoring/alerts/active`

Returns locations with active alerts (Level 3+).

**Query Parameters:**
- `min_level` (default: 3) - Minimum alert level

### GET `/api/v1/monitoring/summary`

Returns summary statistics only.

### GET `/api/v1/monitoring/health`

Returns monitoring system health status.

**Response:**
```json
{
  "status": "healthy",
  "last_update": "2025-11-21T18:30:00Z",
  "is_running": false,
  "model_version": "1.0.0",
  "monitored_locations": 14,
  "timestamp": "2025-11-21T18:35:00Z"
}
```

---

## Troubleshooting

### Backend Issues

**"ModuleNotFoundError: No module named 'redis'"**
```bash
pip install redis>=5.0.1
```

**"Connection refused - MongoDB"**
- Ensure MongoDB is running: `mongod`
- Check connection string in `.env`

**"Monitoring service not updating"**
- Check logs for errors
- Verify background task is running
- Check `/api/v1/monitoring/health`

### Frontend Issues

**"Map not loading"**
- Check browser console for errors
- Ensure backend is running at `http://localhost:8000`
- Check CORS settings in backend

**"No markers showing"**
- Check filters are enabled
- Ensure backend is returning data
- Check browser console for API errors

**"Old map still showing"**
```bash
# Clear Next.js cache
cd frontend
rm -rf .next
npm run dev
```

---

## Performance Optimization

### Backend

1. **MongoDB Indexes** (Add these):
```javascript
// In MongoDB shell
db.monitoring_locations.createIndex({ location_id: 1 })
db.hazard_detections.createIndex({ location_id: 1, timestamp: -1 })
```

2. **Caching**:
- Enable Redis for response caching
- Cache monitoring data for 4 minutes

3. **Background Tasks**:
- Use Celery for scheduled ML runs (optional)
- Implement WebSocket for real-time updates

### Frontend

1. **Map Performance**:
- Already using marker clustering
- Lazy loading popups (on-click only)
- Debounced filters (300ms)

2. **API Calls**:
- Cache responses client-side
- Use React Query for better caching
- Implement WebSocket to reduce polling

---

## Next Steps

### Immediate

1. ✅ Integrate real ML model (replace mock data)
2. ✅ Connect to earthquake API (USGS)
3. ✅ Test with MongoDB running
4. ✅ Add weather API integration
5. ✅ Deploy to production

### Future Enhancements

1. **WebSocket Support**:
   - Real-time updates without polling
   - Instant alert notifications
   - Live marker updates

2. **Historical Data**:
   - Store detection results in MongoDB
   - Show hazard trends over time
   - Alert frequency graphs

3. **User Notifications**:
   - Email alerts for subscribed locations
   - SMS for critical alerts
   - Push notifications (PWA)

4. **Advanced Analytics**:
   - Prediction accuracy tracking
   - False positive rate monitoring
   - ML model performance metrics

5. **Mobile App**:
   - React Native version
   - Offline capability
   - Location-based alerts

---

## Support

- **Documentation**: See `hazard-detection.md` for system architecture
- **API Docs**: `http://localhost:8000/docs` (when backend running)
- **Issues**: Check logs in `backend/` folder
- **Questions**: Contact development team

---

## License

Part of BlueRadar 2.0 (CoastGuardian) - INCOIS SIH 2025

**Built with:**
- FastAPI (Python)
- Next.js (React)
- Leaflet (Maps)
- MongoDB (Database)
- OpenStreetMap (Tiles)
