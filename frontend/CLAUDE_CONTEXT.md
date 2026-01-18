# Claude Context - CoastGuardians Frontend Development

> **Last Updated:** December 4, 2025
> **Branch:** UI_beta

This file provides context for Claude AI assistants working on this codebase. It documents recent changes, architectural decisions, and ongoing work.

---

## Recent Changes (December 4, 2025)

### 1. DashboardLayout - Collapsible Sidebar

**File:** `components/DashboardLayout.js`

Added a toggle button to collapse/expand the main sidebar on desktop:

- **New State:** `sidebarCollapsed` - controls whether sidebar is collapsed
- **Toggle Button:** Circular button with chevron icon, positioned at the right edge of the sidebar
- **Collapsed State:** Sidebar shrinks to 80px width, showing only icons with tooltips
- **Expanded State:** Full 288px (w-72) sidebar with icons and text

**Key Changes:**
```jsx
// New state
const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

// Toggle button (placed outside aside, as fixed element)
<button
  onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
  className={`hidden lg:flex fixed top-6 z-[60] w-8 h-8 bg-white border border-gray-200 rounded-full items-center justify-center shadow-md hover:bg-gray-50 hover:shadow-lg transition-all duration-300 ${
    sidebarCollapsed ? 'left-[88px]' : 'left-[280px]'
  }`}
>
  {sidebarCollapsed ? <ChevronRight /> : <ChevronLeft />}
</button>

// Sidebar width changes based on state
<aside className={`... ${sidebarCollapsed ? 'lg:w-20' : 'lg:w-72'} ...`}>

// Main content padding adjusts
<div className={`transition-all duration-300 ${sidebarCollapsed ? 'lg:pl-20' : 'lg:pl-72'}`}>
```

**New Icons Imported:**
- `ChevronLeft`, `ChevronRight`, `PanelLeftClose`, `PanelLeft`

---

### 2. Map Page - Redesigned Layout

**Files:**
- `app/map/page.js`
- `styles/map.css`

Completely redesigned the map page layout:

#### A. Right Sidebar (Hazard Monitor Panel)

Moved the main map controls from left to right side:

- **Class:** `.map-right-sidebar`
- **Contains:** Status bar, stats, cyclone alerts, tabs (Locations/Alerts/Layers)
- **Toggle:** Chevron button appears when closed to reopen

**New State Variables:**
```jsx
const [rightPanelOpen, setRightPanelOpen] = useState(true);
const [leftNavOpen, setLeftNavOpen] = useState(false);
```

#### B. Left Navigation (Website Nav - Hidden by Default)

Added a slide-out navigation panel with website links:

- **Class:** `.map-left-nav`
- **Hidden by default**, opens via hamburger menu button
- **Contains:** Links to Dashboard, Report Hazard, My Reports, Map View, Community, Leaderboard, Safety Tips
- **Overlay:** Dark backdrop when open (`.left-nav-overlay`)

**Toggle Button:**
```jsx
<button
  onClick={() => setLeftNavOpen(!leftNavOpen)}
  className={`left-nav-toggle ${leftNavOpen ? 'hidden' : ''}`}
>
  <Menu className="w-5 h-5" />
</button>
```

#### C. New Icons Added

```jsx
import {
  ChevronLeft,
  FileText,
  MessageCircle,
  Trophy,
  Shield,
  Map,
  PanelRight
} from 'lucide-react';
```

#### D. CSS Changes

New classes added to `styles/map.css`:

```css
/* Left Navigation */
.map-left-nav { ... }           /* Slide-out nav panel */
.left-nav-header { ... }        /* Nav header with logo */
.left-nav-content { ... }       /* Nav links container */
.left-nav-item { ... }          /* Individual nav links */
.left-nav-toggle { ... }        /* Hamburger menu button */
.left-nav-overlay { ... }       /* Dark backdrop */

/* Right Sidebar */
.map-right-sidebar { ... }      /* Main controls panel */
.right-panel-toggle { ... }     /* Chevron to reopen */
```

**Responsive Behavior:**
- **Desktop (1024px+):** Right panel open by default, left nav hidden
- **Mobile:** Both panels hidden, accessed via mobile UI

---

## Project Architecture

### Key Components

| Component | Purpose |
|-----------|---------|
| `DashboardLayout.js` | Main layout wrapper with collapsible sidebar |
| `ProtectedRoute.js` | Auth guard for protected pages |
| `OceanMap.js` | Leaflet map container |
| `HeatmapLayer.js` | Heatmap visualization for reports |
| `ClusterLayer.js` | Marker clustering for reports |
| `CycloneLayer.js` | Cyclone track visualization |
| `WaveTrackLayer.js` | Ocean currents and wave height |

### State Management

- **Auth:** Zustand store in `context/AuthContext.js`
- **Map Data:** Custom hook `hooks/useMapData.js`

### Styling

- **Framework:** Tailwind CSS
- **Map Styles:** Custom CSS in `styles/map.css`
- **Theme:** Ocean/teal color scheme with glassmorphism effects

---

## User Roles

| Role | Access |
|------|--------|
| `citizen` | Dashboard, Report Hazard, My Reports, Map, Community |
| `authority` | Authority Dashboard, Reports Verification, Tickets, Alerts |
| `analyst` | Social Intelligence, Real-time Monitor, Geo Analysis |
| `authority_admin` | Full admin access, User Management, System Settings |

---

## Design Decisions

### Why Right Sidebar for Map?

1. **More natural for map interaction** - Left hand can use keyboard shortcuts while right panel is visible
2. **Matches Google Maps pattern** - Users familiar with info panels on right
3. **Better for LTR reading** - Map is primary, controls are secondary

### Why Hidden Left Nav?

1. **Maximizes map real estate** - Full-screen map experience
2. **Quick access when needed** - One click to access site navigation
3. **Consistent with mobile patterns** - Hamburger menu is familiar

---

## Running the Project

```bash
# Frontend
cd frontend
npm run dev

# Backend
cd backend
source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Known Issues

1. **Build Warning:** `useSearchParams()` in `/events/create` needs Suspense boundary
2. **ESLint:** Missing TypeScript dependency (non-blocking)

---

## Files Modified Today

```
frontend/
├── components/
│   └── DashboardLayout.js    # Collapsible sidebar
├── app/
│   └── map/
│       └── page.js           # New layout with right sidebar + left nav
└── styles/
    └── map.css               # New CSS classes for layout
```

---

## Tips for Future Claude Sessions

1. **Map page uses its own layout** - Not wrapped in DashboardLayout
2. **Check `map.css` for map-specific styles** - Separate from Tailwind
3. **Sidebar states are separate** - `sidebarCollapsed` (dashboard) vs `rightPanelOpen`/`leftNavOpen` (map)
4. **Mobile has different UI** - Bottom sheet and top bar, not sidebars
