# CoastGuardians - Claude Context File
## Smart India Hackathon 2025 | Ocean Hazards Crowdsourcing for INCOIS

**Last Updated:** December 1, 2025

---

## Quick Recall Prompt
Copy and paste this to Claude when starting a new session:

```
I'm working on CoastGuardians - an Ocean Hazards Crowdsourcing platform for Smart India Hackathon (SIH 2025) for INCOIS. Please read the CLAUDE_CONTEXT.md file in my project root to understand the full context.

Tech Stack:
- Backend: FastAPI + MongoDB + Redis + TensorFlow/FAISS
- Frontend: Next.js 16 + React 19 + Leaflet + TailwindCSS

Key Features:
- Citizen hazard reporting with image/voice
- 6-layer AI verification pipeline (Geofence, Weather, Text/FAISS, Image/TensorFlow, Reporter Score)
- Real-time MultiHazard monitoring (Tsunami, Cyclone, Waves, Floods, Rip Currents)
- 3-way ticketing (Reporter-Analyst-Authority)
- ESRI Ocean basemap with real-time wave data

Working Directory: /Users/patu/Desktop/coastGuardians
```

---

## Project Structure

```
coastGuardians/
├── backend/                    # FastAPI Backend
│   ├── app/
│   │   ├── api/v1/            # API Routes (17 routers, 80+ endpoints)
│   │   │   ├── auth.py        # Authentication
│   │   │   ├── hazards.py     # Hazard reporting + ocean-data endpoint
│   │   │   ├── verification.py # 6-layer verification
│   │   │   ├── tickets.py     # 3-way ticketing
│   │   │   ├── alerts.py      # Authority alerts
│   │   │   ├── multi_hazard.py # Real-time monitoring
│   │   │   └── ...
│   │   ├── models/            # Pydantic/MongoDB models
│   │   ├── services/          # Business logic (23 services)
│   │   │   ├── verification_service.py  # 6-layer pipeline
│   │   │   ├── multi_hazard_service.py  # Real-time detection
│   │   │   ├── vision_service.py        # TensorFlow image classification
│   │   │   ├── vectordb_service.py      # FAISS text classification
│   │   │   └── ...
│   │   └── middleware/        # CORS, RBAC, security
│   ├── main.py                # FastAPI entry point
│   └── Vision_Model/          # TensorFlow trained model
│
├── frontend/                   # Next.js Frontend
│   ├── app/                   # Pages (48 routes)
│   │   ├── map/page.js        # Interactive ocean map
│   │   ├── report-hazard/     # Hazard reporting
│   │   ├── authority/         # Authority dashboard
│   │   ├── analyst/           # Analyst panel
│   │   └── admin/             # Admin dashboard
│   ├── components/
│   │   └── map/               # Map components
│   │       ├── OceanMap.js    # Main map (Leaflet + ESRI)
│   │       ├── WaveTrackLayer.js # Ocean waves/currents
│   │       ├── CycloneLayer.js   # Cyclone visualization
│   │       ├── HeatmapLayer.js   # Hazard density
│   │       └── MapControls.js    # Layer controls
│   └── lib/api.js             # Axios API client
│
└── CLAUDE_CONTEXT.md          # This file
```

---

## Technology Stack

### Backend
| Technology | Purpose |
|------------|---------|
| FastAPI | REST API framework |
| MongoDB | Primary database |
| Redis | Caching, OTP, sessions |
| TensorFlow/Keras | Image classification (4 hazards) |
| FAISS | Text classification (semantic search) |
| Whisper | Voice transcription |
| JWT + bcrypt | Authentication |
| Twilio | SMS notifications |

### Frontend
| Technology | Purpose |
|------------|---------|
| Next.js 16 | React framework |
| React 19 | UI library |
| TailwindCSS 4 | Styling |
| Leaflet | Maps |
| ESRI Basemaps | Ocean visualization |
| Zustand | State management |
| ApexCharts | Analytics charts |

---

## Key Features Implemented

### 1. Hazard Reporting
- 10+ hazard types (natural + human-made)
- Image capture + voice notes
- Auto-location + manual selection
- Weather data enrichment

### 2. 6-Layer AI Verification
| Layer | Weight | Technology |
|-------|--------|------------|
| Geofence | 20% | Coastal boundary check |
| Weather | 25% | WeatherAPI validation |
| Text | 25% | FAISS + sentence-transformers |
| Image | 20% | TensorFlow CNN |
| Reporter | 10% | Historical credibility |

Decision: ≥75% Auto-Approve | 40-75% Manual Review | <40% Reject

### 3. Real-Time MultiHazard Monitoring
- 5 hazard types: Tsunami, Cyclone, High Waves, Coastal Flood, Rip Currents
- 30 monitored coastal locations
- 5-minute detection cycles
- USGS earthquake + Weather API integration

### 4. Interactive Ocean Map
- ESRI Ocean basemap (default)
- 8 map styles available
- Real-time wave height zones (Open-Meteo Marine API)
- Animated ocean current paths
- Cyclone track visualization
- Hazard density heatmap

### 5. 3-Way Ticketing System
- Reporter ↔ Analyst ↔ Authority
- SLA tracking & escalation
- Auto-ticket for manual review reports

### 6. User Roles
- **Citizen**: Report hazards, view alerts
- **Authority**: Verify reports, create alerts
- **Analyst**: Verification queue, analytics
- **Admin**: Full system control

---

## External APIs

| API | Purpose | Endpoint |
|-----|---------|----------|
| WeatherAPI.com | Weather data | Primary |
| Open-Meteo Marine | Wave/ocean data | `/hazards/ocean-data` |
| USGS Earthquake | Seismic data | Tsunami detection |
| ESRI ArcGIS | Ocean basemaps | Map tiles |
| Google OAuth | Social login | `/auth/google/*` |
| Twilio | SMS | Notifications |

---

## Important API Endpoints

```
# Authentication
POST /api/v1/auth/signup
POST /api/v1/auth/login
POST /api/v1/auth/verify-otp
GET  /api/v1/auth/me

# Hazard Reports
POST /api/v1/hazards              # Submit report
GET  /api/v1/hazards/map-data     # Map visualization data
GET  /api/v1/hazards/ocean-data   # Wave & current data (NEW)

# Verification
GET  /api/v1/verification/queue   # Manual review queue
POST /api/v1/verification/{id}/decide  # Analyst decision

# Multi-Hazard
GET  /api/v1/multi-hazard/health
GET  /api/v1/multi-hazard/public/locations
GET  /api/v1/multi-hazard/public/alerts

# Cyclone
GET  /api/v1/multi-hazard/public/cyclone-data
```

---

## Running the Project

### Backend
```bash
cd /Users/patu/Desktop/coastGuardians/backend
source venv/bin/activate
python main.py
# Runs on http://localhost:8000
```

### Frontend
```bash
cd /Users/patu/Desktop/coastGuardians/frontend
npm run dev
# Runs on http://localhost:3000
```

---

## Recent Changes (December 2025)

1. ✅ Fixed `/hazards/ocean-data` endpoint (route ordering issue)
2. ✅ Added ESRI Ocean basemap as default
3. ✅ Added 8 map style options
4. ✅ Real-time wave data from Open-Meteo Marine API
5. ✅ Animated ocean current visualization

---

## Common Issues & Fixes

### Backend won't start
```bash
lsof -ti :8000 | xargs kill -9  # Kill existing process
source venv/bin/activate
python main.py
```

### Ocean-data returns 404
- Route ordering: `/ocean-data` must be BEFORE `/{report_id}` in hazards.py
- Check line ~611 in `/backend/app/api/v1/hazards.py`

### Map not loading
- Check if backend is running on port 8000
- Check browser console for CORS errors
- Ensure frontend .env has correct API URL

---

## Git Status
- **Branch:** VerificationLoop
- **Main Branch:** main

---

## Contact / Notes
- Project for: Smart India Hackathon 2025
- Organization: INCOIS (Indian National Centre for Ocean Information Services)
- Problem: Ocean Hazards Crowdsourcing
