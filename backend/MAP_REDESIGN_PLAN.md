# CoastGuardians Map Page Redesign - Implementation Plan

## Design Reference: INCOIS & Windy.com Style

Based on the reference images provided (INCOIS ocean monitoring interface), the redesign will create a **professional, production-grade ocean monitoring dashboard** with:

- Full-screen immersive map experience
- Glassmorphism UI panels with subtle transparency
- Real-time data overlays with smooth animations
- Layer-based visualization system (like Windy)
- Responsive design optimized for all devices

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         MAP PAGE ARCHITECTURE                             │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                    FULL-SCREEN MAP CONTAINER                        │ │
│  │  ┌───────────────┐                           ┌───────────────────┐  │ │
│  │  │ Control Panel │                           │  Info Panel       │  │ │
│  │  │ (Top-Left)    │                           │  (Collapsible)    │  │ │
│  │  │ - Layers      │                           │  - Location List  │  │ │
│  │  │ - Filters     │                           │  - Active Alerts  │  │ │
│  │  │ - Search      │                           │  - Statistics     │  │ │
│  │  └───────────────┘                           └───────────────────┘  │ │
│  │                                                                      │ │
│  │  ┌──────────────────────────────────────────────────────────────┐   │ │
│  │  │                     MAP LAYERS                                │   │ │
│  │  │  • Base Tiles (Dark Ocean, Satellite, Terrain)               │   │ │
│  │  │  • Heatmap Layer (Report density / Alert intensity)          │   │ │
│  │  │  • Clustered Markers (User Reports)                          │   │ │
│  │  │  • Alert Markers (ML-detected hazards)                       │   │ │
│  │  │  • Animated Pulse Circles (Active alerts)                    │   │ │
│  │  │  • Weather Overlay (Optional - wind/waves)                   │   │ │
│  │  └──────────────────────────────────────────────────────────────┘   │ │
│  │                                                                      │ │
│  │  ┌───────────────────────────────────────────────────────────────┐  │ │
│  │  │                   BOTTOM CONTROLS                              │  │ │
│  │  │  [Legend] [Layer Toggle] [Time Slider] [Map Style] [Fullscreen]│  │ │
│  │  └───────────────────────────────────────────────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                    MODAL COMPONENTS                                  │ │
│  │  • Location Detail Modal (Weather, Marine, Alerts)                  │ │
│  │  • Report Detail Modal (User report with verification status)       │ │
│  │  • Alert Detail Modal (ML-detected hazard details)                  │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Steps

### Phase 1: Core Map Infrastructure

#### 1.1 Create New Map Page Structure
**File:** `frontend/app/map/page.js` (complete rewrite)

- Remove DashboardLayout wrapper for true full-screen experience
- Implement SSR-safe dynamic imports for all Leaflet components
- Create modular component architecture

#### 1.2 Create Map Components
**Directory:** `frontend/components/map/`

| Component | Purpose |
|-----------|---------|
| `OceanMap.js` | Main map container with all layers |
| `MapControls.js` | Top-left control panel (layers, search) |
| `MapInfoPanel.js` | Right sidebar with locations/alerts |
| `MapLegend.js` | Bottom legend with alert levels |
| `HeatmapLayer.js` | Restructured heatmap implementation |
| `ClusterLayer.js` | Report clustering with auto-cleanup |
| `AlertMarkers.js` | ML-detected hazard markers |
| `LocationMarkers.js` | Monitoring station markers |
| `MapStyleSwitcher.js` | Base map style toggle |

---

### Phase 2: Heatmap Redesign

#### 2.1 Heatmap Architecture
The new heatmap will visualize:
1. **Report Density** - Clusters of user-reported hazards
2. **Alert Intensity** - Heat based on alert level severity
3. **Real-time Updates** - Auto-refresh every 60 seconds

**Data Source:** Combine:
- `getHazardReports()` - User reports with coordinates
- `getMultiHazardPublicAlerts()` - ML-detected alerts
- `getMultiHazardPublicLocations()` - Monitoring stations

#### 2.2 Heatmap Configuration
```javascript
const HEATMAP_CONFIG = {
  radius: 25,
  blur: 30,
  maxZoom: 12,
  gradient: {
    0.0: '#1a365d',   // Deep blue (low)
    0.2: '#2b6cb0',   // Blue
    0.4: '#38a169',   // Green
    0.6: '#ecc94b',   // Yellow
    0.8: '#ed8936',   // Orange
    1.0: '#e53e3e'    // Red (critical)
  },
  maxIntensity: 1.0
};
```

---

### Phase 3: Clustering Implementation

#### 3.1 Cluster Architecture
- Use `react-leaflet-cluster` for marker grouping
- Custom cluster icons with count badges
- Smooth expand/collapse animations
- Click cluster to zoom and reveal markers

#### 3.2 Cluster Styling
```javascript
const createClusterIcon = (cluster) => {
  const count = cluster.getChildCount();
  let size = 'small';
  let color = '#22c55e';

  if (count >= 50) { size = 'large'; color = '#ef4444'; }
  else if (count >= 20) { size = 'medium'; color = '#f97316'; }
  else if (count >= 10) { size = 'small'; color = '#eab308'; }

  return L.divIcon({
    html: `<div class="cluster-${size}" style="background:${color}">${count}</div>`,
    className: 'marker-cluster',
    iconSize: [size === 'large' ? 50 : size === 'medium' ? 40 : 30]
  });
};
```

---

### Phase 4: 24-Hour Auto-Cleanup System

#### 4.1 Backend Endpoint (New)
**File:** `backend/app/api/v1/hazards.py`

Add endpoint to filter reports by time:
```python
@router.get("/map-data")
async def get_map_data(
    hours: int = Query(default=24, ge=1, le=168),  # 1-7 days
    include_heatmap: bool = True,
    include_clusters: bool = True
):
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    reports = await db.hazard_reports.find({
        "created_at": {"$gte": cutoff},
        "verification_status": {"$ne": "rejected"}
    }).to_list(1000)

    return {
        "reports": reports,
        "heatmap_data": generate_heatmap_data(reports) if include_heatmap else None,
        "cluster_data": generate_cluster_data(reports) if include_clusters else None,
        "cutoff_time": cutoff.isoformat(),
        "total_count": len(reports)
    }
```

#### 4.2 Frontend Implementation
- Store `cutoff_time` in component state
- Display "Last 24 hours" indicator on map
- Auto-refresh data every 2 minutes
- Animate out-of-date markers before removal

---

### Phase 5: UI/UX Design

#### 5.1 Color Palette (Ocean-Themed)
```css
:root {
  --ocean-deep: #0f172a;
  --ocean-dark: #1e293b;
  --ocean-medium: #334155;
  --ocean-light: #64748b;
  --cyan-primary: #06b6d4;
  --cyan-light: #22d3ee;
  --emerald-safe: #10b981;
  --amber-watch: #f59e0b;
  --orange-warning: #f97316;
  --red-critical: #ef4444;
  --glass-bg: rgba(15, 23, 42, 0.85);
  --glass-border: rgba(255, 255, 255, 0.1);
}
```

#### 5.2 Glassmorphism Components
```css
.glass-panel {
  background: var(--glass-bg);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--glass-border);
  border-radius: 16px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
}
```

#### 5.3 Animation System
```css
/* Pulse animation for critical alerts */
@keyframes alert-pulse {
  0%, 100% {
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7);
  }
  50% {
    transform: scale(1.05);
    box-shadow: 0 0 0 20px rgba(239, 68, 68, 0);
  }
}

/* Fade in for new markers */
@keyframes marker-enter {
  from { opacity: 0; transform: scale(0.5); }
  to { opacity: 1; transform: scale(1); }
}

/* Smooth heatmap transition */
.leaflet-heatmap-layer {
  transition: opacity 0.5s ease-in-out;
}
```

---

### Phase 6: Mobile Responsiveness

#### 6.1 Breakpoint Strategy
| Breakpoint | Layout Changes |
|------------|----------------|
| `< 640px` (mobile) | Bottom sheet for panels, simplified controls |
| `640-1024px` (tablet) | Collapsible sidebar, compact legend |
| `> 1024px` (desktop) | Full sidebar, expanded controls |

#### 6.2 Touch Optimizations
- Larger touch targets (min 44px)
- Swipe gestures for panel navigation
- Pinch-to-zoom for heatmap detail
- Bottom sheet modal for location details

---

### Phase 7: Real-Time Data Integration

#### 7.1 Data Fetching Strategy
```javascript
const useMapData = () => {
  const [data, setData] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      const [locations, alerts, reports] = await Promise.all([
        getMultiHazardPublicLocations(),
        getMultiHazardPublicAlerts({ limit: 50 }),
        getHazardReports({ hours: 24, status: 'verified,pending' })
      ]);

      setData({
        locations: locations.locations || [],
        alerts: alerts.alerts || [],
        reports: reports.reports || [],
        timestamp: Date.now()
      });
    };

    fetchData();
    const interval = setInterval(fetchData, 60000); // 1 min refresh
    return () => clearInterval(interval);
  }, []);

  return data;
};
```

#### 7.2 WebSocket Support (Optional Enhancement)
For true real-time updates, consider WebSocket connection:
- New alert notifications
- Report status changes
- Marker position updates

---

### Phase 8: Performance Optimizations

#### 8.1 Map Performance
- Use `useMemo` for marker icon creation
- Implement viewport-based rendering (only show visible markers)
- Lazy load heatmap data on zoom level change
- Use `requestAnimationFrame` for smooth animations

#### 8.2 Data Caching
```javascript
const MAP_CACHE = {
  locations: { data: null, expiry: 0 },
  alerts: { data: null, expiry: 0 },
  reports: { data: null, expiry: 0 }
};

const getCachedData = async (key, fetcher, ttl = 60000) => {
  const now = Date.now();
  if (MAP_CACHE[key].data && MAP_CACHE[key].expiry > now) {
    return MAP_CACHE[key].data;
  }
  const data = await fetcher();
  MAP_CACHE[key] = { data, expiry: now + ttl };
  return data;
};
```

---

## File Structure (New/Modified)

```
frontend/
├── app/
│   └── map/
│       └── page.js                    # Complete rewrite
│
├── components/
│   └── map/
│       ├── OceanMap.js               # NEW - Main map component
│       ├── MapControls.js            # NEW - Control panel
│       ├── MapInfoPanel.js           # NEW - Info sidebar
│       ├── MapLegend.js              # MODIFY - Enhanced legend
│       ├── HeatmapLayer.js           # NEW - Restructured heatmap
│       ├── ClusterLayer.js           # NEW - Clustering component
│       ├── AlertMarkers.js           # NEW - Alert visualization
│       ├── LocationMarkers.js        # NEW - Station markers
│       ├── MapStyleSwitcher.js       # NEW - Style toggle
│       ├── LocationDetailModal.js    # NEW - Detail modal
│       └── ReportDetailModal.js      # NEW - Report modal
│
├── hooks/
│   └── useMapData.js                 # NEW - Data fetching hook
│
└── styles/
    └── map.css                       # NEW - Map-specific styles

backend/
└── app/
    └── api/
        └── v1/
            └── hazards.py            # MODIFY - Add map-data endpoint
```

---

## API Changes Required

### New Backend Endpoint
**`GET /api/v1/hazards/map-data`**

Query Parameters:
- `hours` (int, default=24): Time window for reports
- `include_heatmap` (bool, default=true): Include heatmap data
- `include_clusters` (bool, default=true): Include cluster data
- `min_severity` (str, optional): Filter by severity
- `hazard_types` (list, optional): Filter by hazard type

Response:
```json
{
  "success": true,
  "data": {
    "reports": [...],
    "heatmap_points": [[lat, lng, intensity], ...],
    "monitoring_stations": [...],
    "alerts": [...],
    "statistics": {
      "total_reports": 150,
      "critical_alerts": 3,
      "warning_alerts": 12,
      "last_update": "2024-01-15T10:30:00Z"
    }
  },
  "meta": {
    "cutoff_time": "2024-01-14T10:30:00Z",
    "refresh_interval": 60
  }
}
```

---

## Estimated Implementation Order

1. **Phase 1** - Core map infrastructure (~2-3 hours)
2. **Phase 5** - UI/UX design & styles (~1-2 hours)
3. **Phase 7** - Real-time data integration (~1 hour)
4. **Phase 2** - Heatmap redesign (~1-2 hours)
5. **Phase 3** - Clustering implementation (~1 hour)
6. **Phase 4** - 24-hour cleanup system (~1 hour)
7. **Phase 6** - Mobile responsiveness (~1-2 hours)
8. **Phase 8** - Performance optimizations (~1 hour)

**Total Estimated Time: 9-14 hours**

---

## Success Criteria

1. **Visual Quality**: Map looks professional, similar to INCOIS/Windy
2. **Performance**: <100ms interaction latency, smooth 60fps animations
3. **Real-time**: Data refreshes automatically, no manual intervention needed
4. **Clustering**: Reports grouped intelligently, expand on zoom
5. **Heatmap**: Shows density/intensity accurately, smooth transitions
6. **24h Cleanup**: Old data automatically filtered, map stays clean
7. **Mobile**: Full functionality on mobile devices
8. **Production Data**: No dummy data, 100% real API integration
