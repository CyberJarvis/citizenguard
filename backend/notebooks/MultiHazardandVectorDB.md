# Building Your Live Hazard Map System - Product Blueprint

---

## **🎯 What You're Building**

A **real-time hazard monitoring map** that shows live coastal hazards (tsunamis, cyclones, floods, high waves) across 12+ locations worldwide, updating every 5 minutes automatically.

---

## **📊 System Architecture - 3 Parts**

```
[ML Model (Python)]  →  [API Server (FastAPI)]  →  [React Map (Your Frontend)]
    We built this         You need to build         You have this base
```

---

## **🔧 Part 1: API Server (What You Need to Build)**

### **Purpose**
Act as a bridge between your ML model and React frontend.

### **Key Components**

**1. Endpoints Your Map Needs:**
- `GET /api/locations` → List all 12 locations (name, coordinates, risk level)
- `GET /api/monitoring/current` → **MAIN ENDPOINT** - Returns all current hazard data
- `GET /api/earthquakes/recent` → Recent earthquakes to show on map
- `WebSocket /ws/live` → Real-time updates (optional but recommended)

**2. Background Worker:**
- Runs ML model every 5 minutes
- Fetches earthquake + weather data
- Stores results in memory/database
- Pushes updates to connected clients

**3. Data Structure You'll Serve:**
```
{
  "locations": {
    "mumbai": {
      "coordinates": {lat: 19.07, lon: 72.87},
      "current_hazards": {
        "tsunami": {alert_level: 5, probability: 0.85},
        "cyclone": {alert_level: 3, category: "STORM"},
        "waves": {alert_level: 2, beach_flag: "YELLOW"},
        "flood": {alert_level: 1, flood_score: 25}
      },
      "max_alert": 5,
      "status": "CRITICAL"
    }
  },
  "summary": {
    "critical_alerts": 2,
    "high_alerts": 3
  }
}
```

---

## **🗺️ Part 2: Map Frontend (What You Need to Enhance)**

### **Current State vs. Target State**

**You Have:**
- ✅ Map view with OpenStreetMap
- ✅ Location detection (blue dot)
- ✅ "All Clear!" message
- ✅ Basic UI structure

**You Need to Add:**

### **A. Location Markers (Color-Coded)**
- **Purpose:** Show each monitored location as a pin
- **Visual Logic:**
  - 🟢 Green marker → Alert Level 1-2 (Normal/Low)
  - 🟡 Yellow marker → Alert Level 3 (Warning)
  - 🟠 Orange marker → Alert Level 4 (High Risk)
  - 🔴 Red marker → Alert Level 5 (Critical - flashing/pulsing)
- **Data Source:** Loop through `locations` from API response
- **Position:** Use `coordinates.lat` and `coordinates.lon`

### **B. Marker Popups (On Click)**
When user clicks a marker, show popup with:
```
📍 Mumbai, India
Population: 12.4M
Status: 🔴 CRITICAL

Hazards Detected:
🌊 Tsunami: 85% probability
   → Alert Level 5
🌀 Cyclone: STORM conditions
   → Alert Level 3
   
Recommendations:
• EVACUATE coastal areas immediately
• Move to higher ground (>30m)

Last updated: 2 minutes ago
```

### **C. Earthquake Markers (Different Style)**
- **Visual:** Small circle with magnitude label
- **Color:** Based on magnitude (5-6=yellow, 6-7=orange, 7+=red)
- **Purpose:** Show recent seismic activity
- **Interaction:** Click shows earthquake details

### **D. Real-Time Updates**
- **Auto-refresh every 5 minutes**
- **Visual indicator:** Show "Updating..." when fetching
- **Smooth transitions:** Markers change color smoothly, not abruptly
- **Notification:** Toast message when new critical alert appears

### **E. Side Panel Enhancements**
Replace "All Clear!" section with:
```
ALERT STATUS
━━━━━━━━━━━━━━
🔴 Critical: 2
🟠 High: 3
🟡 Medium: 2
🟢 Normal: 5

ACTIVE HAZARDS
━━━━━━━━━━━━━━
🌊 Tsunami (2 locations)
🌀 Cyclone (1 location)
🌊 High Waves (3 locations)

AFFECTED REGIONS
━━━━━━━━━━━━━━
• Port Blair (CRITICAL)
• Mumbai (HIGH)
• Chennai (MEDIUM)
```

### **F. Filters (Toggle On/Off)**
Add buttons to filter what's shown:
- ☑️ Tsunamis
- ☑️ Cyclones
- ☑️ High Waves
- ☑️ Floods
- ☑️ Earthquakes

### **G. Legend Enhancement**
Update your legend to show:
- 🔴 Critical Alert (Level 5)
- 🟠 High Alert (Level 4)
- 🟡 Warning (Level 3)
- 🟢 Normal (Level 1-2)
- 📍 Your Location
- ⚫ Earthquake Epicenter

---

## **🔄 Data Flow - Step by Step**

### **How Data Moves From ML Model to Your Map**

**Step 1: Background Process (Every 5 minutes)**
```
ML System runs → Analyzes all locations → Stores results
```

**Step 2: Your Frontend Requests Data**
```
React app → HTTP GET /api/monitoring/current → Receives JSON
```

**Step 3: Process and Display**
```
Parse JSON → Update marker colors → Update popup content → Update side panel stats
```

**Step 4: User Interaction**
```
User clicks marker → Show popup with that location's hazard details
```

---

## **🎨 Visual Design Guidelines**

### **Alert Level Colors**
| Level | Color | Meaning | Visual Effect |
|-------|-------|---------|---------------|
| 5 | `#DC2626` (Red) | Critical | Pulsing animation |
| 4 | `#F97316` (Orange) | High | Solid, larger size |
| 3 | `#FCD34D` (Yellow) | Warning | Solid, medium size |
| 2 | `#60A5FA` (Blue) | Low | Solid, small size |
| 1 | `#10B981` (Green) | Normal | Solid, small size |

### **Marker Sizes**
- Level 5: 40px (with pulse animation)
- Level 4: 35px
- Level 3: 30px
- Level 1-2: 25px

### **Animation for Critical Alerts**
```
Red marker pulses every 2 seconds
Opacity: 1 → 0.6 → 1 (repeating)
Scale: 1 → 1.2 → 1 (repeating)
```

---

## **📱 Responsive Behavior**

### **Desktop (>1024px)**
- Map: 70% width
- Side panel: 30% width (fixed right)
- Popups: Full detail

### **Tablet (768-1024px)**
- Map: Full width
- Side panel: Overlay (slide from right)
- Popups: Condensed detail

### **Mobile (<768px)**
- Map: Full screen
- Side panel: Bottom sheet (slide up)
- Popups: Minimal detail (tap for full screen)

---

## **⚡ Performance Optimization**

### **Data Fetching Strategy**
1. **Initial Load:** Fetch all locations + current data
2. **Updates:** Poll `/api/monitoring/current` every 5 minutes
3. **On-Demand:** Fetch specific location details only when marker clicked
4. **WebSocket (Optional):** For instant updates without polling

### **Map Performance**
- **Cluster markers** when zoomed out (>5 markers in view)
- **Lazy load popups** (don't pre-render, create on click)
- **Debounce filters** (wait 300ms after toggle before re-rendering)
- **Cache API responses** (don't refetch if < 1 minute old)

---

## **🔔 Alert Notification System**

### **When to Notify User**
- New critical alert (Level 5) appears
- Alert level increases (e.g., 3 → 4)
- User's location has active hazard

### **Notification Types**
1. **Browser Notification** (if permission granted)
   - Title: "🚨 CRITICAL ALERT - Mumbai"
   - Body: "Tsunami detected - 85% probability"

2. **In-App Toast** (always shown)
   - Top-right corner
   - Auto-dismiss after 8 seconds
   - Click to focus on location

3. **Sound Alert** (optional, toggleable)
   - Play alert sound for Level 4-5
   - User can mute in settings

---

## **🎯 User Interactions - Complete Flow**

### **Scenario 1: User Opens App**
```
1. Load map centered on user's location
2. Show "Loading..." indicator
3. Fetch all locations from API
4. Place markers on map (color-coded)
5. Fetch current monitoring data
6. Update marker colors based on alert levels
7. Update side panel with summary stats
8. Hide loading indicator
9. Show "Last updated: Just now"
```

### **Scenario 2: User Clicks Mumbai Marker**
```
1. Map zooms to Mumbai (smooth animation)
2. Popup appears above marker
3. Show loading spinner in popup
4. Fetch detailed data for Mumbai
5. Populate popup with:
   - Location name, country, population
   - All 4 hazard statuses
   - Weather conditions
   - Nearby earthquakes (if any)
   - Recommendations
6. User can click "View Full Details" → Opens modal
```

### **Scenario 3: Critical Alert Appears**
```
1. Background: API detects new Level 5 alert
2. WebSocket pushes update to frontend (or next poll catches it)
3. Frontend receives new data
4. Marker color changes: 🟢 → 🔴 (animated transition)
5. Marker starts pulsing
6. Browser notification appears
7. Toast notification slides in
8. Side panel updates: Critical Alerts: 1 → 2
9. If marker is visible, show brief info banner
```

### **Scenario 4: User Filters Hazards**
```
1. User clicks "Cyclones" toggle (turns off)
2. All markers with only cyclone hazards fade out
3. Markers with multiple hazards remain (but popup hides cyclone section)
4. Side panel updates to show filtered stats
5. Legend updates to show only active filters
```

---

## **🗃️ Data Caching Strategy**

### **What to Cache**
- **Locations list:** Cache forever (rarely changes)
- **Monitoring data:** Cache for 4 minutes (updates every 5)
- **Earthquake data:** Cache for 2 minutes (fast-moving)
- **Marker states:** Keep in React state (don't refetch)

### **When to Invalidate Cache**
- User clicks "Refresh" button
- 5 minutes elapsed since last update
- WebSocket receives update notification
- User navigates back to app after being away

---

## **🚀 Implementation Priority**

### **Phase 1: MVP (Week 1-2)**
1. ✅ Create FastAPI endpoints
2. ✅ Add location markers to map
3. ✅ Color-code by alert level
4. ✅ Basic popup on click
5. ✅ Auto-refresh every 5 minutes

### **Phase 2: Enhanced UX (Week 3)**
1. ✅ Earthquake markers
2. ✅ Side panel with live stats
3. ✅ Filters for hazard types
4. ✅ Smooth animations
5. ✅ Better mobile layout

### **Phase 3: Real-Time (Week 4)**
1. ✅ WebSocket for instant updates
2. ✅ Browser notifications
3. ✅ Toast alerts
4. ✅ Sound alerts (optional)
5. ✅ Performance optimizations

---

## **🛠️ Technical Stack Summary**

```
Backend:
├── FastAPI (Python web framework)
├── Your ML model (already built)
├── Uvicorn (ASGI server)
├── WebSockets (for real-time)
└── CORS middleware (for React connection)

Frontend:
├── React.js (already using)
├── Leaflet.js (already using)
├── Axios (HTTP requests)
├── React Query (caching, optional)
├── Socket.io-client (WebSocket)
└── React Toastify (notifications)

Data Flow:
Python ML → FastAPI → JSON → React → Leaflet → User
```

---

## **📊 Key Metrics to Track**

### **System Health**
- API response time (target: <500ms)
- Update frequency (every 5 min)
- WebSocket connection uptime
- Error rate (<1%)

### **User Engagement**
- Active users per hour
- Marker clicks per session
- Filter usage statistics
- Notification open rate

### **Alert Metrics**
- Critical alerts per day
- False positive rate
- Average time to first alert view
- User location vs. alert location distance

---

## **🎓 What You Tell Claude Code**

### **Prompt Template**

```
I need to build a FastAPI backend that:
1. Loads my ML hazard detection model (I'll provide the Python code)
2. Runs monitoring every 5 minutes in background
3. Exposes these REST endpoints:
   - GET /api/locations (list all locations)
   - GET /api/monitoring/current (all current hazard data)
   - GET /api/earthquakes/recent (recent seismic events)
4. Returns JSON in this format: [show example]
5. Has CORS enabled for React frontend
6. Includes WebSocket endpoint for real-time updates

Then help me integrate it with my React map:
1. Fetch data from API every 5 minutes
2. Display markers color-coded by alert level
3. Show popups with hazard details on click
4. Add side panel showing alert summary
5. Make markers pulse/animate for critical alerts
```

---

This blueprint gives you everything needed to build the system without overwhelming you with code. Use this as your reference when working with Claude Code - just point to specific sections you're implementing! 🚀