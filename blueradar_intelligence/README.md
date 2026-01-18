# BlueRadar Intelligence Engine v2.0

**Real-Time Ocean Hazard Monitoring System for Indian Coastal Waters**

Built for SIH 2025 | INCOIS | Optimized for MacBook Air M2

---

## Overview

BlueRadar Intelligence is a production-grade social media monitoring system that scrapes, analyzes, and alerts on ocean hazards affecting Indian coastal regions. The system provides real-time monitoring through a WebSocket-based dashboard with live alerts.

### Key Features

| Feature                 | Description                                                   |
| ----------------------- | ------------------------------------------------------------- |
| **Real-Time Dashboard** | Live WebSocket-based alert streaming with interactive UI      |
| **4 Platform Support**  | Twitter, YouTube, Google News, Instagram (via RapidAPI)       |
| **Smart NLP Pipeline**  | Hazard classification, location extraction, severity scoring  |
| **India-Focused**       | Geographic filtering for Indian coastal regions only          |
| **Content Validation**  | Recency checks (48hr), duplicate detection, relevance scoring |
| **Multi-Language**      | English, Hindi, Tamil, Telugu support                         |

---

## Quick Start

### 1. Setup

```bash
# Clone and navigate to project
cd blueradar_intelligence

# Run setup
./run.sh -m setup

# Edit .env with your API keys
nano .env
```

### 2. Configure API Keys

Edit `.env` file:

```env
# RapidAPI Keys (get from rapidapi.com)
RAPIDAPI_KEY=your_twitter_api_key
RAPIDAPI_INSTAGRAM_KEY=your_instagram_api_key
```

### 3. Start Monitoring

```bash
# Start real-time monitoring (opens dashboard automatically)
./run.sh

# Or with custom options
./run.sh --interval 120 --platforms twitter youtube news
```

---

## Run Script Usage

```bash
./run.sh [OPTIONS]

Options:
  -m, --mode MODE       Run mode: realtime, demo, setup, stop, status
  -p, --port PORT       WebSocket port (default: 8765)
  -h, --http PORT       HTTP dashboard port (default: 8080)
  -i, --interval SEC    Scrape interval in seconds (default: 60)
  --platforms LIST      Platforms: twitter youtube news instagram
  --no-browser          Don't open browser automatically
  --help                Show help message

Examples:
  ./run.sh                              # Start real-time monitoring
  ./run.sh -m demo                      # Run demo mode
  ./run.sh -i 120 --no-browser          # 2-minute interval, no browser
  ./run.sh --platforms twitter news     # Only Twitter and News
  ./run.sh -m stop                      # Stop all processes
  ./run.sh -m status                    # Check running status
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        BLUERADAR ARCHITECTURE                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │  Twitter    │  │  YouTube    │  │   News      │  │  Instagram  │   │
│  │  RapidAPI   │  │  RSS/API    │  │  Google RSS │  │  RapidAPI   │   │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘   │
│         │                │                │                │           │
│         └────────────────┴────────────────┴────────────────┘           │
│                                  │                                      │
│                    ┌─────────────▼─────────────┐                       │
│                    │   PARALLEL SCRAPER MGR    │                       │
│                    │   (Async + ThreadPool)    │                       │
│                    └─────────────┬─────────────┘                       │
│                                  │                                      │
│                    ┌─────────────▼─────────────┐                       │
│                    │   CONTENT VALIDATOR       │                       │
│                    │   • Recency (48hr max)    │                       │
│                    │   • Geography (India)     │                       │
│                    │   • Duplicate Detection   │                       │
│                    └─────────────┬─────────────┘                       │
│                                  │                                      │
│                    ┌─────────────▼─────────────┐                       │
│                    │   FAST NLP PROCESSOR      │                       │
│                    │   • Hazard Classification │                       │
│                    │   • Location Extraction   │                       │
│                    │   • Severity Scoring      │                       │
│                    └─────────────┬─────────────┘                       │
│                                  │                                      │
│                    ┌─────────────▼─────────────┐                       │
│                    │   WEBSOCKET SERVER        │                       │
│                    │   ws://localhost:8765     │                       │
│                    └─────────────┬─────────────┘                       │
│                                  │                                      │
│                    ┌─────────────▼─────────────┐                       │
│                    │   LIVE DASHBOARD          │                       │
│                    │   http://localhost:8080   │                       │
│                    └───────────────────────────┘                       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
blueradar_intelligence/
├── run.sh                    # Main run script
├── run_realtime.py           # Real-time engine launcher
├── main.py                   # Batch processing orchestrator
├── requirements.txt          # Python dependencies
├── .env                      # API keys (not in git)
│
├── services/                 # Core microservices
│   ├── fast_scraper.py       # Parallel scraper manager
│   ├── fast_nlp.py           # NLP processing pipeline
│   └── content_validator.py  # Validation filters
│
├── realtime/                 # Real-time engine
│   ├── engine.py             # Main orchestrator
│   └── websocket_server.py   # WebSocket + Alert system
│
├── dashboard/                # Web dashboard
│   └── index.html            # Single-page dashboard UI
│
├── scrapers/                 # Legacy scrapers
│   ├── session_manager.py    # Cookie management
│   └── anti_detection.py     # Bot detection bypass
│
├── nlp/                      # NLP models
│   └── pipeline.py           # Transformer pipeline
│
├── config/                   # Configuration
│   ├── settings.py           # System settings
│   └── cookies.json          # Session cookies
│
└── data/                     # Output data
    ├── output/               # Scan results
    ├── logs/                 # Execution logs
    └── reports/              # Generated reports
```

---

## Data Sources

### Twitter (via RapidAPI Twitter241)

- **Endpoint**: `twitter241.p.rapidapi.com/search`
- **Method**: Single batch request with comprehensive query
- **Rate Limit**: 500 requests/month (free tier)
- **Features**: Real-time tweets, location filtering, engagement metrics

### YouTube (RSS Feeds)

- **Endpoint**: Google News RSS for YouTube
- **Method**: Keyword-based search
- **Rate Limit**: None (RSS)
- **Features**: Video metadata, descriptions, thumbnails

### Google News (RSS)

- **Endpoint**: `news.google.com/rss/search`
- **Method**: Keyword search with region filtering
- **Rate Limit**: None (RSS)
- **Features**: News articles, publication dates, sources

### Instagram (via RapidAPI Instagram-Data1)

- **Endpoint**: `instagram-data1.p.rapidapi.com/hashtag/feed`
- **Method**: Hashtag-based search
- **Rate Limit**: Limited on free tier
- **Features**: Posts, images, captions, engagement

---

## NLP Pipeline

The Fast NLP Processor analyzes each post through:

1. **Hazard Detection** - Identifies ocean hazards (cyclone, flood, tsunami, storm surge, etc.)
2. **Location Extraction** - Extracts Indian coastal locations using NER + keyword matching
3. **Severity Classification** - CRITICAL / HIGH / MEDIUM / LOW based on:
   - Hazard type
   - Urgency indicators
   - Official source mentions
   - Warning keywords
4. **Relevance Scoring** - 0-100 score based on:
   - Hazard relevance
   - Location specificity
   - Source credibility
   - Recency

---

## Content Validation

Posts are filtered through a validation pipeline:

| Filter         | Criteria                                        |
| -------------- | ----------------------------------------------- |
| **Recency**    | Posts must be < 48 hours old                    |
| **Geography**  | Must reference Indian locations or water bodies |
| **Duplicates** | Similar content within 24hr window is rejected  |
| **Relevance**  | Must pass NLP relevance threshold               |

### India Geographic Filter

**Included Regions:**

- Bay of Bengal, Arabian Sea, Indian Ocean
- East Coast: Chennai, Vizag, Puri, Kolkata
- West Coast: Mumbai, Goa, Mangalore, Kochi
- Islands: Andaman, Nicobar, Lakshadweep

**Blocked International:**

- Philippines, Taiwan, Japan, Vietnam
- Bangladesh, Myanmar, Thailand
- Caribbean, Pacific, Atlantic

---

## Dashboard Features

The real-time dashboard at `http://localhost:8080` provides:

- **Live Alert Feed** - Streaming alerts via WebSocket
- **Severity Indicators** - Color-coded CRITICAL/HIGH/MEDIUM/LOW
- **Platform Filters** - Filter by Twitter/YouTube/News/Instagram
- **Region Filters** - East Coast/West Coast/Islands
- **Time Filters** - Last 1hr/6hr/24hr/48hr
- **Statistics Panel** - Total alerts, severity breakdown, hazard types
- **Click-to-Source** - Direct links to original posts

---

## Alert Format

```json
{
  "id": "abc123def456",
  "type": "cyclone",
  "severity": "CRITICAL",
  "title": "CRITICAL: Cyclone detected near Chennai",
  "description": "IMD issues red alert for Chennai coast...",
  "location": "chennai",
  "region": "east_coast",
  "platform": "twitter",
  "source_url": "https://twitter.com/...",
  "relevance_score": 92,
  "timestamp": "2024-12-02T16:30:00"
}
```

---

## Hazard Keywords

The system monitors for these hazard types:

| Category        | Keywords                                                   |
| --------------- | ---------------------------------------------------------- |
| **Cyclone**     | cyclone, CycloneAlert, hurricane, typhoon, IMDAlert        |
| **Flood**       | flood, flooding, MumbaiFloods, ChennaiFloods, KeralaFloods |
| **Tsunami**     | tsunami, TsunamiWarning, tidal wave, INCOIS                |
| **Storm Surge** | storm surge, coastal flooding, high tide                   |
| **Rough Sea**   | HighWaves, RoughSea, RipCurrent, dangerous seas            |

---

## API Configuration

### RapidAPI Setup

1. Create account at [rapidapi.com](https://rapidapi.com)
2. Subscribe to:
   - **Twitter241** - For Twitter data
   - **Instagram-Data1** - For Instagram data
3. Copy API keys to `.env` file

### Rate Limits

| API             | Free Tier | Recommendation        |
| --------------- | --------- | --------------------- |
| Twitter241      | 500/month | Use 60-120s intervals |
| Instagram-Data1 | Limited   | Use sparingly         |
| YouTube RSS     | Unlimited | Default source        |
| News RSS        | Unlimited | Default source        |

---

## Troubleshooting

| Issue                  | Solution                                      |
| ---------------------- | --------------------------------------------- |
| No alerts showing      | Check WebSocket connection in browser console |
| Instagram rate limited | Wait for limit reset or upgrade API plan      |
| Twitter not working    | Verify RAPIDAPI_KEY in .env                   |
| Dashboard not loading  | Check if port 8080 is available               |
| WebSocket disconnected | Refresh browser, check port 8765              |

### Check Status

```bash
./run.sh -m status
```

### View Logs

```bash
# Check running output
./run.sh -m status

# Stop all processes
./run.sh -m stop
```

---

## Performance

| Metric          | Value          |
| --------------- | -------------- |
| Scrape Cycle    | 60-120 seconds |
| Posts per Cycle | 400-500        |
| NLP Processing  | ~50ms/post     |
| Alert Latency   | < 1 second     |
| Memory Usage    | ~500MB         |

---

## Security Notes

- Never commit `.env` file to git
- API keys are stored locally only
- No user credentials required
- All data sources are public APIs/RSS

---

## License

Built for SIH 2025 | INCOIS Ocean Hazard Reporting Platform

---

## Support

For issues or questions:

1. Check troubleshooting section above
2. Run `./run.sh -m status` for diagnostics
3. Check browser console for WebSocket errors
