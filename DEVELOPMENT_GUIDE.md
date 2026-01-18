# CoastGuardians - Complete Development Guide
## Smart India Hackathon 2025 | Ocean Hazards Crowdsourcing for INCOIS

**Version:** 1.0
**Last Updated:** December 1, 2025
**Branch:** VerificationLoop

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture](#2-architecture)
3. [Technology Stack](#3-technology-stack)
4. [Project Structure](#4-project-structure)
5. [Key Features](#5-key-features)
6. [Getting Started](#6-getting-started)
7. [Backend API Reference](#7-backend-api-reference)
8. [Mobile API Endpoints](#8-mobile-api-endpoints)
9. [External APIs](#9-external-apis)
10. [Database Schema](#10-database-schema)
11. [Development Workflow](#11-development-workflow)
12. [Troubleshooting](#12-troubleshooting)

---

## 1. Project Overview

**CoastGuardians** is an Ocean Hazards Crowdsourcing platform developed for INCOIS (Indian National Centre for Ocean Information Services) as part of Smart India Hackathon 2025.

### Mission
Enable citizens to report ocean hazards in real-time, verified through a 6-layer AI pipeline, and monitored by authorities to issue timely alerts.

### Key Capabilities
- Citizen hazard reporting with image/voice capture
- 6-layer AI verification pipeline
- Real-time multi-hazard monitoring (Tsunami, Cyclone, Waves, Floods, Rip Currents)
- Interactive ocean map with ESRI basemaps
- 3-way ticketing system (Reporter-Analyst-Authority)
- Push notifications and SMS alerts

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                                │
├─────────────────┬─────────────────┬─────────────────────────────────┤
│   Web App       │   Mobile App    │   Authority Dashboard           │
│   (Next.js)     │   (Future)      │   (Next.js)                     │
└────────┬────────┴────────┬────────┴────────┬────────────────────────┘
         │                 │                 │
         └─────────────────┼─────────────────┘
                           │
                    ┌──────▼──────┐
                    │  FastAPI    │
                    │  Backend    │
                    └──────┬──────┘
                           │
    ┌──────────────────────┼──────────────────────┐
    │                      │                      │
┌───▼───┐           ┌──────▼──────┐        ┌─────▼─────┐
│MongoDB│           │    Redis    │        │ TensorFlow│
│  DB   │           │   Cache     │        │  + FAISS  │
└───────┘           └─────────────┘        └───────────┘
                                                 │
                    ┌────────────────────────────┤
                    │                            │
              ┌─────▼─────┐              ┌───────▼───────┐
              │  Vision   │              │  VectorDB     │
              │  Model    │              │  (Text Class) │
              └───────────┘              └───────────────┘
```

### Data Flow
1. **Citizen** submits hazard report (image + description + location)
2. **Verification Service** runs 6-layer AI pipeline
3. **Auto-Decision**: ≥75% = Approve, 40-75% = Manual Review, <40% = Reject
4. **Verified reports** displayed on public map
5. **Authorities** create alerts based on reports
6. **Citizens** receive push/SMS notifications

---

## 3. Technology Stack

### Backend
| Technology | Purpose | Version |
|------------|---------|---------|
| FastAPI | REST API framework | 0.104+ |
| MongoDB | Primary database | 6.0+ |
| Redis | Caching, OTP, sessions | 7.0+ |
| TensorFlow/Keras | Image classification | 2.15+ |
| FAISS | Text classification | 1.7+ |
| Whisper | Voice transcription | OpenAI |
| JWT + bcrypt | Authentication | - |
| Twilio | SMS notifications | - |

### Frontend
| Technology | Purpose | Version |
|------------|---------|---------|
| Next.js | React framework | 16.x |
| React | UI library | 19.x |
| TailwindCSS | Styling | 4.x |
| Leaflet | Interactive maps | 1.9+ |
| ESRI Basemaps | Ocean visualization | - |
| Zustand | State management | 4.x |
| ApexCharts | Analytics charts | - |

### External Services
| Service | Purpose |
|---------|---------|
| WeatherAPI.com | Weather data |
| Open-Meteo Marine | Wave/ocean data |
| USGS Earthquake | Seismic data |
| Google OAuth | Social login |
| Firebase | Push notifications |

---

## 4. Project Structure

```
coastGuardians/
├── backend/                    # FastAPI Backend
│   ├── app/
│   │   ├── api/v1/            # API Routes (17 routers, 80+ endpoints)
│   │   │   ├── auth.py        # Authentication (signup, login, OTP, OAuth)
│   │   │   ├── hazards.py     # Hazard reporting + ocean-data endpoint
│   │   │   ├── verification.py # 6-layer verification pipeline
│   │   │   ├── tickets.py     # 3-way ticketing system
│   │   │   ├── alerts.py      # Authority alerts
│   │   │   ├── multi_hazard.py # Real-time monitoring
│   │   │   ├── notifications.py # Push/SMS notifications
│   │   │   ├── profile.py     # User profile management
│   │   │   └── ...
│   │   ├── models/            # Pydantic/MongoDB models
│   │   ├── services/          # Business logic (23 services)
│   │   │   ├── verification_service.py  # 6-layer AI pipeline
│   │   │   ├── multi_hazard_service.py  # Real-time detection
│   │   │   ├── vision_service.py        # TensorFlow image classification
│   │   │   ├── vectordb_service.py      # FAISS text classification
│   │   │   ├── weather_service.py       # Weather API integration
│   │   │   └── ...
│   │   └── middleware/        # CORS, RBAC, security
│   ├── main.py                # FastAPI entry point
│   ├── Vision_Model/          # TensorFlow trained model
│   └── requirements.txt       # Python dependencies
│
├── frontend/                   # Next.js Frontend
│   ├── app/                   # Pages (48 routes)
│   │   ├── map/page.js        # Interactive ocean map
│   │   ├── report-hazard/     # Hazard reporting wizard
│   │   ├── authority/         # Authority dashboard
│   │   ├── analyst/           # Analyst verification panel
│   │   └── admin/             # Admin dashboard
│   ├── components/
│   │   ├── map/               # Map components
│   │   │   ├── OceanMap.js    # Main map (Leaflet + ESRI)
│   │   │   ├── WaveTrackLayer.js # Ocean waves/currents
│   │   │   ├── CycloneLayer.js   # Cyclone visualization
│   │   │   ├── HeatmapLayer.js   # Hazard density heatmap
│   │   │   └── MapControls.js    # Layer controls
│   │   └── ...
│   ├── lib/api.js             # Axios API client
│   ├── hooks/                 # Custom React hooks
│   └── styles/                # CSS styles
│
├── CLAUDE_CONTEXT.md          # Claude session context
├── MOBILE_API_ENDPOINTS.md    # Mobile API documentation
└── DEVELOPMENT_GUIDE.md       # This file
```

---

## 5. Key Features

### 5.1 Hazard Reporting
- **10+ hazard types** (natural + human-made)
- **Image capture** with camera integration
- **Voice notes** with Whisper transcription
- **Auto-location** + manual selection on map
- **Weather enrichment** from WeatherAPI

### 5.2 6-Layer AI Verification Pipeline

| Layer | Weight | Technology | Description |
|-------|--------|------------|-------------|
| Geofence | 20% | Coastal boundary | Verifies report is within coastal zone |
| Weather | 25% | WeatherAPI | Cross-validates with current conditions |
| Text | 25% | FAISS + sentence-transformers | Semantic hazard classification |
| Image | 20% | TensorFlow CNN | Visual hazard identification |
| Reporter | 10% | Historical data | Credibility score from past reports |

**Decision Thresholds:**
- **≥75%**: Auto-Approve
- **40-75%**: Manual Review (ticket created)
- **<40%**: Auto-Reject

### 5.3 Real-Time Multi-Hazard Monitoring

| Hazard Type | Detection Source | Alert Levels |
|-------------|------------------|--------------|
| Tsunami | USGS Earthquake API | 1-5 |
| Cyclone | IMD/Weather API | 1-5 |
| High Waves | Open-Meteo Marine | 1-5 |
| Coastal Flood | Weather + Tide data | 1-5 |
| Rip Currents | Wave + Wind analysis | 1-5 |

- **30 monitored coastal locations** along Indian coast
- **5-minute detection cycles**
- **Automatic alert escalation**

### 5.4 Interactive Ocean Map

- **ESRI Ocean basemap** (default) - optimized for marine visualization
- **8 map styles**: Ocean, Ocean+Labels, Dark, Satellite, NatGeo, Physical, Terrain, Light
- **Real-time wave height zones** from Open-Meteo Marine API
- **Animated ocean current paths** (Bay of Bengal circulation)
- **Cyclone track visualization** with forecast cone
- **Hazard density heatmap**

### 5.5 3-Way Ticketing System

```
Reporter ←→ Analyst ←→ Authority
```

- **Auto-ticket creation** for manual review reports
- **SLA tracking** with escalation
- **Real-time messaging** within tickets
- **Status tracking**: Open → In Progress → Resolved

### 5.6 User Roles

| Role | Permissions |
|------|-------------|
| Citizen | Report hazards, view alerts, receive notifications |
| Authority | Verify reports, create alerts, manage tickets |
| Analyst | Verification queue, analytics, ticket responses |
| Admin | Full system control, user management |

---

## 6. Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- MongoDB 6.0+
- Redis 7.0+

### Backend Setup

```bash
cd /Users/patu/Desktop/coastGuardians/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your API keys

# Run backend
python main.py
# Runs on http://localhost:8000
```

### Frontend Setup

```bash
cd /Users/patu/Desktop/coastGuardians/frontend

# Install dependencies
npm install

# Set environment variables
cp .env.example .env.local
# Edit .env.local with API URL

# Run frontend
npm run dev
# Runs on http://localhost:3000
```

### Environment Variables

**Backend (.env):**
```
MONGODB_URL=mongodb://localhost:27017/coastguardians
REDIS_URL=redis://localhost:6379
JWT_SECRET=your-secret-key
WEATHER_API_KEY=your-weatherapi-key
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
GOOGLE_CLIENT_ID=your-google-client-id
```

**Frontend (.env.local):**
```
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your-google-client-id
```

---

## 7. Backend API Reference

### Authentication Routes
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/signup` | User registration |
| POST | `/auth/verify-otp` | OTP verification |
| POST | `/auth/login` | User login |
| POST | `/auth/google/callback` | Google OAuth |
| POST | `/auth/refresh` | Token refresh |
| POST | `/auth/logout` | User logout |
| GET | `/auth/me` | Current user |

### Hazard Routes
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/hazards` | Submit report |
| GET | `/hazards` | List reports |
| GET | `/hazards/my-reports` | User's reports |
| GET | `/hazards/map-data` | Map visualization |
| GET | `/hazards/ocean-data` | Wave & current data |
| GET | `/hazards/{id}` | Report details |
| DELETE | `/hazards/{id}` | Delete report |

### Multi-Hazard Routes
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/multi-hazard/health` | Service status |
| GET | `/multi-hazard/public/locations` | Monitored locations |
| GET | `/multi-hazard/public/alerts` | Real-time alerts |
| GET | `/multi-hazard/public/cyclone-data` | Cyclone tracking |

### Alert Routes
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/alerts` | List alerts |
| GET | `/alerts/{id}` | Alert details |
| POST | `/alerts` | Create alert (Authority) |

### Verification Routes
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/verification/queue` | Manual review queue |
| POST | `/verification/{id}/decide` | Analyst decision |

### Ticket Routes
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/tickets/my` | User's tickets |
| GET | `/tickets/{id}` | Ticket details |
| POST | `/tickets/{id}/messages` | Send message |

---

## 8. Mobile API Endpoints

### Base URL
- **Development:** `http://localhost:8000/api/v1`
- **Production:** `https://your-domain.com/api/v1`

### Authentication Headers
```
Authorization: Bearer <access_token>
```

### 8.1 Authentication

#### Sign Up
```http
POST /auth/signup
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "name": "John Doe",
  "phone": "+919876543210"
}

Response (201):
{
  "success": true,
  "user_id": "USR_abc123",
  "requires_verification": true
}
```

#### Login
```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123!"
}

Response (200):
{
  "success": true,
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "expires_in": 7200,
  "user": {
    "user_id": "USR_abc123",
    "name": "John Doe",
    "role": "citizen",
    "credibility_score": 75
  }
}
```

### 8.2 Hazard Reporting

#### Submit Report
```http
POST /hazards
Authorization: Bearer <access_token>
Content-Type: multipart/form-data

Form Data:
- hazard_type: "high_waves"
- category: "natural"
- latitude: 19.076
- longitude: 72.877
- address: "Juhu Beach, Mumbai"
- description: "High waves observed..."
- image: <file>
- voice_note: <file> (optional)

Response (201):
{
  "success": true,
  "report_id": "RPT_xyz789",
  "verification_status": "pending",
  "verification_score": 78.5,
  "verification_decision": "auto_approved"
}
```

**Hazard Types:**
```
Natural: high_waves, rip_current, storm_surge, coastal_flooding,
         tsunami_warning, jellyfish_bloom, algal_bloom, erosion

Human-Made: oil_spill, plastic_pollution, chemical_spill,
            ship_wreck, illegal_fishing, beached_animals
```

#### Get Map Data
```http
GET /hazards/map-data?hours=24&include_heatmap=true
Authorization: Bearer <access_token>

Response (200):
{
  "success": true,
  "data": {
    "reports": [...],
    "heatmap_points": [[lat, lon, weight], ...],
    "statistics": {
      "total_reports": 45,
      "critical_count": 5
    }
  }
}
```

#### Get Ocean Data
```http
GET /hazards/ocean-data?include_waves=true&include_currents=true

Response (200):
{
  "success": true,
  "timestamp": "2025-12-01T13:00:00Z",
  "source": "Open-Meteo Marine API",
  "waveZones": [
    {
      "name": "Central Bay",
      "center": [15.0, 88.0],
      "radius": 142400,
      "waveHeight": 1.56,
      "waveDirection": 188,
      "wavePeriod": 10.2,
      "level": "Moderate-High",
      "color": "#f97316"
    }
  ],
  "currentPaths": [...]
}
```

### 8.3 Alerts

#### Get Active Alerts
```http
GET /alerts?status=active
Authorization: Bearer <access_token>

Response (200):
{
  "total": 3,
  "alerts": [
    {
      "alert_id": "ALT_abc123",
      "title": "High Wave Warning - Mumbai Coast",
      "alert_type": "high_waves",
      "severity": "high",
      "status": "active",
      "regions": ["Mumbai", "Thane"],
      "issued_at": "2025-12-01T08:00:00Z"
    }
  ]
}
```

### 8.4 Multi-Hazard Real-Time

#### Get Monitored Locations
```http
GET /multi-hazard/public/locations

Response (200):
{
  "success": true,
  "locations": [
    {
      "location_id": "LOC_mumbai",
      "location_name": "Mumbai",
      "coordinates": {"lat": 19.076, "lon": 72.877},
      "alert_level": 2,
      "active_hazards": ["high_waves"]
    }
  ]
}
```

#### Get Cyclone Data
```http
GET /multi-hazard/public/cyclone-data?include_forecast=true

Response (200):
{
  "success": true,
  "hasActiveCyclone": true,
  "cyclone": {
    "name": "CYCLONE DANA",
    "category": 2,
    "maxWindSpeed": 120,
    "currentPosition": {"lat": 18.5, "lon": 87.2},
    "track": [...],
    "forecast": [...]
  }
}
```

### 8.5 Notifications

#### Get Notifications
```http
GET /notifications?page=1&page_size=20
Authorization: Bearer <access_token>

Response (200):
{
  "total": 25,
  "unread_count": 5,
  "notifications": [
    {
      "notification_id": "NOT_abc123",
      "type": "alert",
      "severity": "high",
      "title": "High Wave Warning",
      "is_read": false,
      "created_at": "2025-12-01T10:00:00Z"
    }
  ]
}
```

### 8.6 Error Response Format

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message"
  }
}
```

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Invalid input |
| `UNAUTHORIZED` | 401 | Invalid token |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `RATE_LIMITED` | 429 | Too many requests |

### 8.7 Rate Limiting

| Endpoint Type | Limit |
|---------------|-------|
| Auth endpoints | 5 requests/15 min |
| Report submission | 10 requests/hour |
| General API | 100 requests/min |

---

## 9. External APIs

### WeatherAPI.com
- **Purpose:** Current weather data for verification
- **Endpoint:** `https://api.weatherapi.com/v1/current.json`
- **Used in:** Weather verification layer

### Open-Meteo Marine API
- **Purpose:** Real-time wave and ocean data
- **Endpoint:** `https://marine-api.open-meteo.com/v1/marine`
- **Used in:** `/hazards/ocean-data` endpoint, wave zones visualization

### USGS Earthquake API
- **Purpose:** Seismic data for tsunami detection
- **Endpoint:** `https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/`
- **Used in:** Multi-hazard tsunami monitoring

### ESRI ArcGIS
- **Purpose:** Ocean basemap tiles
- **Endpoints:**
  - `https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}`
  - `https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Reference/MapServer/tile/{z}/{y}/{x}`

---

## 10. Database Schema

### Users Collection
```javascript
{
  _id: ObjectId,
  user_id: "USR_xxx",
  email: String,
  phone: String,
  password_hash: String,
  name: String,
  role: "citizen" | "authority" | "analyst" | "admin",
  profile_picture: String,
  credibility_score: Number (0-100),
  total_reports: Number,
  verified_reports: Number,
  email_verified: Boolean,
  phone_verified: Boolean,
  fcm_token: String,
  created_at: Date,
  updated_at: Date
}
```

### Reports Collection
```javascript
{
  _id: ObjectId,
  report_id: "RPT_xxx",
  user_id: String,
  hazard_type: String,
  category: "natural" | "humanMade",
  description: String,
  location: {
    latitude: Number,
    longitude: Number,
    address: String
  },
  image_url: String,
  voice_note_url: String,
  weather: Object,
  verification_status: "pending" | "verified" | "rejected" | "manual_review",
  verification_score: Number,
  verification_result: {
    layers: [
      { name: String, status: String, score: Number }
    ]
  },
  views: Number,
  likes: [String], // user_ids
  created_at: Date,
  verified_at: Date
}
```

### Alerts Collection
```javascript
{
  _id: ObjectId,
  alert_id: "ALT_xxx",
  title: String,
  description: String,
  alert_type: String,
  severity: "low" | "medium" | "high" | "critical",
  status: "active" | "expired" | "cancelled",
  regions: [String],
  coordinates: [{ lat: Number, lon: Number }],
  recommendations: [String],
  created_by: String,
  issued_at: Date,
  effective_from: Date,
  expires_at: Date
}
```

### Tickets Collection
```javascript
{
  _id: ObjectId,
  ticket_id: "TKT_xxx",
  report_id: String,
  reporter_id: String,
  status: "open" | "in_progress" | "resolved" | "closed",
  priority: "low" | "medium" | "high",
  messages: [
    {
      sender_id: String,
      sender_role: String,
      content: String,
      timestamp: Date
    }
  ],
  created_at: Date,
  updated_at: Date
}
```

---

## 11. Development Workflow

### Git Branching
- **main**: Production-ready code
- **VerificationLoop**: Current development branch
- Feature branches: `feature/xxx`
- Bug fixes: `fix/xxx`

### Code Style
- **Python**: Black formatter, flake8 linter
- **JavaScript**: ESLint + Prettier
- **Commits**: Conventional commits format

### Testing
```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm run test
```

### Deployment Checklist
- [ ] Environment variables configured
- [ ] MongoDB indexes created
- [ ] Redis connection verified
- [ ] TensorFlow model loaded
- [ ] FAISS index built
- [ ] SSL certificates installed
- [ ] Rate limiting configured
- [ ] CORS origins whitelisted

---

## 12. Troubleshooting

### Backend Won't Start
```bash
# Kill existing process on port 8000
lsof -ti :8000 | xargs kill -9

# Activate venv and run
cd backend
source venv/bin/activate
python main.py
```

### Ocean-data Returns 404
- **Cause:** Route ordering issue in FastAPI
- **Fix:** Ensure `/ocean-data` is defined BEFORE `/{report_id}` in `hazards.py`
- **Location:** Line ~611 in `/backend/app/api/v1/hazards.py`

### Map Not Loading
1. Check if backend is running on port 8000
2. Check browser console for CORS errors
3. Verify frontend `.env.local` has correct API URL
4. Check network tab for failed tile requests

### Verification Score Always Low
- Check if TensorFlow model is loaded (`Vision_Model/` directory)
- Verify FAISS index is built
- Check WeatherAPI key is valid
- Review geofence boundaries

### Push Notifications Not Working
- Verify FCM token is registered
- Check Firebase configuration
- Ensure notification permissions granted

---

## Mobile App Feature Checklist

### Authentication
- [ ] Email/Password signup & login
- [ ] OTP verification (email/SMS)
- [ ] Google OAuth login
- [ ] Password reset
- [ ] Token refresh mechanism
- [ ] Biometric login (local)

### Profile
- [ ] View/Edit profile
- [ ] Upload profile picture
- [ ] Update location
- [ ] Notification preferences
- [ ] FCM token registration

### Hazard Reporting
- [ ] Select hazard type
- [ ] Capture/upload image
- [ ] Record voice note
- [ ] Auto-detect location
- [ ] Manual location selection
- [ ] View my reports
- [ ] Track verification status

### Map View
- [ ] Display hazard markers
- [ ] Heatmap layer
- [ ] Wave data visualization
- [ ] Cyclone track (if active)
- [ ] Filter by hazard type
- [ ] Filter by time range

### Alerts
- [ ] View active alerts
- [ ] Alert details
- [ ] Push notification for new alerts
- [ ] Location-based alerts

### Notifications
- [ ] Notification list
- [ ] Unread badge count
- [ ] Mark as read
- [ ] Push notifications (FCM)

---

## Recommended Mobile Tech Stack

### React Native
```
- HTTP Client: Axios
- State Management: Redux Toolkit
- Maps: react-native-maps
- Push Notifications: @react-native-firebase/messaging
- Image Picker: react-native-image-picker
- Voice Recording: react-native-audio-recorder-player
- Location: react-native-geolocation
- Storage: @react-native-async-storage/async-storage
```

### Flutter
```
- HTTP Client: Dio
- State Management: Provider / Riverpod
- Maps: google_maps_flutter
- Push Notifications: firebase_messaging
- Image Picker: image_picker
- Voice Recording: audio_recorder
- Location: geolocator
- Storage: shared_preferences
```

---

## Contact & Resources

- **Project:** Smart India Hackathon 2025
- **Organization:** INCOIS (Indian National Centre for Ocean Information Services)
- **Problem Statement:** Ocean Hazards Crowdsourcing

### Quick Links
- API Docs: `http://localhost:8000/docs`
- Frontend: `http://localhost:3000`
- MongoDB: `mongodb://localhost:27017/coastguardians`

---

**Document Version:** 1.0
**Last Updated:** December 1, 2025
**Maintained By:** CoastGuardians Team
