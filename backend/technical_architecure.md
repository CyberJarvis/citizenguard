# CoastGuardian: Technical Architecture Document

**SIH25039 | INCOIS Ocean Hazard Reporting Platform**  
**Version 2.0 - Executive Submission | Updated Tech Stack**

---

## 1. EXECUTIVE SUMMARY

**Problem Context**  
India's 7,517 km coastline faces tsunamis, storm surges, and high waves affecting 250+ million people. Current early warning systems lack real-time ground truth from citizens and miss critical social media intelligence during disasters.

**Solution: CoastGuardian**  
An **offline-first Progressive Web App (PWA)** enabling:

- **Citizens**: Report hazards with multimedia even without internet connectivity
- **AI Analytics**: Monitor social media (Twitter/Facebook/YouTube) for hazard trends using multilingual NLP
- **Analysts**: Verify reports through correlation-based validation dashboards
- **Admins**: Manage alerts, users, and system configuration
- **Automated Intelligence**: Generate risk hotspots using multi-source data fusion

**Core Innovation**  
**Offline-First Architecture**: Service Workers + IndexedDB enable full functionality in zero-connectivity coastal areas, with automatic background sync when connection resumes.

**Updated Technology Foundation**

- **Frontend**: Next.js 14 (PWA) with TypeScript, Tailwind CSS, Leaflet Maps
- **Backend**: FastAPI (Python) with async architecture
- **Database**: MongoDB with geospatial indexing
- **Intelligence Layer**: Kafka + Elasticsearch + IndicBERT (NLP)
- **Infrastructure**: Docker + Kubernetes on AWS/GCP

**Key Metrics (Target Year 1)**

- 10,000+ active citizen reporters
- 100+ verified reports/day
- <2s page load, <500ms API response
- 99.5% uptime, >95% offline sync success

---

## 2. SYSTEM ARCHITECTURE OVERVIEW

### 2.1 Architectural Paradigm

**Microservices + Event-Driven + Offline-First**

```
┌─────────────────────────────────────────────────────┐
│         PRESENTATION LAYER (Next.js PWA)            │
│   Citizen App | Analyst Dashboard | Admin Panel     │
│   Service Worker + IndexedDB (Offline Storage)      │
└─────────────────────────────────────────────────────┘
                        ↕ HTTPS/REST
┌─────────────────────────────────────────────────────┐
│          API GATEWAY (FastAPI + Traefik)            │
│   Auth • Rate Limiting • Request Routing • CORS     │
└─────────────────────────────────────────────────────┘
                        ↕
┌─────────────────────────────────────────────────────┐
│           MICROSERVICES LAYER (FastAPI)             │
│ Reports | Social Analytics | Hotspot | Alerts       │
│ Users | Weather | Media | Verification              │
└─────────────────────────────────────────────────────┘
                        ↕
┌─────────────────────────────────────────────────────┐
│    EVENT STREAMING (Apache Kafka)                   │
│  report.created | social.classified | hotspot.alert │
└─────────────────────────────────────────────────────┘
                        ↕
┌─────────────────────────────────────────────────────┐
│              DATA LAYER                             │
│ MongoDB (Reports/Users) | Elasticsearch (Social)    │
│ Redis (Cache/Sessions) | MinIO/S3 (Media)           │
└─────────────────────────────────────────────────────┘
                        ↕
┌─────────────────────────────────────────────────────┐
│         EXTERNAL INTEGRATIONS                       │
│ INCOIS API | Weather | Twitter | FCM | SMS Gateway  │
└─────────────────────────────────────────────────────┘
```

### 2.2 Critical Data Flows

**Offline Report Submission**

```
Citizen (No Internet) → Form Fill → Service Worker → IndexedDB Queue
→ Network Detected → Background Sync → FastAPI /reports endpoint
→ Media Upload (S3) → MongoDB Write → Kafka Event
→ Hotspot Calculation → Dashboard Update
```

**Social Media Intelligence Pipeline**

```
Twitter Stream API → Kafka (raw_posts topic)
→ NLP Service (IndicBERT) → Classification + Entity Extraction
→ Elasticsearch Index → Analyst Dashboard Feed
→ Misinformation Flagging → Alert Trigger (if critical)
```

**Alert Distribution Flow**

```
Admin Creates Alert → Geospatial Query (find users in polygon)
→ Batch Processing (500 users/batch) → Multi-channel Dispatch
→ FCM (Push) + Twilio (SMS) + SendGrid (Email)
→ Delivery Status Tracking → Analytics Dashboard
```

---

## 3. TECHNOLOGY STACK RATIONALE

### 3.1 Core Stack Decisions

| Component            | Technology                     | Justification                                                                                                                                                                                       |
| -------------------- | ------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Backend API**      | **FastAPI (Python 3.11+)**     | • Async/await for high concurrency<br>• Auto-generated OpenAPI docs<br>• Pydantic validation (type safety)<br>• Native async MongoDB support<br>• ML library ecosystem (scikit-learn, transformers) |
| **Frontend**         | **Next.js 14 (React 18)**      | • Built-in PWA support (next-pwa)<br>• Server components + streaming<br>• Image optimization<br>• File-system routing<br>• Vercel deployment optimized                                              |
| **Primary Database** | **MongoDB 7.x**                | • Native GeoJSON support (2dsphere indexes)<br>• Flexible schema (evolving report types)<br>• Horizontal scaling (sharding)<br>• Change streams for real-time updates                               |
| **Search Engine**    | **Elasticsearch 8.x**          | • Full-text search (multilingual)<br>• Aggregations for analytics<br>• Geospatial queries<br>• Social media post indexing                                                                           |
| **Cache/Session**    | **Redis 7.x**                  | • Sub-millisecond latency<br>• Pub/sub for real-time events<br>• Rate limiting counters<br>• Session storage                                                                                        |
| **Event Streaming**  | **Apache Kafka**               | • Decouples microservices<br>• Event sourcing for audit trails<br>• Guaranteed message delivery<br>• Real-time processing pipelines                                                                 |
| **NLP Models**       | **IndicBERT (HuggingFace)**    | • Pre-trained on 12 Indian languages<br>• Fine-tuned for disaster keywords<br>• mBERT fallback for accuracy                                                                                         |
| **Maps**             | **Leaflet.js + OpenStreetMap** | • Offline tile caching<br>• Lightweight (38KB gzipped)<br>• GeoJSON layer support                                                                                                                   |

### 3.2 Infrastructure Choices

**Container Orchestration**: Kubernetes (EKS/GKE)

- Auto-scaling (3-20 pods based on CPU/memory)
- Multi-AZ deployment for 99.95% uptime
- Rolling updates with zero downtime

**CI/CD**: GitHub Actions → Docker → Kubernetes  
**Monitoring**: Prometheus + Grafana + ELK Stack  
**CDN**: Cloudflare (DDoS protection + edge caching)

---

## 4. MODULE 1: AUTHENTICATION & AUTHORIZATION SYSTEM

### 4.1 Design Principles

- **Role-Based Access Control (RBAC)** with 3 tiers: Citizen, Analyst, Admin
- **JWT-based stateless authentication** with refresh tokens
- **OTP for citizens** (SMS via Twilio), **password for officials**

### 4.2 Authentication Flows

**Citizen Registration/Login**

```python
# FastAPI endpoint
@router.post("/auth/citizen/login")
async def citizen_login(phone: str):
    # Generate 6-digit OTP
    otp = generate_otp()

    # Store in Redis (5-min expiry)
    await redis.setex(f"otp:{phone}", 300, otp)

    # Send via Twilio
    await sms_service.send(phone, f"CoastGuardian OTP: {otp}")

    return {"message": "OTP sent", "expires_in": 300}

@router.post("/auth/citizen/verify")
async def verify_otp(phone: str, otp: str):
    stored_otp = await redis.get(f"otp:{phone}")

    if otp != stored_otp:
        raise HTTPException(401, "Invalid OTP")

    # Create/fetch user
    user = await User.find_or_create(phone=phone)

    # Generate tokens
    access_token = create_jwt(user.id, expires_delta=timedelta(hours=2))
    refresh_token = create_jwt(user.id, expires_delta=timedelta(days=7))

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": user.dict()
    }
```

**Analyst/Admin Login**

```python
@router.post("/auth/staff/login")
async def staff_login(credentials: LoginSchema):
    user = await User.find_one({"email": credentials.email})

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(401, "Invalid credentials")

    if user.role not in ["analyst", "admin"]:
        raise HTTPException(403, "Access denied")

    # Optional 2FA check for admins
    if user.role == "admin" and user.two_factor_enabled:
        # Trigger TOTP verification flow
        return {"requires_2fa": True, "temp_token": create_temp_token(user.id)}

    return generate_tokens(user)
```

### 4.3 Permission Matrix

| Feature          | Citizen | Analyst | Admin |
| ---------------- | ------- | ------- | ----- |
| Submit Reports   | ✅      | ✅      | ✅    |
| View Own Reports | ✅      | ✅      | ✅    |
| View All Reports | ❌      | ✅      | ✅    |
| Verify Reports   | ❌      | ✅      | ✅    |
| Access Analytics | ❌      | ✅      | ✅    |
| Create Alerts    | ❌      | ❌      | ✅    |
| Manage Users     | ❌      | ❌      | ✅    |
| System Config    | ❌      | ❌      | ✅    |

### 4.4 Security Measures

- **Password Hashing**: bcrypt (12 rounds)
- **JWT Secret**: 256-bit key rotated monthly
- **Rate Limiting**: 5 login attempts/15 min per IP
- **Session Management**: Redis with automatic expiry
- **Audit Logging**: All auth events logged to MongoDB with IP, timestamp, user-agent

---

## 5. MODULE 2: CITIZEN REPORTING SYSTEM

### 5.1 Report Submission Flow

**Frontend (Next.js)**

```typescript
// /app/(app)/reports/new/page.tsx
export default function NewReportPage() {
  const [formData, setFormData] = useState({
    hazardType: "",
    severity: "",
    description: "",
    location: null,
    media: [],
    voiceNote: null,
  });

  const handleSubmit = async () => {
    // Works offline - queues in IndexedDB
    if (!navigator.onLine) {
      await offlineQueue.add(formData);
      showToast("Report queued for sync");
      return;
    }

    // Online - direct submission
    const formData = new FormData();
    formData.append("hazard_type", formData.hazardType);
    // ... append other fields

    const response = await fetch("/api/v1/reports", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: formData,
    });
  };
}
```

**Backend (FastAPI)**

```python
# app/api/v1/reports.py
from fastapi import APIRouter, UploadFile, Depends
from app.services.media import MediaService
from app.services.credibility import CredibilityService

router = APIRouter()

@router.post("/reports")
async def create_report(
    hazard_type: str = Form(...),
    severity: str = Form(...),
    description: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    media: List[UploadFile] = File(default=[]),
    voice_note: UploadFile = File(default=None),
    current_user: User = Depends(get_current_user)
):
    # 1. Validate inputs
    validate_hazard_type(hazard_type)

    # 2. Upload media to S3/MinIO
    media_urls = []
    for file in media:
        # Compress images (JPEG quality 80, max 1920px)
        compressed = await MediaService.compress_image(file)
        url = await MediaService.upload(compressed, f"reports/{report_id}/{file.filename}")
        media_urls.append(url)

    # 3. Transcribe voice note (Google Speech API)
    transcription = None
    if voice_note:
        audio_url = await MediaService.upload(voice_note, f"reports/{report_id}/voice.mp3")
        transcription = await SpeechService.transcribe(audio_url, language="hi-IN")

    # 4. Fetch weather data for location
    weather = await WeatherService.get_current(latitude, longitude)

    # 5. Calculate credibility score
    credibility_score = await CredibilityService.calculate(
        user=current_user,
        has_media=len(media) > 0,
        description_length=len(description)
    )

    # 6. Create report document
    report = Report(
        report_id=generate_id(),
        user_id=current_user.id,
        hazard_type=hazard_type,
        severity=severity,
        description=description,
        location={"type": "Point", "coordinates": [longitude, latitude]},
        media=media_urls,
        voice_note={"url": audio_url, "transcription": transcription},
        weather=weather.dict(),
        credibility_score=credibility_score,
        status="pending",
        reported_at=datetime.utcnow()
    )

    # 7. Save to MongoDB
    await report.insert()

    # 8. Emit Kafka event for downstream processing
    await kafka_producer.send("report.created", report.dict())

    # 9. Return response
    return {"report_id": report.report_id, "status": "pending", "credibility_score": credibility_score}
```

### 5.2 Credibility Scoring Algorithm

```python
class CredibilityService:
    @staticmethod
    async def calculate(user: User, has_media: bool, description_length: int) -> int:
        base_score = 50

        # Historical accuracy bonus (0-30 points)
        total_reports = await Report.count_documents({"user_id": user.id})
        verified_reports = await Report.count_documents({
            "user_id": user.id,
            "status": "verified"
        })

        if total_reports > 0:
            accuracy_ratio = verified_reports / total_reports
            base_score += int(accuracy_ratio * 30)

        # Media attachment bonus (+5 per photo/video, max 15)
        if has_media:
            base_score += min(15, 5 * len(media))

        # Detailed description bonus (+5 if >50 words)
        if description_length > 250:  # ~50 words
            base_score += 5

        # False report penalty (-10 per false report)
        false_reports = await Report.count_documents({
            "user_id": user.id,
            "status": "rejected"
        })
        base_score -= (false_reports * 10)

        # Clamp to 0-100
        return max(0, min(100, base_score))
```

### 5.3 Data Model (MongoDB)

```python
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class Report(BaseModel):
    report_id: str = Field(default_factory=generate_id)
    user_id: str
    hazard_type: str  # tsunami, storm_surge, high_waves, coastal_current, swell_surge
    severity: str  # low, medium, high, critical
    description: str
    location: dict  # GeoJSON Point: {"type": "Point", "coordinates": [lon, lat]}
    media: List[str] = []  # S3 URLs
    voice_note: Optional[dict] = None  # {"url": str, "transcription": str, "language": str}
    weather: Optional[dict] = None  # {"temp": float, "wind_speed": float, "wave_height": float}
    status: str = "pending"  # pending, verified, rejected
    credibility_score: int
    verified_by: Optional[str] = None
    verification_notes: Optional[str] = None
    reported_at: datetime
    verified_at: Optional[datetime] = None

    class Config:
        collection = "reports"
        indexes = [
            [("report_id", 1)],  # Unique
            [("user_id", 1)],
            [("location", "2dsphere")],  # Geospatial
            [("status", 1), ("reported_at", -1)],  # Compound for queries
            [("hazard_type", 1)]
        ]
```

---

## 6. MODULE 3: OFFLINE-FIRST INFRASTRUCTURE

### 6.1 Service Worker Architecture

**Core Strategy**: Cache-First for static assets, Network-First with cache fallback for API calls

```javascript
// public/service-worker.js
const CACHE_VERSION = "v1.2.0";
const STATIC_CACHE = `static-${CACHE_VERSION}`;
const DYNAMIC_CACHE = `dynamic-${CACHE_VERSION}`;

// Cache static assets on install
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => {
      return cache.addAll([
        "/",
        "/offline",
        "/manifest.json",
        "/_next/static/css/app.css",
        "/_next/static/chunks/main.js",
        // Map tiles for offline use
        "/map-tiles/india-coast-z8.mbtiles",
      ]);
    })
  );
  self.skipWaiting();
});

// Intercept fetch requests
self.addEventListener("fetch", (event) => {
  const { request } = event;

  // API requests - Network first, cache fallback
  if (request.url.includes("/api/")) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          // Cache successful responses
          if (response.status === 200) {
            const clonedResponse = response.clone();
            caches.open(DYNAMIC_CACHE).then((cache) => {
              cache.put(request, clonedResponse);
            });
          }
          return response;
        })
        .catch(() => {
          // Fallback to cache
          return caches.match(request).then((cachedResponse) => {
            if (cachedResponse) {
              return new Response(cachedResponse.body, {
                ...cachedResponse,
                headers: {
                  ...cachedResponse.headers,
                  "X-From-Cache": "true",
                },
              });
            }
            return new Response("Offline", { status: 503 });
          });
        })
    );
  }

  // Static assets - Cache first
  else {
    event.respondWith(
      caches.match(request).then((cachedResponse) => {
        return cachedResponse || fetch(request);
      })
    );
  }
});

// Background sync for queued reports
self.addEventListener("sync", (event) => {
  if (event.tag === "sync-reports") {
    event.waitUntil(syncPendingReports());
  }
});

async function syncPendingReports() {
  const db = await openIndexedDB();
  const pendingReports = await db.getAll("pending_reports");

  for (const report of pendingReports) {
    try {
      const response = await fetch("/api/v1/reports", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${report.token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(report.data),
      });

      if (response.ok) {
        await db.delete("pending_reports", report.id);
        // Notify user
        self.registration.showNotification("Report Synced", {
          body: `Your ${report.data.hazard_type} report has been submitted.`,
          icon: "/icon-192.png",
        });
      }
    } catch (error) {
      console.error("Sync failed:", error);
      // Will retry on next sync event
    }
  }
}
```

### 6.2 IndexedDB Schema

```typescript
// lib/offline/db.ts
import { openDB, DBSchema } from "idb";

interface CoastGuardianDB extends DBSchema {
  pending_reports: {
    key: string;
    value: {
      id: string;
      data: any;
      token: string;
      created_at: number;
      retry_count: number;
    };
  };
  cached_reports: {
    key: string;
    value: any;
    indexes: { "by-date": number };
  };
  map_tiles: {
    key: string;
    value: Blob;
  };
  user_profile: {
    key: "current_user";
    value: any;
  };
}

export const initDB = async () => {
  return openDB<CoastGuardianDB>("CoastGuardian-offline", 1, {
    upgrade(db) {
      // Pending reports queue
      db.createObjectStore("pending_reports", { keyPath: "id" });

      // Cached reports for offline viewing
      const reportsStore = db.createObjectStore("cached_reports", {
        keyPath: "report_id",
      });
      reportsStore.createIndex("by-date", "reported_at");

      // Map tiles
      db.createObjectStore("map_tiles");

      // User profile
      db.createObjectStore("user_profile");
    },
  });
};
```

### 6.3 Network-Aware UI

```typescript
// components/NetworkIndicator.tsx
export function NetworkIndicator() {
  const [online, setOnline] = useState(navigator.onLine);
  const [connectionType, setConnectionType] = useState<string>("unknown");

  useEffect(() => {
    const updateOnlineStatus = () => setOnline(navigator.onLine);

    window.addEventListener("online", updateOnlineStatus);
    window.addEventListener("offline", updateOnlineStatus);

    // Detect connection type (4G, 3G, 2G)
    if ("connection" in navigator) {
      const conn = (navigator as any).connection;
      setConnectionType(conn.effectiveType);

      conn.addEventListener("change", () => {
        setConnectionType(conn.effectiveType);
      });
    }

    return () => {
      window.removeEventListener("online", updateOnlineStatus);
      window.removeEventListener("offline", updateOnlineStatus);
    };
  }, []);

  return (
    <div className={`network-indicator ${online ? "online" : "offline"}`}>
      {online ? (
        <>
          <WifiIcon /> {connectionType.toUpperCase()}
        </>
      ) : (
        <>
          <WifiOffIcon /> OFFLINE MODE
        </>
      )}
    </div>
  );
}
```

---

## 7. MODULE 4: SOCIAL MEDIA INTELLIGENCE ENGINE

### 7.1 Data Collection Pipeline

**Twitter/X Stream (Real-time)**

```python
# app/services/social/twitter_stream.py
import tweepy
from kafka import KafkaProducer

class TwitterStreamListener(tweepy.StreamingClient):
    def __init__(self, bearer_token):
        super().__init__(bearer_token)
        self.kafka_producer = KafkaProducer(
            bootstrap_servers=['kafka:9092'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )

    def on_tweet(self, tweet):
        # Send raw tweet to Kafka
        self.kafka_producer.send('social.raw_posts', {
            'post_id': tweet.id,
            'platform': 'twitter',
            'content': tweet.text,
            'author': tweet.author_id,
            'created_at': tweet.created_at.isoformat(),
            'location': self.extract_location(tweet),
            'engagement': {
                'likes': tweet.public_metrics['like_count'],
                'retweets': tweet.public_metrics['retweet_count']
            }
        })

    @staticmethod
    def extract_location(tweet):
        if tweet.geo:
            return {
                "type": "Point",
                "coordinates": [tweet.geo.coordinates.longitude,
                              tweet.geo.coordinates.latitude]
            }
        return None

# Start streaming with hazard keywords
keywords = [
    # English
    "tsunami", "storm surge", "high waves", "coastal flooding",
    # Hindi
    "सुनामी", "तूफान", "ऊंची लहरें",
    # Tamil
    "சுனாமி", "கடல் அலைகள்",
    # Telugu
    "సునామీ", "తుఫాను"
]

stream = TwitterStreamListener(bearer_token=TWITTER_BEARER_TOKEN)
stream.filter(tweet_fields=['geo', 'public_metrics'], expansions=['geo.place_id'])
stream.add_rules(tweepy.StreamRule(" OR ".join(keywords)))
```

### 7.2 NLP Classification Pipeline

```python
# app/services/nlp/classifier.py
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

class HazardClassifier:
    def __init__(self):
        # Load IndicBERT fine-tuned on disaster corpus
        self.tokenizer = AutoTokenizer.from_pretrained("ai4bharat/indic-bert")
        self.model = AutoModelForSequenceClassification.from_pretrained(
            "models/indicbert-disaster-classification"
        )
        self.model.eval()

    async def classify(self, text: str, language: str = "auto") -> dict:
        # 1. Language detection
        detected_lang = self.detect_language(text) if language == "auto" else language

        # 2. Tokenize
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            max_length=512,
            truncation=True,
            padding=True
        )

        # 3. Inference
        with torch.no_grad():
            outputs = self.model(**inputs)
            probabilities = torch.softmax(outputs.logits, dim=1)

        # 4. Extract predictions
        hazard_types = ["tsunami", "storm_surge", "high_waves", "coastal_current", "swell_surge", "other"]
        hazard_probs = probabilities[0].tolist()

        predicted_idx = torch.argmax(probabilities, dim=1).item()
        confidence = hazard_probs[predicted_idx]

        # 5. Urgency scoring (keyword-based heuristic)
        urgency = self.calculate_urgency(text, detected_lang)

        # 6. Sentiment analysis
        sentiment = self.analyze_sentiment(text)

        # 7. Entity extraction (locations, dates)
        entities = self.extract_entities(text, detected_lang)

        return {
            "is_hazard_related": confidence > 0.7,
            "hazard_type": hazard_types[predicted_idx] if confidence > 0.7 else None,
            "confidence": round(confidence, 3),
            "language": detected_lang,
            "urgency": urgency,  # low, medium, high
            "sentiment": sentiment,  # negative, neutral, positive
            "entities": entities,
            "misinformation_flags": self.check_misinformation(text)
        }

    def calculate_urgency(self, text: str, language: str) -> str:
        urgent_keywords = {
            "en": ["urgent", "emergency", "evacuate", "immediate", "danger"],
            "hi": ["तत्काल", "खतरा", "आपातकाल"],
            "ta": ["அவசரம்", "ஆபத்து"],
            "te": ["అత్యవసరం", "ప్రమాదం"]
        }

        text_lower = text.lower()
        matches = sum(1 for kw in urgent_keywords.get(language, []) if kw in text_lower)

        if matches >= 2:
            return "high"
        elif matches == 1:
            return "medium"
        return "low"

    def check_misinformation(self, text: str) -> dict:
        flags = []

        # Check for common misinformation patterns
        if "forward this" in text.lower() or "share immediately" in text.lower():
            flags.append("viral_chain")

        if "confirmed by whatsapp" in text.lower():
            flags.append("unverified_source")

        # Check for exaggerated numbers
        import re
        numbers = re.findall(r'\d+', text)
        if any(int(n) > 1000 for n in numbers if n.isdigit()):
            flags.append("exaggerated_claims")

        return {
            "is_flagged": len(flags) > 0,
            "flags": flags
        }
```

### 7.3 Kafka Consumer for Processing

```python
# app/workers/social_processor.py
from kafka import KafkaConsumer
from elasticsearch import AsyncElasticsearch

consumer = KafkaConsumer(
    'social.raw_posts',
    bootstrap_servers=['kafka:9092'],
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)

es = AsyncElasticsearch(['http://elasticsearch:9200'])
classifier = HazardClassifier()

async def process_social_posts():
    for message in consumer:
        post = message.value

        # Classify with NLP
        classification = await classifier.classify(
            text=post['content'],
            language="auto"
        )

        # Only index if hazard-related
        if classification['is_hazard_related']:
            await es.index(
                index="social_posts",
                document={
                    **post,
                    "classification": classification,
                    "indexed_at": datetime.utcnow().isoformat()
                }
            )

            # If high urgency + credible, trigger alert
            if (classification['urgency'] == 'high' and
                not classification['misinformation_flags']['is_flagged']):
                await kafka_producer.send('alerts.social_trigger', post)
```

---

## 8. MODULE 5: ANALYST VERIFICATION DASHBOARD

### 8.1 Verification Queue API

```python
# app/api/v1/analyst.py
@router.get("/analyst/verification/queue")
async def get_verification_queue(
    priority: str = Query("all"),  # all, high, medium, low
    limit: int = Query(20),
    skip: int = Query(0),
    current_user: User = Depends(require_analyst_role)
):
    # Build query
    query = {"status": "pending"}

    if priority != "all":
        query["severity"] = priority

    # Fetch with correlation data
    reports = await Report.find(query) \
        .sort([("severity", -1), ("reported_at", -1)]) \
        .skip(skip) \
        .limit(limit) \
        .to_list()

    # Enrich with correlation data
    enriched_reports = []
    for report in reports:
        # Find nearby reports (50km, last 24h)
        nearby = await find_nearby_reports(
            location=report.location,
            radius_km=50,
            time_window_hours=24
        )

        # Find social media mentions
        social_posts = await search_social_posts(
            location=report.location,
            radius_km=25,
            hazard_type=report.hazard_type
        )

        # Get weather data
        weather = await WeatherService.get_current(
            report.location['coordinates'][1],
            report.location['coordinates'][0]
        )

        enriched_reports.append({
            **report.dict(),
            "correlation": {
                "nearby_reports": len(nearby),
                "social_mentions": len(social_posts),
                "weather_severity": classify_weather_severity(weather)
            }
        })

    return {"reports": enriched_reports, "total": await Report.count_documents(query)}
```

### 8.2 Verification Actions

```python
@router.post("/analyst/verification/{report_id}/approve")
async def approve_report(
    report_id: str,
    notes: str = Body(None),
    current_user: User = Depends(require_analyst_role)
):
    report = await Report.find_one({"report_id": report_id})

    if not report:
        raise HTTPException(404, "Report not found")

    # Update report status
    report.status = "verified"
    report.verified_by = current_user.id
    report.verification_notes = notes
    report.verified_at = datetime.utcnow()
    await report.save()

    # Update user credibility (positive reinforcement)
    user = await User.find_one({"user_id": report.user_id})
    user.credibility_score = min(100, user.credibility_score + 2)
    await user.save()

    # Emit Kafka event for hotspot recalculation
    await kafka_producer.send("report.verified", report.dict())

    return {"status": "verified", "credibility_updated": True}

@router.post("/analyst/verification/{report_id}/reject")
async def reject_report(
    report_id: str,
    reason: str = Body(...),
    current_user: User = Depends(require_analyst_role)
):
    report = await Report.find_one({"report_id": report_id})

    # Update report
    report.status = "rejected"
    report.verified_by = current_user.id
    report.verification_notes = reason
    report.verified_at = datetime.utcnow()
    await report.save()

    # Update user credibility (penalty)
    user = await User.find_one({"user_id": report.user_id})
    user.credibility_score = max(0, user.credibility_score - 10)
    await user.save()

    return {"status": "rejected"}
```

### 8.3 Analytics Endpoints

```python
@router.get("/analyst/analytics/trends")
async def get_trends(
    start_date: datetime = Query(...),
    end_date: datetime = Query(...),
    group_by: str = Query("day")  # hour, day, week
):
    pipeline = [
        {
            "$match": {
                "reported_at": {"$gte": start_date, "$lte": end_date},
                "status": "verified"
            }
        },
        {
            "$group": {
                "_id": {
                    "date": {"$dateTrunc": {"date": "$reported_at", "unit": group_by}},
                    "hazard_type": "$hazard_type"
                },
                "count": {"$sum": 1},
                "avg_severity": {"$avg": {"$switch": {
                    "branches": [
                        {"case": {"$eq": ["$severity", "low"]}, "then": 1},
                        {"case": {"$eq": ["$severity", "medium"]}, "then": 2},
                        {"case": {"$eq": ["$severity", "high"]}, "then": 3},
                        {"case": {"$eq": ["$severity", "critical"]}, "then": 4}
                    ]
                }}}
            }
        },
        {"$sort": {"_id.date": 1}}
    ]

    results = await Report.aggregate(pipeline).to_list()
    return {"trends": results}
```

---

## 9. MODULE 6: ADMINISTRATIVE CONTROL CENTER

### 9.1 User Management

```python
@router.get("/admin/users")
async def list_users(
    role: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50),
    skip: int = Query(0),
    current_user: User = Depends(require_admin_role)
):
    query = {}

    if role:
        query["role"] = role

    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"phone": {"$regex": search, "$options": "i"}}
        ]

    users = await User.find(query).skip(skip).limit(limit).to_list()
    total = await User.count_documents(query)

    return {"users": users, "total": total}

@router.patch("/admin/users/{user_id}/role")
async def change_user_role(
    user_id: str,
    new_role: str = Body(...),
    current_user: User = Depends(require_admin_role)
):
    if new_role not in ["citizen", "analyst", "admin"]:
        raise HTTPException(400, "Invalid role")

    user = await User.find_one({"user_id": user_id})
    user.role = new_role
    await user.save()

    # Log admin action
    await AuditLog.insert({
        "action": "role_change",
        "admin_id": current_user.id,
        "target_user_id": user_id,
        "old_role": user.role,
        "new_role": new_role,
        "timestamp": datetime.utcnow()
    })

    return {"success": True}
```

### 9.2 System Configuration

```python
@router.get("/admin/config")
async def get_config(current_user: User = Depends(require_admin_role)):
    return await SystemConfig.find_one({"_id": "global"})

@router.patch("/admin/config")
async def update_config(
    updates: dict = Body(...),
    current_user: User = Depends(require_admin_role)
):
    config = await SystemConfig.find_one({"_id": "global"})

    # Update fields
    for key, value in updates.items():
        if hasattr(config, key):
            setattr(config, key, value)

    await config.save()

    # Broadcast config change to all services (Redis pub/sub)
    await redis.publish("config.updated", json.dumps(updates))

    return {"success": True}
```

---

## 10. MODULE 7: HOTSPOT GENERATION ENGINE

### 10.1 Scoring Algorithm

```python
# app/services/hotspot/generator.py
import h3
from datetime import timedelta

class HotspotGenerator:
    @staticmethod
    async def generate_hotspots():
        # 1. Fetch data from last 6 hours
        cutoff_time = datetime.utcnow() - timedelta(hours=6)

        reports = await Report.find({
            "status": "verified",
            "reported_at": {"$gte": cutoff_time}
        }).to_list()

        social_posts = await es.search(
            index="social_posts",
            body={
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"classification.is_hazard_related": True}},
                            {"range": {"created_at": {"gte": cutoff_time.isoformat()}}}
                        ]
                    }
                }
            },
            size=1000
        )

        # 2. Convert locations to H3 hexagons (resolution 7 ≈ 5km²)
        hex_data = {}

        for report in reports:
            lon, lat = report.location['coordinates']
            hex_id = h3.geo_to_h3(lat, lon, 7)

            if hex_id not in hex_data:
                hex_data[hex_id] = {
                    "reports": [],
                    "social_posts": [],
                    "weather": None,
                    "official_alert": False
                }

            hex_data[hex_id]["reports"].append(report)

        for post in social_posts['hits']['hits']:
            source = post['_source']
            if source.get('location'):
                lon, lat = source['location']['coordinates']
                hex_id = h3.geo_to_h3(lat, lon, 7)

                if hex_id in hex_data:
                    hex_data[hex_id]["social_posts"].append(source)

        # 3. Calculate scores for each hexagon
        hotspots = []

        for hex_id, data in hex_data.items():
            score = await self.calculate_hex_score(hex_id, data)

            if score > 40:  # Minimum threshold
                hotspot = {
                    "hotspot_id": generate_id(),
                    "hex_id": hex_id,
                    "location": self.hex_to_geojson(hex_id),
                    "score": score,
                    "score_breakdown": self.get_score_breakdown(data, score),
                    "risk_level": self.classify_risk(score),
                    "contributing_reports": [r.report_id for r in data["reports"]],
                    "generated_at": datetime.utcnow(),
                    "expires_at": datetime.utcnow() + timedelta(hours=24)
                }

                hotspots.append(hotspot)

        # 4. Sort by score and keep top 50
        hotspots.sort(key=lambda x: x["score"], reverse=True)
        hotspots = hotspots[:50]

        # 5. Save to MongoDB
        await Hotspot.delete_many({})  # Clear old hotspots
        await Hotspot.insert_many(hotspots)

        # 6. Emit Kafka event
        await kafka_producer.send("hotspots.updated", {"count": len(hotspots)})

        # 7. Trigger alerts for critical hotspots
        critical_hotspots = [h for h in hotspots if h["risk_level"] == "critical"]
        for hotspot in critical_hotspots:
            await kafka_producer.send("alerts.hotspot_critical", hotspot)

        return hotspots

    @staticmethod
    async def calculate_hex_score(hex_id: str, data: dict) -> float:
        score = 0.0

        # Component 1: Report Density (40%)
        report_count = len(data["reports"])
        report_density_score = min(100, (report_count / 10) * 100)  # 10 reports = max
        score += 0.40 * report_density_score

        # Component 2: Average Credibility (25%)
        if data["reports"]:
            avg_credibility = sum(r.credibility_score for r in data["reports"]) / len(data["reports"])
            score += 0.25 * avg_credibility

        # Component 3: Social Media Volume × Urgency (20%)
        if data["social_posts"]:
            social_volume = len(data["social_posts"])
            high_urgency_count = sum(
                1 for p in data["social_posts"]
                if p['classification']['urgency'] == 'high'
            )
            urgency_factor = (high_urgency_count / social_volume) if social_volume > 0 else 0
            social_score = min(100, (social_volume / 50) * 100) * (1 + urgency_factor)
            score += 0.20 * social_score

        # Component 4: Weather Severity (10%)
        weather = await self.get_weather_for_hex(hex_id)
        if weather:
            weather_score = self.calculate_weather_severity(weather)
            score += 0.10 * weather_score

        # Component 5: Official Alert Flag (5%)
        incois_alerts = await self.check_incois_alerts(hex_id)
        if incois_alerts:
            score += 0.05 * 100

        return min(100, score)

    @staticmethod
    def classify_risk(score: float) -> str:
        if score >= 86:
            return "critical"
        elif score >= 71:
            return "high"
        elif score >= 41:
            return "medium"
        return "low"

    @staticmethod
    def hex_to_geojson(hex_id: str) -> dict:
        boundary = h3.h3_to_geo_boundary(hex_id, geo_json=True)
        return {
            "type": "Polygon",
            "coordinates": [boundary]
        }
```

### 10.2 Scheduled Execution

```python
# app/workers/hotspot_scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('cron', minute='*/15')  # Every 15 minutes
async def run_hotspot_generation():
    try:
        logger.info("Starting hotspot generation...")
        hotspots = await HotspotGenerator.generate_hotspots()
        logger.info(f"Generated {len(hotspots)} hotspots")

        # Update dashboard via WebSocket
        await broadcast_to_analysts({
            "type": "hotspots_updated",
            "count": len(hotspots)
        })

    except Exception as e:
        logger.error(f"Hotspot generation failed: {e}")
        # Alert admins via Slack/email
        await alert_admins("Hotspot generation error", str(e))

scheduler.start()
```

---

## 11. MODULE 8: ALERT DISTRIBUTION SYSTEM

### 11.1 Alert Creation & Targeting

```python
@router.post("/admin/alerts")
async def create_alert(
    alert_data: AlertCreate,
    current_user: User = Depends(require_admin_role)
):
    # 1. Validate alert data
    validate_alert(alert_data)

    # 2. Find users in target region (geospatial query)
    target_users = await User.find({
        "location": {
            "$geoWithin": {
                "$geometry": alert_data.region  # GeoJSON Polygon
            }
        },
        "notification_preferences.alerts_enabled": True
    }).to_list()

    # 3. Create alert document
    alert = Alert(
        alert_id=generate_id(),
        title=alert_data.title,
        message=alert_data.message,
        severity=alert_data.severity,
        region=alert_data.region,
        channels=alert_data.channels,  # ["push", "sms", "email"]
        target_user_count=len(target_users),
        created_by=current_user.id,
        status="pending",
        created_at=datetime.utcnow()
    )
    await alert.insert()

    # 4. Queue delivery jobs
    await kafka_producer.send("alerts.deliver", {
        "alert_id": alert.alert_id,
        "user_ids": [u.user_id for u in target_users],
        "channels": alert_data.channels
    })

    return {"alert_id": alert.alert_id, "target_users": len(target_users)}
```

### 11.2 Multi-Channel Delivery

```python
# app/workers/alert_delivery.py
from kafka import KafkaConsumer
from firebase_admin import messaging as fcm
from twilio.rest import Client as TwilioClient

consumer = KafkaConsumer('alerts.deliver')
twilio_client = TwilioClient(account_sid=TWILIO_SID, auth_token=TWILIO_TOKEN)

async def deliver_alerts():
    for message in consumer:
        payload = message.value
        alert = await Alert.find_one({"alert_id": payload["alert_id"]})

        # Batch users (500 per batch for FCM limits)
        user_batches = chunk_list(payload["user_ids"], 500)

        delivery_stats = {
            "push": {"sent": 0, "delivered": 0, "failed": 0},
            "sms": {"sent": 0, "delivered": 0, "failed": 0},
            "email": {"sent": 0, "delivered": 0, "failed": 0}
        }

        for batch in user_batches:
            users = await User.find({"user_id": {"$in": batch}}).to_list()

            # Push Notifications (Firebase FCM)
            if "push" in alert.channels:
                tokens = [u.fcm_token for u in users if u.fcm_token]

                fcm_message = fcm.MulticastMessage(
                    notification=fcm.Notification(
                        title=alert.title,
                        body=alert.message
                    ),
                    data={"alert_id": alert.alert_id, "severity": alert.severity},
                    tokens=tokens
                )

                response = fcm.send_multicast(fcm_message)
                delivery_stats["push"]["sent"] += len(tokens)
                delivery_stats["push"]["delivered"] += response.success_count
                delivery_stats["push"]["failed"] += response.failure_count

            # SMS (Twilio) - Only for critical alerts
            if "sms" in alert.channels and alert.severity == "critical":
                for user in users:
                    if user.phone:
                        try:
                            twilio_client.messages.create(
                                to=user.phone,
                                from_=TWILIO_PHONE,
                                body=f"{alert.title}\n{alert.message}"
                            )
                            delivery_stats["sms"]["sent"] += 1
                            delivery_stats["sms"]["delivered"] += 1
                        except Exception as e:
                            delivery_stats["sms"]["failed"] += 1
                            logger.error(f"SMS failed for {user.phone}: {e}")

            # Email (SendGrid) - Low priority
            if "email" in alert.channels:
                # Implement email delivery
                pass

        # Update alert with delivery stats
        alert.status = "sent"
        alert.delivery_status = delivery_stats
        alert.sent_at = datetime.utcnow()
        await alert.save()
```

---

## 12. DATA ARCHITECTURE & SCHEMA DESIGN

### 12.1 MongoDB Collections

**users**

```python
{
    "_id": ObjectId,
    "user_id": "USR-001",
    "phone": "hashed_phone",  # bcrypt
    "email": "user@example.com",
    "name": "John Doe",
    "role": "citizen",  # citizen | analyst | admin
    "location": {
        "type": "Point",
        "coordinates": [80.2707, 13.0827]  # [lon, lat]
    },
    "credibility_score": 75,
    "fcm_token": "...",
    "notification_preferences": {
        "alerts_enabled": true,
        "channels": ["push", "sms"]
    },
    "created_at": ISODate("2025-01-15T10:30:00Z")
}

# Indexes
db.users.createIndex({"user_id": 1}, {unique: true})
db.users.createIndex({"phone": 1}, {unique: true})
db.users.createIndex({"location": "2dsphere"})
db.users.createIndex({"role": 1})
```

**reports**

```python
{
    "_id": ObjectId,
    "report_id": "RPT-001",
    "user_id": "USR-001",
    "hazard_type": "tsunami",
    "severity": "high",
    "description": "Unusual water receding from shore",
    "location": {
        "type": "Point",
        "coordinates": [80.2707, 13.0827]
    },
    "media": [
        {"type": "image", "url": "s3://...", "thumbnail_url": "s3://..."},
        {"type": "video", "url": "s3://...", "duration": 15}
    ],
    "voice_note": {
        "url": "s3://...",
        "transcription": "समुद्र का पानी तेज़ी से पीछे जा रहा है",
        "language": "hi"
    },
    "weather": {
        "temperature": 28.5,
        "wind_speed": 25,
        "wave_height": 3.2
    },
    "status": "pending",  # pending | verified | rejected
    "credibility_score": 78,
    "verified_by": null,
    "verification_notes": null,
    "reported_at": ISODate("2025-11-18T14:20:00Z"),
    "verified_at": null
}

# Indexes
db.reports.createIndex({"report_id": 1}, {unique: true})
db.reports.createIndex({"location": "2dsphere"})
db.reports.createIndex({"status": 1, "reported_at": -1})
db.reports.createIndex({"user_id": 1})
db.reports.createIndex({"hazard_type": 1})
```

**hotspots**

```python
{
    "_id": ObjectId,
    "hotspot_id": "HOT-001",
    "hex_id": "872830820ffffff",  # H3 hexagon ID
    "location": {
        "type": "Polygon",
        "coordinates": [[...]]  # Hexagon boundary
    },
    "score": 85.4,
    "score_breakdown": {
        "report_density": 34.2,
        "avg_credibility": 21.3,
        "social_volume": 17.0,
        "weather_severity": 8.5,
        "official_alert": 5.0
    },
    "risk_level": "high",
    "contributing_reports": ["RPT-001", "RPT-002", "RPT-003"],
    "generated_at": ISODate("2025-11-18T15:00:00Z"),
    "expires_at": ISODate("2025-11-19T15:00:00Z")
}

# TTL Index (auto-delete after 24 hours)
db.hotspots.createIndex({"expires_at": 1}, {expireAfterSeconds: 0})
db.hotspots.createIndex({"location": "2dsphere"})
db.hotspots.createIndex({"score": -1})
```

### 12.2 Elasticsearch Index

**social_posts**

```json
{
  "post_id": "1234567890",
  "platform": "twitter",
  "content": "High waves hitting Marina Beach, Chennai. Stay safe!",
  "language": "en",
  "author": {
    "id": "user123",
    "username": "chennai_updates",
    "follower_count": 15000
  },
  "location": {
    "lat": 13.0497,
    "lon": 80.2826
  },
  "classification": {
    "is_hazard_related": true,
    "hazard_type": "high_waves",
    "confidence": 0.92,
    "urgency": "medium",
    "sentiment": "negative",
    "entities": {
      "locations": ["Marina Beach", "Chennai"],
      "keywords": ["high waves", "flooding", "danger"]
    },
    "misinformation_flags": {
      "is_flagged": false,
      "flags": []
    }
  },
  "engagement": {
    "likes": 234,
    "retweets": 89,
    "comments": 12
  },
  "created_at": "2025-11-18T14:30:00Z",
  "indexed_at": "2025-11-18T14:31:00Z"
}
```

---

## 13. API ARCHITECTURE & INTEGRATION LAYER

### 13.1 API Design Principles

- **RESTful** resource-based URLs
- **Versioned** endpoints (`/api/v1/`)
- **JWT Authentication** in `Authorization: Bearer <token>` header
- **Consistent Error Format**
- **Pagination** with cursor-based approach for large datasets

### 13.2 Core API Endpoints

**Authentication**

```
POST   /api/v1/auth/citizen/login        # Send OTP
POST   /api/v1/auth/citizen/verify       # Verify OTP, get tokens
POST   /api/v1/auth/staff/login          # Email/password login
POST   /api/v1/auth/refresh              # Refresh access token
POST   /api/v1/auth/logout               # Invalidate tokens
```

**Reports (Citizen)**

```
POST   /api/v1/reports                   # Submit new report
GET    /api/v1/reports                   # List reports (filtered)
GET    /api/v1/reports/{id}              # Get report details
GET    /api/v1/users/me/reports          # My reports
```

**Analyst Dashboard**

```
GET    /api/v1/analyst/verification/queue         # Pending reports
POST   /api/v1/analyst/verification/{id}/approve  # Approve report
POST   /api/v1/analyst/verification/{id}/reject   # Reject report
GET    /api/v1/analyst/analytics/trends           # Trend analysis
GET    /api/v1/analyst/social/posts               # Social media feed
POST   /api/v1/analyst/reports/generate           # Generate PDF report
```

**Admin Control**

```
GET    /api/v1/admin/users                # List all users
PATCH  /api/v1/admin/users/{id}/role      # Change user role
POST   /api/v1/admin/alerts               # Create new alert
GET    /api/v1/admin/monitoring/health    # System health
PUT    /api/v1/admin/config               # Update configuration
```

**Public/Shared**

```
GET    /api/v1/hotspots                   # Current hotspots
GET    /api/v1/weather/{lat}/{lon}        # Weather data
GET    /api/v1/stats                      # Public statistics
```

### 13.3 Error Response Format

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid hazard type",
    "details": {
      "field": "hazard_type",
      "allowed_values": [
        "tsunami",
        "storm_surge",
        "high_waves",
        "coastal_current",
        "swell_surge"
      ]
    },
    "timestamp": "2025-11-18T15:30:00Z",
    "request_id": "req_abc123xyz"
  }
}
```

### 13.4 External Integrations

**INCOIS Integration**

```python
# Outbound: Send verified reports
async def sync_to_incois():
    reports = await Report.find({
        "status": "verified",
        "synced_to_incois": False
    }).to_list()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://incois.gov.in/api/ground-truth",
            json=[r.dict() for r in reports],
            headers={"X-API-Key": INCOIS_API_KEY}
        )

    if response.status_code == 200:
        # Mark as synced
        await Report.update_many(
            {"report_id": {"$in": [r.report_id for r in reports]}},
            {"$set": {"synced_to_incois": True}}
        )

# Inbound: Receive official warnings
@app.post("/api/v1/incois/webhook")
async def receive_incois_alert(alert: dict, api_key: str = Header(...)):
    if api_key != INCOIS_WEBHOOK_SECRET:
        raise HTTPException(401, "Invalid API key")

    # Store official alert
    await OfficialAlert.insert(alert)

    # Trigger hotspot recalculation
    await kafka_producer.send("incois.alert_received", alert)

    return {"received": True}
```

**Weather API**

```python
# app/services/weather.py
class WeatherService:
    @staticmethod
    async def get_current(lat: float, lon: float) -> dict:
        # Check Redis cache first (30-min TTL)
        cache_key = f"weather:{lat:.2f}:{lon:.2f}"
        cached = await redis.get(cache_key)

        if cached:
            return json.loads(cached)

        # Primary: WeatherAPI.com
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.weatherapi.com/v1/current.json",
                    params={
                        "key": WEATHER_API_KEY,
                        "q": f"{lat},{lon}",
                        "aqi": "no"
                    },
                    timeout=5.0
                )
                data = response.json()

                weather = {
                    "temperature": data['current']['temp_c'],
                    "wind_speed": data['current']['wind_kph'],
                    "wave_height": data['current'].get('wave_m', 0),
                    "condition": data['current']['condition']['text']
                }

                # Cache for 30 minutes
                await redis.setex(cache_key, 1800, json.dumps(weather))

                return weather

        except Exception as e:
            logger.error(f"Weather API failed: {e}")
            # Fallback to cached stale data or default
            return {"temperature": None, "wind_speed": None, "wave_height": None}
```

---

## 14. SECURITY ARCHITECTURE

### 14.1 Authentication & Authorization

**JWT Token Structure**

```python
# Access Token (2-hour expiry)
{
  "sub": "USR-001",           # user_id
  "role": "citizen",
  "iat": 1700320000,          # issued at
  "exp": 1700327200,          # expires at
  "jti": "unique-token-id"
}

# Refresh Token (7-day expiry)
{
  "sub": "USR-001",
  "type": "refresh",
  "iat": 1700320000,
  "exp": 1700924800
}
```

**Security Middleware**

```python
from fastapi import Request, HTTPException
from jose import jwt, JWTError

async def verify_token(request: Request):
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid token")

    token = auth_header.split(" ")[1]

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        request.state.user_id = payload["sub"]
        request.state.role = payload["role"]
    except JWTError:
        raise HTTPException(401, "Invalid or expired token")

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    return response
```

### 14.2 Data Protection

- **Encryption at Rest**: MongoDB Atlas encryption (AES-256)
- **Encryption in Transit**: TLS 1.3 for all connections
- **Sensitive Data**: Phone numbers hashed with bcrypt
- **Media Files**: S3 server-side encryption

### 14.3 Input Validation

```python
from pydantic import BaseModel, Field, validator
from typing import List

class ReportCreate(BaseModel):
    hazard_type: str = Field(..., regex="^(tsunami|storm_surge|high_waves|coastal_current|swell_surge)$")
    severity: str = Field(..., regex="^(low|medium|high|critical)$")
    description: str = Field(..., min_length=10, max_length=1000)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)

    @validator('description')
    def sanitize_description(cls, v):
        # Remove potential XSS
        from bleach import clean
        return clean(v, tags=[], strip=True)
```

### 14.3 Rate Limiting

```python
from fastapi import Request
from fastapi.responses import JSONResponse

async def rate_limit_middleware(request: Request, call_next):
    user_id = request.state.get("user_id", request.client.host)
    endpoint = request.url.path

    # Check Redis counter
    key = f"ratelimit:{user_id}:{endpoint}"
    count = await redis.incr(key)

    if count == 1:
        await redis.expire(key, 3600)  # 1-hour window

    # Limits by role
    limits = {
        "citizen": 100,
        "analyst": 500,
        "admin": 1000
    }

    role = request.state.get("role", "citizen")
    limit = limits.get(role, 100)

    if count > limit:
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded"}
        )

    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(limit - count)

    return response
```

### 14.4 Security Checklist

- ✅ **HTTPS Only** (TLS 1.3)
- ✅ **JWT** with short expiry
- ✅ **RBAC** enforced at API gateway
- ✅ **Input Validation** (Pydantic schemas)
- ✅ **XSS Prevention** (Content Security Policy, sanitization)
- ✅ **CSRF Protection** (SameSite cookies)
- ✅ **SQL Injection N/A** (NoSQL database)
- ✅ **File Upload Validation** (type, size, malware scan with ClamAV)
- ✅ **Rate Limiting** (Redis-based)
- ✅ **Audit Logging** (all sensitive operations)
- ✅ **Secrets Management** (AWS Secrets Manager / HashiCorp Vault)

---

## 15. PERFORMANCE & SCALABILITY STRATEGY

### 15.1 Performance Targets

| Metric               | Target | Critical Threshold |
| -------------------- | ------ | ------------------ |
| Page Load Time (PWA) | <2s    | <4s                |
| API Response (p95)   | <500ms | <1s                |
| Offline Report Save  | <100ms | <500ms             |
| Background Sync Time | <10s   | <30s               |
| Hotspot Generation   | <2min  | <5min              |
| System Uptime        | >99.5% | >99%               |

### 15.2 Caching Strategy

**Multi-Layer Caching**

```
Level 1: Browser Cache (Service Worker) → 7-30 days
Level 2: CDN (Cloudflare) → 1 hour
Level 3: Redis (Application) → 5-60 minutes
Level 4: MongoDB Query Cache → Automatic
```

**Redis Caching Patterns**

```python
# Weather data (30-min TTL)
await redis.setex(f"weather:{lat}:{lon}", 1800, json.dumps(data))

# User session (2-hour TTL, matches JWT)
await redis.setex(f"session:{user_id}", 7200, json.dumps(user_data))

# API rate limits (1-hour window)
await redis.incr(f"ratelimit:{user_id}:{endpoint}")
await redis.expire(f"ratelimit:{user_id}:{endpoint}", 3600)
```

### 15.3 Database Optimization

**Indexing Strategy**

```python
# Compound index for verification queue (most common query)
db.reports.createIndex({"status": 1, "reported_at": -1})

# Geospatial index for proximity queries
db.reports.createIndex({"location": "2dsphere"})

# Partial index for pending reports only (reduces index size)
db.reports.createIndex(
    {"reported_at": -1},
    {partialFilterExpression: {"status": "pending"}}
)
```

**Connection Pooling**

```python
from motor.motor_asyncio import AsyncIOMotorClient

mongo_client = AsyncIOMotorClient(
    MONGODB_URI,
    maxPoolSize=50,          # Max connections
    minPoolSize=10,          # Keep-alive connections
    maxIdleTimeMS=45000,     # Close idle after 45s
    serverSelectionTimeoutMS=5000
)
```

### 15.4 Horizontal Scaling

**Kubernetes Auto-Scaling**

```yaml
# k8s/api-deployment.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: CoastGuardian-api
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: CoastGuardian-api
  minReplicas: 3
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

**Database Sharding**

```python
# MongoDB sharding key: hash(report_id)
sh.shardCollection("CoastGuardian.reports", {"report_id": "hashed"})

# Geospatial queries remain efficient with geo-near
```

### 15.5 Load Testing Results (Simulated)

**Normal Load** (100 concurrent users)

- Avg Response Time: 180ms
- Throughput: 500 req/s
- Error Rate: 0.1%

**Peak Load** (5000 concurrent users, cyclone event)

- Avg Response Time: 420ms
- Throughput: 2000 req/s
- Error Rate: 0.8%

**Stress Test** (10,000 concurrent users)

- System remains stable up to 8,000 users
- Degradation beyond 8,000 (response time >1s)
- No crashes, graceful degradation

---

## 16. DEPLOYMENT ARCHITECTURE

### 16.1 Infrastructure Overview

**Production Environment**

```
Frontend (Next.js PWA)
└─> Vercel (Global CDN + Edge Functions)

Backend (FastAPI)
└─> Kubernetes (AWS EKS / GCP GKE)
    ├─> API Pods (3-20 replicas, auto-scaling)
    ├─> Worker Pods (NLP, Hotspot, Alert)
    └─> Load Balancer (ALB / GCP Load Balancer)

Databases
├─> MongoDB Atlas (M30 cluster, 3-node replica set, sharded)
├─> Redis Cluster (3 nodes, AWS ElastiCache)
├─> Elasticsearch Cloud (8GB RAM, 2 nodes)
└─> Kafka (Confluent Cloud, 3 brokers)

Media Storage
└─> S3 / MinIO (with CloudFront CDN)

Monitoring
├─> Prometheus + Grafana (metrics)
├─> ELK Stack (logs)
└─> Sentry (error tracking)
```

### 16.2 CI/CD Pipeline

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: |
          pytest tests/ --cov --cov-report=xml

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Build Docker image
        run: |
          docker build -t CoastGuardian-api:${{ github.sha }} .

      - name: Security scan
        run: |
          docker scan CoastGuardian-api:${{ github.sha }}

      - name: Push to registry
        run: |
          docker push gcr.io/CoastGuardian/api:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Kubernetes
        run: |
          kubectl set image deployment/CoastGuardian-api \
            api=gcr.io/CoastGuardian/api:${{ github.sha }}
          kubectl rollout status deployment/CoastGuardian-api

      - name: Run smoke tests
        run: |
          curl -f https://api.CoastGuardian.in/health || exit 1
```

### 16.3 Disaster Recovery

**Backup Strategy**

- **MongoDB**: Full backup daily (2 AM IST) → S3, retained 30 days
- **MongoDB**: Incremental every 6 hours → retained 7 days
- **Redis**: Snapshots hourly → retained 24 hours
- **Media Files**: S3 versioning enabled (continuous)

**Recovery Metrics**

- **RTO** (Recovery Time Objective): 4 hours
- **RPO** (Recovery Point Objective): 6 hours (max data loss)

**Multi-Region Setup**

- **Primary**: Mumbai (ap-south-1)
- **Secondary**: Chennai (DR site, manual failover)

---

## 17. MONITORING & OBSERVABILITY

### 17.1 Metrics (Prometheus + Grafana)

**System Metrics**

- CPU, Memory, Disk, Network per service
- Pod count, restarts, health status

**Application Metrics**

```python
from prometheus_client import Counter, Histogram, Gauge

# Custom metrics
reports_submitted = Counter('reports_submitted_total', 'Total reports submitted', ['hazard_type'])
reports_verified = Counter('reports_verified_total', 'Total reports verified')
api_latency = Histogram('api_request_duration_seconds', 'API latency', ['endpoint'])
active_users = Gauge('active_users_count', 'Current active users')
hotspot_count = Gauge('hotspots_active_count', 'Current active hotspots')
```

**Dashboard Panels**

- API response time (p50, p95, p99)
- Request rate (req/s)
- Error rate (%)
- Database query time
- Cache hit ratio
- Background sync success rate

### 17.2 Logging (ELK Stack)

**Log Structure**

```json
{
  "timestamp": "2025-11-18T15:30:00Z",
  "level": "INFO",
  "service": "api",
  "endpoint": "/api/v1/reports",
  "method": "POST",
  "user_id": "USR-001",
  "duration_ms": 240,
  "status_code": 201,
  "request_id": "req_abc123"
}
```

**Log Aggregation**

- All services → Filebeat → Logstash → Elasticsearch → Kibana
- Retention: 30 days
- Searchable by service, user, endpoint, error type

### 17.3 Alerting (Prometheus AlertManager)

**Alert Rules**

```yaml
groups:
  - name: CoastGuardian_alerts
    rules:
      - alert: HighAPILatency
        expr: histogram_quantile(0.95, api_request_duration_seconds) > 1
        for: 10m
        annotations:
          summary: "API latency above 1s (p95)"
        labels:
          severity: warning

      - alert: HighErrorRate
        expr: rate(api_errors_total[5m]) > 0.05
        for: 5m
        annotations:
          summary: "Error rate above 5%"
        labels:
          severity: critical

      - alert: PodCrashLooping
        expr: rate(kube_pod_container_status_restarts_total[10m]) > 0.5
        annotations:
          summary: "Pod restarting frequently"
        labels:
          severity: critical
```

**Notification Channels**

- **Warning**: Slack #CoastGuardian-alerts
- **Critical**: PagerDuty (on-call engineer) + Slack

---

## 18. RISK ASSESSMENT & MITIGATION

### 18.1 Technical Risks

| Risk                          | Impact | Probability | Mitigation                                                                             |
| ----------------------------- | ------ | ----------- | -------------------------------------------------------------------------------------- |
| **Service Worker bugs**       | High   | Medium      | Extensive testing, fallback to online mode, phased rollout                             |
| **API rate limits (Twitter)** | Medium | High        | Caching, queue management, multiple API keys, fallback to scraping                     |
| **Database overload**         | High   | Low         | Sharding, read replicas, query optimization, connection pooling                        |
| **Third-party API downtime**  | Medium | Medium      | Fallback providers (Weather: WeatherAPI → OpenWeather → IMD), stale data with warnings |
| **NLP model accuracy**        | Medium | Medium      | Confidence thresholds, human verification loop, continuous retraining                  |

### 18.2 Operational Risks

| Risk                      | Impact | Probability | Mitigation                                                                                          |
| ------------------------- | ------ | ----------- | --------------------------------------------------------------------------------------------------- |
| **Low user adoption**     | High   | Medium      | Gamification (badges, leaderboards), community engagement, training workshops, govt partnerships    |
| **Misinformation spam**   | High   | Medium      | NLP filtering, credibility scoring, manual review queue, rate limiting                              |
| **Data privacy concerns** | High   | Low         | Anonymization (aggregate reports), GDPR compliance, clear privacy policy, optional location sharing |
| **Infrastructure costs**  | Medium | Medium      | Cost monitoring, auto-scaling limits, reserved instances, serverless for bursty workloads           |

### 18.3 Security Risks

| Risk                 | Impact   | Probability | Mitigation                                                                         |
| -------------------- | -------- | ----------- | ---------------------------------------------------------------------------------- |
| **DDoS attacks**     | High     | Low         | Cloudflare protection, rate limiting, IP blocking, CDN caching                     |
| **Data breaches**    | Critical | Low         | Encryption (rest + transit), access controls, security audits, penetration testing |
| **Account takeover** | High     | Medium      | 2FA for admins, OTP for citizens, session monitoring, CAPTCHA on sensitive actions |
| **API abuse**        | Medium   | Medium      | Rate limiting, API key rotation, usage monitoring, webhook verification            |

---

## 19. TESTING STRATEGY

### 19.1 Testing Pyramid

```
        E2E Tests (5%)
         /        \
    Integration (20%)
        /            \
   Unit Tests (75%)
```

### 19.2 Test Coverage

**Unit Tests** (pytest, target 80% coverage)

```python
# tests/test_credibility.py
def test_credibility_calculation():
    user = User(id="USR-001", credibility_score=50)
    report = Report(has_media=True, description="..." * 50)

    score = CredibilityService.calculate(user, report)

    assert score > 50  # Media and description bonuses
    assert score <= 100

def test_hotspot_scoring():
    data = {
        "reports": [Report(...), Report(...)],
        "social_posts": [...]
    }

    score = HotspotGenerator.calculate_hex_score("hex_id", data)

    assert 0 <= score <= 100
    assert score > 40  # Above threshold
```

**Integration Tests** (FastAPI TestClient)

```python
# tests/test_api.py
from fastapi.testclient import TestClient

client = TestClient(app)

def test_create_report():
    # Login first
    auth_response = client.post("/api/v1/auth/citizen/login", json={"phone": "+919876543210"})
    token = auth_response.json()["access_token"]

    # Submit report
    response = client.post(
        "/api/v1/reports",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "hazard_type": "tsunami",
            "severity": "high",
            "description": "Water receding rapidly",
            "latitude": 13.0827,
            "longitude": 80.2707
        }
    )

    assert response.status_code == 201
    assert "report_id" in response.json()
```

**E2E Tests** (Playwright)

```python
# tests/e2e/test_report_flow.py
def test_offline_report_submission(page):
    # 1. Login
    page.goto("https://CoastGuardian.in/login")
    page.fill("#phone", "+919876543210")
    page.click("button[type='submit']")
    page.fill("#otp", "123456")
    page.click("button[type='submit']")

    # 2. Go offline
    page.context.set_offline(True)

    # 3. Submit report
    page.goto("/reports/new")
    page.select_option("#hazard_type", "tsunami")
    page.select_option("#severity", "high")
    page.fill("#description", "Unusual sea behavior observed")
    page.click("button[type='submit']")

    # 4. Verify queued status
    expect(page.locator(".sync-status")).to_contain_text("Queued for sync")

    # 5. Go online
    page.context.set_offline(False)

    # 6. Wait for sync
    expect(page.locator(".sync-status")).to_contain_text("Synced", timeout=15000)
```

### 19.3 Performance Testing (Locust)

```python
# tests/load/locustfile.py
from locust import HttpUser, task, between

class CitizenUser(HttpUser):
    wait_time = between(1, 5)

    def on_start(self):
        # Login
        response = self.client.post("/api/v1/auth/citizen/login", json={"phone": "+919876543210"})
        self.token = response.json()["access_token"]

    @task(3)
    def view_reports(self):
        self.client.get(
            "/api/v1/reports",
            headers={"Authorization": f"Bearer {self.token}"}
        )

    @task(1)
    def submit_report(self):
        self.client.post(
            "/api/v1/reports",
            headers={"Authorization": f"Bearer {self.token}"},
            json={
                "hazard_type": "high_waves",
                "severity": "medium",
                "description": "Moderate waves observed",
                "latitude": 13.0 + random.random(),
                "longitude": 80.0 + random.random()
            }
        )

# Run with: locust -f locustfile.py --users 5000 --spawn-rate 100
```

---

## 20. IMPLEMENTATION ROADMAP

### Phase 1: Foundation (Months 1-2)

**Month 1: Core Setup**

- Week 1-2:
  - Project initialization (Next.js + FastAPI)
  - Database setup (MongoDB Atlas, Redis)
  - Docker Compose for local dev
  - Authentication module (JWT, OTP)
- Week 3-4:
  - User management module
  - Citizen reporting module (basic form)
  - API endpoints for reports
  - Frontend components (report form, map)

**Month 2: Offline Capabilities**

- Week 1-2:
  - Service Worker implementation
  - IndexedDB wrapper
  - Background sync logic
  - Network status detection
- Week 3-4:
  - Media upload and compression
  - Voice recording integration
  - GPS location capture
  - Testing offline functionality

**Deliverable**: Working PWA with offline report submission

---

### Phase 2: Intelligence Layer (Months 3-4)

**Month 3: Social Media Analytics**

- Week 1-2:
  - Kafka setup
  - Twitter API integration
  - Social media crawler service
  - Raw post ingestion
- Week 3-4:
  - NLP pipeline setup (IndicBERT)
  - Classification logic
  - Elasticsearch integration
  - Testing classification accuracy

**Month 4: Analyst Dashboard**

- Week 1-2:
  - Analyst dashboard layout
  - Verification queue component
  - Correlation view
  - Bulk operations
- Week 3-4:
  - Analytics charts (trends, heatmaps)
  - Social feed for analysts
  - Report generation and export
  - Testing verification workflow

**Deliverable**: Analyst dashboard with verification and analytics

---

### Phase 3: Admin & Integration (Months 5-6)

**Month 5: Admin Panel & Hotspot Engine**

- Week 1-2:
  - Admin dashboard layout
  - User management interface
  - Hotspot scoring algorithm
  - H3 grid integration
- Week 3-4:
  - Alert management interface
  - System monitoring dashboard
  - Feature flag system
  - Hotspot visualization on map

**Month 6: Integration & Polish**

- Week 1-2:
  - INCOIS API integration
  - Weather API integration
  - FCM/SMS gateway setup
  - Speech-to-text integration
- Week 3-4:
  - Kubernetes deployment setup
  - CI/CD pipeline configuration
  - Performance optimization
  - Security hardening
  - Documentation

**Deliverable**: Complete production-ready system

---

### Post-Launch: Maintenance & Enhancement (Months 7-12)

**Months 7-8: Stabilization**

- Bug fixes from user feedback
- Performance tuning
- Load testing with real traffic
- User training and documentation

**Months 9-12: Enhancements**

- AI image analysis (detect hazards from photos)
- Predictive hotspot modeling
- Satellite imagery integration
- Native mobile app (Flutter)
- Expansion to other disasters (floods, earthquakes)

---

## CONCLUSION & KEY SUCCESS FACTORS

### Critical Success Factors

1. **Offline-First Architecture**: Must work flawlessly without internet in coastal areas
2. **User Trust**: Credibility scoring + analyst verification builds confidence
3. **Multi-Source Intelligence**: Combining citizen reports + social media + weather + official alerts
4. **Response Time**: Real-time processing and hotspot generation enables faster disaster response
5. **Scalability**: Auto-scaling infrastructure handles sudden traffic spikes during cyclones

### Innovation Highlights

- **Offline PWA**: Full functionality without internet (Service Workers + IndexedDB)
- **Multilingual NLP**: IndicBERT for Indian languages (Hindi, Tamil, Telugu, Bengali)
- **H3 Hexagonal Grid**: Efficient geospatial hotspot calculation
- **Event-Driven Architecture**: Kafka for real-time data pipelines
- **Credibility Scoring**: Combats misinformation through user reputation

### Expected Impact

- **40% faster** disaster response through real-time ground truth
- **50% reduction** in false positives via crowdsourced validation
- **100% coverage** of India's 7,517 km coastline
- **Measurable lives saved** through timely evacuations

### Technical Readiness

✅ **Modern Stack**: FastAPI + Next.js + MongoDB  
✅ **Production-Grade**: Kubernetes + CI/CD + Monitoring  
✅ **Extensible**: Modular microservices architecture  
✅ **Tested**: 80% code coverage, E2E tests, load tests  
✅ **Secure**: Encryption, RBAC, rate limiting, audit logs  
✅ **Documented**: API docs (OpenAPI), architecture diagrams, runbooks

---

**Document Version**: 2.0 (Updated Tech Stack)  
**Date**: November 2025  
**Team**: CoastGuardians  
**Problem Statement**: SIH25039 (INCOIS)  
**Total Pages**: 10 (condensed from 40-page detailed doc)

---

## APPENDIX: Technology Comparison Matrix

| Aspect             | Original (NestJS)          | Updated (FastAPI)            | Rationale for Change                                        |
| ------------------ | -------------------------- | ---------------------------- | ----------------------------------------------------------- |
| **Language**       | TypeScript                 | Python                       | Better ML/NLP library ecosystem (HuggingFace, scikit-learn) |
| **Async Support**  | Yes (async/await)          | Yes (async/await)            | Equivalent                                                  |
| **Performance**    | High                       | High                         | Similar (both async, non-blocking I/O)                      |
| **API Docs**       | Swagger (manual)           | OpenAPI (auto-generated)     | FastAPI auto-generates from type hints                      |
| **Type Safety**    | Strong (TypeScript)        | Strong (Pydantic)            | Pydantic provides runtime validation                        |
| **ML Integration** | Requires external services | Native (import transformers) | Direct model inference in API                               |
| **Learning Curve** | Medium                     | Low                          | Python more accessible for data scientists                  |
| **Ecosystem**      | Large (npm)                | Very Large (PyPI)            | More ML/data tools in Python                                |

**Conclusion**: FastAPI chosen for superior ML/NLP integration, automatic API documentation, and team familiarity with Python data science stack.

---


**END OF DOCUMENT**
