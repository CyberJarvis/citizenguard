# CoastGuardians Mobile App API Endpoints
## Citizen-Side API Reference for Mobile Development

**Base URL:** `http://localhost:8000/api/v1` (Development)
**Production:** `https://your-domain.com/api/v1`

---

## Authentication Headers

For protected endpoints, include:
```
Authorization: Bearer <access_token>
```

---

## 1. Authentication APIs

### 1.1 Sign Up
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
  "message": "OTP sent to email/phone",
  "user_id": "USR_abc123",
  "requires_verification": true
}
```

### 1.2 Verify OTP
```http
POST /auth/verify-otp
Content-Type: application/json

{
  "user_id": "USR_abc123",
  "otp": "123456",
  "type": "email"  // or "phone"
}

Response (200):
{
  "success": true,
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 7200,
  "user": {
    "user_id": "USR_abc123",
    "name": "John Doe",
    "email": "user@example.com",
    "role": "citizen"
  }
}
```

### 1.3 Login
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
  "token_type": "bearer",
  "expires_in": 7200,
  "user": {
    "user_id": "USR_abc123",
    "name": "John Doe",
    "email": "user@example.com",
    "role": "citizen",
    "profile_picture": "https://...",
    "credibility_score": 75
  }
}
```

### 1.4 Google OAuth Login
```http
POST /auth/google/callback
Content-Type: application/json

{
  "id_token": "<google_id_token>"
}

Response (200):
{
  "success": true,
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "user": {...}
}
```

### 1.5 Refresh Token
```http
POST /auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGc..."
}

Response (200):
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "expires_in": 7200
}
```

### 1.6 Logout
```http
POST /auth/logout
Authorization: Bearer <access_token>

Response (200):
{
  "success": true,
  "message": "Logged out successfully"
}
```

### 1.7 Forgot Password
```http
POST /auth/forgot-password
Content-Type: application/json

{
  "email": "user@example.com"
}

Response (200):
{
  "success": true,
  "message": "Password reset OTP sent"
}
```

### 1.8 Reset Password
```http
POST /auth/reset-password
Content-Type: application/json

{
  "email": "user@example.com",
  "otp": "123456",
  "new_password": "NewSecurePass123!"
}

Response (200):
{
  "success": true,
  "message": "Password reset successful"
}
```

### 1.9 Get Current User
```http
GET /auth/me
Authorization: Bearer <access_token>

Response (200):
{
  "user_id": "USR_abc123",
  "name": "John Doe",
  "email": "user@example.com",
  "phone": "+919876543210",
  "role": "citizen",
  "profile_picture": "https://...",
  "credibility_score": 75,
  "total_reports": 12,
  "verified_reports": 10,
  "email_verified": true,
  "phone_verified": true,
  "created_at": "2025-01-15T10:30:00Z"
}
```

---

## 2. Profile APIs

### 2.1 Get Profile
```http
GET /profile/me
Authorization: Bearer <access_token>

Response (200):
{
  "user_id": "USR_abc123",
  "name": "John Doe",
  "email": "user@example.com",
  "phone": "+919876543210",
  "profile_picture": "https://...",
  "location": {
    "latitude": 19.076,
    "longitude": 72.877,
    "address": "Mumbai, Maharashtra",
    "region": "Maharashtra"
  },
  "notification_preferences": {
    "email": true,
    "sms": true,
    "push": true,
    "alert_types": ["tsunami", "cyclone", "high_waves"]
  },
  "credibility_score": 75,
  "total_reports": 12,
  "verified_reports": 10
}
```

### 2.2 Update Profile
```http
PUT /profile/me
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "John Doe Updated",
  "phone": "+919876543211",
  "location": {
    "latitude": 19.076,
    "longitude": 72.877,
    "address": "Mumbai, Maharashtra"
  },
  "notification_preferences": {
    "email": true,
    "sms": true,
    "push": true
  }
}

Response (200):
{
  "success": true,
  "user": {...}
}
```

### 2.3 Upload Profile Picture
```http
POST /profile/picture
Authorization: Bearer <access_token>
Content-Type: multipart/form-data

Form Data:
- image: <file>

Response (200):
{
  "success": true,
  "profile_picture": "https://..."
}
```

### 2.4 Update FCM Token (Push Notifications)
```http
PUT /profile/fcm-token
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "fcm_token": "<firebase_cloud_messaging_token>"
}

Response (200):
{
  "success": true
}
```

---

## 3. Hazard Reporting APIs

### 3.1 Submit Hazard Report
```http
POST /hazards
Authorization: Bearer <access_token>
Content-Type: multipart/form-data

Form Data:
- hazard_type: "high_waves"  // See hazard types below
- category: "natural"        // "natural" or "humanMade"
- latitude: 19.076
- longitude: 72.877
- address: "Juhu Beach, Mumbai"
- description: "High waves observed at Juhu Beach, approximately 3-4 meters"
- image: <file>              // Required image
- voice_note: <file>         // Optional audio file
- weather: {"temperature": 28, "wind_speed": 25}  // Optional JSON string

Response (201):
{
  "success": true,
  "report_id": "RPT_xyz789",
  "verification_status": "pending",
  "verification_score": 78.5,
  "verification_decision": "auto_approved",
  "message": "Report submitted successfully"
}
```

**Hazard Types:**
```
Natural:
- high_waves
- rip_current
- storm_surge
- coastal_flooding
- tsunami_warning
- jellyfish_bloom
- algal_bloom
- erosion

Human-Made:
- oil_spill
- plastic_pollution
- chemical_spill
- ship_wreck
- illegal_fishing
- beached_animals
```

### 3.2 Get My Reports
```http
GET /hazards/my-reports?page=1&page_size=20
Authorization: Bearer <access_token>

Response (200):
{
  "total": 12,
  "page": 1,
  "page_size": 20,
  "reports": [
    {
      "report_id": "RPT_xyz789",
      "hazard_type": "high_waves",
      "category": "natural",
      "description": "High waves at Juhu Beach",
      "location": {
        "latitude": 19.076,
        "longitude": 72.877,
        "address": "Juhu Beach, Mumbai"
      },
      "image_url": "https://...",
      "verification_status": "verified",
      "verification_score": 85.2,
      "created_at": "2025-12-01T10:30:00Z",
      "views": 45,
      "likes": 12
    }
  ]
}
```

### 3.3 Get Report Details
```http
GET /hazards/{report_id}
Authorization: Bearer <access_token>

Response (200):
{
  "report_id": "RPT_xyz789",
  "user_id": "USR_abc123",
  "user_name": "John Doe",
  "hazard_type": "high_waves",
  "category": "natural",
  "description": "High waves observed...",
  "location": {...},
  "image_url": "https://...",
  "voice_note_url": "https://...",
  "weather": {
    "temperature": 28,
    "wind_speed": 25,
    "humidity": 80
  },
  "verification_status": "verified",
  "verification_score": 85.2,
  "verification_result": {
    "layers": [
      {"name": "geofence", "status": "pass", "score": 95},
      {"name": "weather", "status": "pass", "score": 88},
      {"name": "text", "status": "pass", "score": 82},
      {"name": "image", "status": "pass", "score": 79},
      {"name": "reporter", "status": "pass", "score": 75}
    ]
  },
  "created_at": "2025-12-01T10:30:00Z",
  "verified_at": "2025-12-01T10:31:00Z",
  "views": 45,
  "likes": 12
}
```

### 3.4 Like/Unlike Report
```http
POST /hazards/{report_id}/like
Authorization: Bearer <access_token>

Response (200):
{
  "liked": true,  // or false if unliked
  "total_likes": 13
}
```

### 3.5 Delete My Report
```http
DELETE /hazards/{report_id}
Authorization: Bearer <access_token>

Response (200):
{
  "success": true,
  "message": "Report deleted"
}
```

---

## 4. Public Hazard Feed APIs

### 4.1 Get Verified Reports (Public Feed)
```http
GET /hazards?page=1&page_size=20&verification_status=verified
Authorization: Bearer <access_token>

Query Parameters:
- page: Page number (default: 1)
- page_size: Items per page (default: 20, max: 100)
- verification_status: "verified" (default for public)
- hazard_type: Filter by type (optional)
- category: "natural" or "humanMade" (optional)

Response (200):
{
  "total": 150,
  "page": 1,
  "page_size": 20,
  "reports": [...]
}
```

### 4.2 Get Map Data (For Map View)
```http
GET /hazards/map-data?hours=24&include_heatmap=true&include_clusters=true
Authorization: Bearer <access_token>

Query Parameters:
- hours: Time window in hours (1-168, default: 24)
- include_heatmap: Include heatmap points (default: true)
- include_clusters: Include cluster data (default: true)

Response (200):
{
  "success": true,
  "data": {
    "reports": [
      {
        "id": "RPT_xyz789",
        "hazard_type": "high_waves",
        "severity": "high",
        "latitude": 19.076,
        "longitude": 72.877,
        "verification_status": "verified",
        "created_at": "2025-12-01T10:30:00Z"
      }
    ],
    "heatmap_points": [
      [19.076, 72.877, 0.8],  // [lat, lon, weight]
      [13.082, 80.270, 0.6]
    ],
    "statistics": {
      "total_reports": 45,
      "critical_count": 5,
      "high_count": 12,
      "medium_count": 18,
      "low_count": 10
    }
  }
}
```

### 4.3 Get Ocean Data (Waves & Currents)
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
  "currentPaths": [
    {
      "name": "East India Coastal Current",
      "path": [[8.5, 80], [10, 80.2], ...],
      "color": "#22d3ee",
      "speed": "0.5-0.8 m/s",
      "direction": "Northward"
    }
  ]
}
```

---

## 5. Alerts APIs (Read-Only for Citizens)

### 5.1 Get Active Alerts
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
      "description": "Waves of 3-4 meters expected...",
      "alert_type": "high_waves",
      "severity": "high",
      "status": "active",
      "regions": ["Mumbai", "Thane"],
      "issued_at": "2025-12-01T08:00:00Z",
      "expires_at": "2025-12-02T08:00:00Z",
      "created_by": "INCOIS Authority"
    }
  ]
}
```

### 5.2 Get Alert Details
```http
GET /alerts/{alert_id}
Authorization: Bearer <access_token>

Response (200):
{
  "alert_id": "ALT_abc123",
  "title": "High Wave Warning - Mumbai Coast",
  "description": "Waves of 3-4 meters expected along Mumbai coastline...",
  "alert_type": "high_waves",
  "severity": "high",
  "status": "active",
  "regions": ["Mumbai", "Thane", "Raigad"],
  "coordinates": [
    {"lat": 19.076, "lon": 72.877},
    {"lat": 19.200, "lon": 72.900}
  ],
  "recommendations": [
    "Avoid beaches and coastal areas",
    "Fishermen should not venture into the sea",
    "Stay updated with local weather reports"
  ],
  "issued_at": "2025-12-01T08:00:00Z",
  "effective_from": "2025-12-01T10:00:00Z",
  "expires_at": "2025-12-02T08:00:00Z"
}
```

---

## 6. Multi-Hazard Real-Time APIs

### 6.1 Get Service Health
```http
GET /multi-hazard/health

Response (200):
{
  "status": "healthy",
  "monitored_locations": 30,
  "active_alerts": 2,
  "last_detection_cycle": "2025-12-01T13:05:00Z"
}
```

### 6.2 Get Monitored Locations
```http
GET /multi-hazard/public/locations

Response (200):
{
  "success": true,
  "locations": [
    {
      "location_id": "LOC_mumbai",
      "location_name": "Mumbai",
      "region": "Maharashtra",
      "coordinates": {"lat": 19.076, "lon": 72.877},
      "alert_level": 2,
      "active_hazards": ["high_waves"],
      "last_updated": "2025-12-01T13:05:00Z"
    }
  ]
}
```

### 6.3 Get Real-Time Alerts
```http
GET /multi-hazard/public/alerts?min_level=1&limit=100

Query Parameters:
- min_level: Minimum alert level 1-5 (default: 1)
- limit: Max results (default: 100)

Response (200):
{
  "success": true,
  "alerts": [
    {
      "alert_id": "MH_alert_123",
      "hazard_type": "high_waves",
      "alert_level": 3,
      "location_id": "LOC_mumbai",
      "location_name": "Mumbai",
      "coordinates": {"lat": 19.076, "lon": 72.877},
      "detected_at": "2025-12-01T13:00:00Z",
      "confidence": 0.85,
      "parameters": {
        "wave_height": 2.8,
        "wind_speed": 45
      },
      "recommendations": ["Avoid beaches", "Stay indoors"]
    }
  ]
}
```

### 6.4 Get Cyclone Data
```http
GET /multi-hazard/public/cyclone-data?include_forecast=true&include_surge=true

Response (200):
{
  "success": true,
  "hasActiveCyclone": true,
  "isDemo": false,
  "cyclone": {
    "name": "CYCLONE DANA",
    "category": 2,
    "maxWindSpeed": 120,
    "currentPosition": {"lat": 18.5, "lon": 87.2},
    "movementDirection": "NW",
    "movementSpeed": 15,
    "pressure": 980,
    "track": [
      {"lat": 17.0, "lon": 89.0, "time": "2025-12-01T00:00:00Z"},
      {"lat": 17.5, "lon": 88.5, "time": "2025-12-01T06:00:00Z"}
    ],
    "forecast": [
      {"lat": 19.0, "lon": 86.5, "time": "2025-12-01T18:00:00Z"},
      {"lat": 20.0, "lon": 85.5, "time": "2025-12-02T00:00:00Z"}
    ],
    "windRadii": {
      "34kt": 200,
      "50kt": 100,
      "64kt": 50
    }
  },
  "surge": {
    "maxHeight": 2.5,
    "affectedCoastline": ["Odisha", "West Bengal"],
    "zones": [...]
  }
}
```

---

## 7. Notifications APIs

### 7.1 Get Notifications
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
      "message": "High waves expected in your region",
      "is_read": false,
      "alert_id": "ALT_abc123",
      "created_at": "2025-12-01T10:00:00Z"
    },
    {
      "notification_id": "NOT_xyz789",
      "type": "report_update",
      "severity": "info",
      "title": "Report Verified",
      "message": "Your hazard report has been verified",
      "is_read": true,
      "report_id": "RPT_xyz789",
      "created_at": "2025-12-01T09:00:00Z"
    }
  ]
}
```

### 7.2 Get Unread Count
```http
GET /notifications/stats
Authorization: Bearer <access_token>

Response (200):
{
  "unread_count": 5,
  "total_count": 25,
  "by_type": {
    "alert": 3,
    "report_update": 2,
    "system": 0
  }
}
```

### 7.3 Mark Notification as Read
```http
PUT /notifications/{notification_id}
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "is_read": true
}

Response (200):
{
  "success": true
}
```

### 7.4 Mark All as Read
```http
POST /notifications/mark-all-read
Authorization: Bearer <access_token>

Response (200):
{
  "success": true,
  "marked_count": 5
}
```

### 7.5 Delete Notification
```http
DELETE /notifications/{notification_id}
Authorization: Bearer <access_token>

Response (200):
{
  "success": true
}
```

---

## 8. Tickets APIs (For Citizen Support)

### 8.1 Get My Tickets
```http
GET /tickets/my?page=1&page_size=20
Authorization: Bearer <access_token>

Response (200):
{
  "total": 3,
  "tickets": [
    {
      "ticket_id": "TKT_abc123",
      "report_id": "RPT_xyz789",
      "status": "in_progress",
      "priority": "medium",
      "subject": "Report Verification Issue",
      "created_at": "2025-12-01T10:00:00Z",
      "last_message_at": "2025-12-01T11:00:00Z",
      "unread_messages": 2
    }
  ]
}
```

### 8.2 Get Ticket Details
```http
GET /tickets/{ticket_id}
Authorization: Bearer <access_token>

Response (200):
{
  "ticket_id": "TKT_abc123",
  "report_id": "RPT_xyz789",
  "status": "in_progress",
  "priority": "medium",
  "created_at": "2025-12-01T10:00:00Z",
  "messages": [
    {
      "sender_id": "USR_abc123",
      "sender_name": "John Doe",
      "sender_role": "citizen",
      "content": "My report was rejected but...",
      "timestamp": "2025-12-01T10:00:00Z"
    },
    {
      "sender_id": "USR_analyst1",
      "sender_name": "Analyst Team",
      "sender_role": "analyst",
      "content": "We are reviewing your report...",
      "timestamp": "2025-12-01T11:00:00Z"
    }
  ]
}
```

### 8.3 Send Ticket Message
```http
POST /tickets/{ticket_id}/messages
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "content": "Thank you for the update. Here is additional information..."
}

Response (201):
{
  "success": true,
  "message_id": "MSG_xyz789"
}
```

---

## 9. Voice Transcription API

### 9.1 Transcribe Voice Note
```http
POST /transcription
Authorization: Bearer <access_token>
Content-Type: multipart/form-data

Form Data:
- audio: <file>  // WAV, MP3, or WEBM (max 5MB)

Response (200):
{
  "success": true,
  "transcript": "I am reporting high waves at Marina Beach...",
  "language": "en",
  "confidence": 0.95
}
```

---

## 10. Safety Information API

### 10.1 Get Safety Tips
```http
GET /safety/tips?hazard_type=tsunami

Response (200):
{
  "hazard_type": "tsunami",
  "tips": [
    "Move to higher ground immediately",
    "Stay away from beaches and coastal areas",
    "Listen to official warnings",
    "Do not return until authorities declare it safe"
  ],
  "emergency_contacts": [
    {"name": "INCOIS", "phone": "1800-xxx-xxxx"},
    {"name": "Disaster Management", "phone": "108"}
  ]
}
```

---

## Error Response Format

All error responses follow this format:

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": [...]  // Optional field-level errors
  }
}
```

**Common Error Codes:**
| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Invalid input data |
| `UNAUTHORIZED` | 401 | Missing/invalid token |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `RATE_LIMITED` | 429 | Too many requests |
| `SERVER_ERROR` | 500 | Internal server error |

---

## Rate Limiting

| Endpoint Type | Limit |
|---------------|-------|
| Auth endpoints | 5 requests/15 min |
| Report submission | 10 requests/hour |
| General API | 100 requests/min |

---

## WebSocket Connection (Real-Time Updates)

```javascript
// Connect to WebSocket for real-time notifications
const ws = new WebSocket('wss://your-domain.com/ws/notifications');

ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'auth',
    token: '<access_token>'
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // Handle real-time notification
  // Types: 'alert', 'report_update', 'ticket_message'
};
```

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

### Support
- [ ] View my tickets
- [ ] Send messages
- [ ] Receive responses

---

## Recommended Mobile Tech Stack

### React Native / Flutter
- **HTTP Client:** Axios / Dio
- **State Management:** Redux / Provider
- **Maps:** react-native-maps / google_maps_flutter
- **Push Notifications:** Firebase Cloud Messaging
- **Image Picker:** react-native-image-picker / image_picker
- **Voice Recording:** react-native-audio-recorder-player
- **Location:** react-native-geolocation / geolocator
- **Storage:** AsyncStorage / shared_preferences

---

## Testing the APIs

### Using cURL
```bash
# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'

# Get Map Data
curl -X GET "http://localhost:8000/api/v1/hazards/map-data?hours=24" \
  -H "Authorization: Bearer <token>"

# Submit Report
curl -X POST http://localhost:8000/api/v1/hazards \
  -H "Authorization: Bearer <token>" \
  -F "hazard_type=high_waves" \
  -F "category=natural" \
  -F "latitude=19.076" \
  -F "longitude=72.877" \
  -F "address=Juhu Beach, Mumbai" \
  -F "description=High waves observed" \
  -F "image=@photo.jpg"
```

---

**Document Version:** 1.0
**Last Updated:** December 1, 2025
**API Version:** v1
