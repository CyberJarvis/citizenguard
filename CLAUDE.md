# CoastGuardian - Project Context

## Overview
CoastGuardian is an ocean hazard reporting platform for coastal communities in India. It allows citizens to report hazards, authorities to verify them, and analysts to monitor social media intelligence.

## Tech Stack
- **Frontend**: Next.js 15, React, Tailwind CSS, Zustand (state management)
- **Backend**: Python FastAPI, MongoDB, Redis
- **APIs**: WeatherAPI, Google Translate, USGS Earthquake data

## Project Structure
```
coastGuardians/
├── frontend/           # Next.js frontend application
│   ├── app/           # Next.js App Router pages
│   ├── components/    # React components
│   ├── context/       # Zustand auth store (AuthContext.js)
│   ├── lib/           # API utilities (api.js, smiApi.js)
│   └── public/        # Static assets
├── backend/           # FastAPI backend
│   └── app/
│       ├── api/v1/    # API routes
│       ├── services/  # Business logic
│       └── models/    # MongoDB models
└── blueradar_intelligence/  # Social Media Intelligence module
```

## User Roles
- **citizen**: Report hazards, view alerts, track tickets
- **authority**: Verify reports, create alerts, manage tickets
- **analyst**: Monitor social media, analyze data, real-time monitoring
- **authority_admin**: Full system administration

## Key Components
- `ProtectedRoute.js` - Auth guard for protected pages
- `DashboardLayout.js` - Main layout with sidebar navigation
- `AuthContext.js` - Zustand store for authentication state
- `GoogleTranslate.js` - Multi-language support (Indian languages)

## Running the Project

### Backend
```bash
cd backend
source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend
```bash
cd frontend
npm run dev
```

## Recent Changes (Dec 2025)
1. Fixed infinite loading issue in page navigation
2. Added Google Translate widget for Indian regional languages
3. SMI 2.0 - Social Media Intelligence with MEDIUM alert levels
4. BlueRadar NLP for hazard classification

## Environment Variables
Frontend (.env.local):
- `NEXT_PUBLIC_API_URL` - Backend API URL
- `NEXT_PUBLIC_WEATHER_API_KEY` - WeatherAPI key
- `NEXT_PUBLIC_WEATHER_API_BASE_URL` - WeatherAPI base URL

## Git Branches
- `main` - Production branch
- `VerificationLoop` - Current development branch
- `SMI_2.0` - Social Media Intelligence features
