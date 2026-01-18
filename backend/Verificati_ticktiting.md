# 🚀 Step-by-Step Implementation Prompts for Claude Code Opus

Here are detailed, sequential prompts to implement the 6-layer verification system.  Use these one at a time:

---

## **Prompt 1: Enhanced Database Schema**

```
I need to enhance the HazardReport model in my CoastGuardians project to support a 6-layer verification system. 

CURRENT LOCATION: backend/app/models/hazard. py

REQUIREMENTS:
1. Add a new VerificationLayer Pydantic model with these fields:
   - layer_name: str
   - status: str (values: "passed", "failed", "warning", "skipped")
   - score: float (0. 0 to 1.0)
   - confidence: float
   - reason: str
   - timestamp: datetime
   - metadata: Optional[Dict[str, Any]]

2.  Extend the existing HazardReport model with these NEW fields:
   
   # Verification tracking
   - verification_layers: Dict[str, VerificationLayer] (default empty dict)
   
   # Layer 1: Geofencing
   - geofence_status: Optional[str] ("inside_zone" or "outside_zone")
   - distance_from_coastline_km: Optional[float]
   - nearest_coastal_point: Optional[str]
   
   # Layer 2: Weather validation (natural hazards only)
   - weather_criticality: Optional[str] ("Warning", "Alert", "Watch", "No Threat")
   - weather_validation_result: Optional[bool]
   - weather_validation_reason: Optional[str]
   - weather_score: Optional[float]
   - applies_weather_validation: bool (default False)
   
   # Layer 3: Text analysis
   - text_analysis_score: Optional[float]
   - vector_similarity_score: Optional[float]
   - vector_predicted_type: Optional[str]
   - vector_confidence: Optional[float]
   - text_anomaly_flags: Optional[List[str]]
   - panic_level: Optional[float]
   - is_spam: Optional[bool]
   
   # Layer 4: Image classification
   - image_classification: Optional[str]
   - image_confidence: Optional[float]
   - image_matches_report: Optional[bool]
   - applies_image_validation: bool (default False)
   
   # Layer 5: Reporter score
   - reporter_accuracy_score: Optional[float]
   
   # Layer 6: Composite score
   - composite_verification_score: float (default 0.0, range 0-100)
   - auto_approval_eligible: bool (default False)
   
   # Workflow
   - workflow_status: str (default "pending_verification")
     Valid values: "pending_verification", "verified", "needs_manual_review", "rejected", "auto_rejected"
   - manual_review_required: bool (default False)
   - manual_review_reason: Optional[str]
   - auto_rejection_reason: Optional[str]

3. Keep ALL existing fields in the HazardReport model unchanged

4. Add appropriate Field() descriptions for documentation

5. Ensure proper imports from typing, datetime, and pydantic

Please show me the complete updated hazard.py file with proper Python formatting. 
```

---

## **Prompt 2: Layer 1 - Geofencing Validator**

```
Create a geofencing validation service for the CoastGuardians project that AUTO-REJECTS reports outside valid coastal zones.

CREATE NEW FILE: backend/app/services/geofence_validator.py

REQUIREMENTS:

1. Create a GeofenceValidator class with these components:

2.  COASTLINE_POINTS constant - list of dicts with 100+ Indian coastal locations:
   - Include: Mumbai, Chennai, Kolkata, Visakhapatnam, Kochi, Port Blair, Puducherry, Goa, Mangalore, Thiruvananthapuram, Rameswaram, Kandla, Paradip, Haldia
   - Each entry: {"name": str, "lat": float, "lon": float}
   - Add more coastal cities from Gujarat, Maharashtra, Karnataka, Kerala, Tamil Nadu, Andhra Pradesh, Odisha, West Bengal coasts

3. Constants:
   - INLAND_LIMIT_KM = 20 (max distance inland)
   - OFFSHORE_LIMIT_KM = 30 (max distance offshore)

4. Methods to implement:

   @staticmethod
   def find_nearest_coastline(lat: float, lon: float) -> Tuple[float, Dict]:
   - Calculate geodesic distance to all coastline points
   - Return (min_distance, nearest_point_dict)
   - Use geopy. distance.geodesic

   @staticmethod
   def is_on_land(lat: float, lon: float) -> bool:
   - Use geopy.geocoders. Nominatim for reverse geocoding
   - Check if location contains water keywords: 'ocean', 'sea', 'bay', 'arabian sea', 'bay of bengal', 'indian ocean'
   - Return True if on land, False if in water
   - Handle API errors gracefully (default to True)

   @staticmethod
   def validate(lat: float, lon: float) -> Dict[str, Any]:
   - Main validation method
   - Call find_nearest_coastline() and is_on_land()
   - Logic:
     * If on land AND distance > INLAND_LIMIT_KM: AUTO-REJECT (auto_reject=True)
     * If in water AND distance > OFFSHORE_LIMIT_KM: AUTO-REJECT (auto_reject=True)
     * Otherwise: PASS (auto_reject=False)
   
   - Return dict with:
     {
       "status": "passed" or "failed",
       "score": 1.0 (passed) or 0.0 (failed),
       "distance_km": float (rounded to 2 decimals),
       "is_inland": bool,
       "nearest_coast": str,
       "reason": str (descriptive message with ❌ AUTO-REJECT prefix if rejected),
       "auto_reject": bool
     }

5. Add proper type hints, docstrings, and error handling

6. Required imports: math, typing, geopy. distance, geopy.geocoders

Please provide the complete geofence_validator.py file. 
```

---

## **Prompt 3: Layer 2 - Weather Validator**

```
Create a weather validation service for natural hazards using real-time environmental data. 

CREATE NEW FILE: backend/app/services/weather_validator.py

REQUIREMENTS:

1. Create a WeatherValidator class

2. Constants:

   NATURAL_HAZARDS = ["tsunami", "cyclone", "high_waves", "flooded_coastline", "rip_current"]

   HAZARD_RULES = Dict with validation rules for each hazard:
   
   For "tsunami":
   - "warning": magnitude >= 8 AND depth <= 50km
   - "alert": 7 <= magnitude < 8 AND depth <= 70km
   - "watch": 6 <= magnitude < 7
   - "threat_boost": tide_height > 1.5m
   
   For "cyclone":
   - "warning": wind >= 90 kph OR gust >= 110 kph OR pressure < 985 mb OR (precip >= 30mm AND visibility <= 2km)
   - "alert": 70 <= wind < 90 kph OR 985 <= pressure < 995 mb OR 20 <= precip < 30mm OR 2 < visibility <= 5km
   - "watch": 50 <= wind < 70 kph OR 995 <= pressure < 1005 mb OR 10 <= precip < 20mm
   
   For "high_waves":
   - "warning": sig_height > 4m OR swell_height > 3m OR swell_period > 18s OR (tide_height > 2m AND tide_type == "HIGH")
   - "alert": 3 <= sig_height <= 4m OR 2 <= swell_height <= 3m OR 15 <= swell_period <= 18s OR 1. 5 <= tide_height <= 2m
   - "watch": 2 <= sig_height <= 3m OR 1.5 <= swell_height <= 2m OR 12 <= swell_period <= 15s
   
   For "flooded_coastline":
   - "warning": (tide_height > 2m AND precip >= 20mm) OR (precip >= 30mm AND visibility <= 2km)
   - "alert": (1.5 <= tide_height <= 2m AND 10 <= precip < 20mm) OR 20 <= precip < 30mm
   - "watch": 0.8 <= tide_height <= 1.5m OR 10 <= precip <= 20mm
   
   For "rip_current":
   - "warning": swell_period > 18s AND swell_height > 2m
   - "alert": 15 <= swell_period <= 18s AND 1.5 <= swell_height <= 2m
   - "watch": 12 <= swell_period <= 15s AND 1 <= swell_height <= 1.5m

3. Methods:

   @staticmethod
   def applies_to_hazard(hazard_type: str) -> bool:
   - Check if hazard is in NATURAL_HAZARDS list
   - Normalize hazard name (lowercase, replace spaces/slashes with underscores)

   @staticmethod
   async def fetch_environmental_data(lat: float, lon: float) -> Dict[str, Any]:
   - Fetch weather data from existing app. services.weather_service. WeatherService
   - Fetch earthquake data from USGS API (https://earthquake.usgs.gov/fdsnws/event/1/query)
     * Parameters: lat, lon, maxradiuskm=500, minmagnitude=4.5, limit=1, orderby=time
   - Optional: Fetch marine data from Stormglass API if MARINE_API_KEY exists
   - Return dict with keys: wind_kph, gust_kph, pressure_mb, precip_mm, vis_km, humidity, temp_c, sig_ht_mt, swell_ht_mt, swell_period_secs, tide_height_mt, magnitude, depth_km
   - Handle API errors gracefully

   @staticmethod
   def calculate_criticality(hazard_type: str, env_data: Dict) -> str:
   - Apply HAZARD_RULES to determine criticality level
   - Check "warning" → "alert" → "watch" in order
   - Apply threat_boost if available
   - Return: "Warning", "Alert", "Watch", or "No Threat"

   @staticmethod
   async def validate(hazard_type: str, lat: float, lon: float) -> Dict[str, Any]:
   - Check if validation applies using applies_to_hazard()
   - If not applicable: return {"applies": False, "score": 1.0, ... }
   - Fetch environmental data
   - Calculate criticality
   - Determine if user report is valid (criticality in Warning/Alert/Watch)
   - Calculate score: Warning=1.0, Alert=0. 85, Watch=0.70, No Threat=0.0
   - Calculate confidence based on data availability (min(len(env_data)/8, 1. 0))
   - Return dict with: applies, hazard, criticality, user_report (bool), reason, score, confidence, environmental_data

4. Required imports: httpx, typing, os, app.services.weather_service

Provide the complete weather_validator.py file with async methods and proper error handling.
```

---

## **Prompt 4: Layer 3 - Text Analyzer with VectorDB Integration**

```
Create a text analysis service that integrates with the existing CoastGuardian VectorDB for semantic similarity. 

CREATE NEW FILE: backend/app/services/text_analyzer.py

REQUIREMENTS:

1. Add BlueRadar Intelligence path to sys.path:
   sys.path.append(os.path.join(os.path.dirname(__file__), '../../../blueradar_intelligence'))

2.  Import NLP processor from BlueRadar (replaces VectorDB):
   try:
       from services.fast_nlp import FastNLPProcessor
       BLUERADAR_AVAILABLE = True
   except ImportError:
       BLUERADAR_AVAILABLE = False

3.  Create TextAnalyzer class with constants:

   PANIC_KEYWORDS = ["help", "urgent", "emergency", "dying", "death", "severe", "critical", "disaster", "catastrophe", "apocalypse", "everyone", "all", "mass"]
   
   SPAM_KEYWORDS = ["buy", "click", "link", "free", "prize", "winner", "subscribe", "follow", "like", "share", "comment", "promotion", "offer"]

4. Methods:

   @staticmethod
   def get_vector_db() -> CoastGuardianVectorDB:
   - Try to get existing VectorDB instance
   - If None, initialize new one
   - Return None if unavailable, handle gracefully

   @staticmethod
   def detect_panic_level(text: str) -> float:
   - Count panic keywords in text (lowercase)
   - Count exclamation marks
   - Calculate CAPS ratio (uppercase chars / total chars)
   - Formula: (panic_count * 0.3) + (min(exclamation/3, 1. 0) * 0.3) + (min(caps_ratio*2, 1.0) * 0.4)
   - Return: 0.0 to 1.0

   @staticmethod
   def detect_spam(text: str) -> bool:
   - Count spam keywords
   - Check for URLs using regex r'http[s]?://'
   - Return True if: spam_count >= 2 OR has_url

   @staticmethod
   def extract_keywords(text: str) -> List[str]:
   - Extract words with 4+ letters using regex r'\b[a-zA-Z]{4,}\b'
   - Remove stopwords: 'this', 'that', 'with', 'from', 'have', 'been', 'were', 'there', 'what', 'when', 'where', 'which', 'will', 'would', 'could', 'about'
   - Return top 10 unique keywords

   @staticmethod
   def analyze(description: str, hazard_type: str) -> Dict[str, Any]:
   - Validate description (min 5 chars)
   - Get VectorDB instance
   - Run panic detection, spam detection, keyword extraction
   - If VectorDB available:
     * Call vector_db.classify_disaster_type(description, confidence_threshold=0.4)
     * Get predicted_type, confidence, similar_results
     * Calculate vector_similarity from top 3 results average
     * Check if predicted type matches reported type (normalized)
     * Add anomaly flag if mismatch with confidence > 0.6
   - Calculate overall score:
     * If spam: score = 0.0
     * Otherwise: (vector_similarity * 0.5) + (vector_confidence * 0.3) + ((1 - panic_level) * 0.2)
   - Calculate confidence: min(len(description)/100, 1.0) * (1 - panic_level)
     * Reduce by 50% if VectorDB unavailable
   - Return dict with: score, vector_similarity, vector_predicted_type, vector_confidence, panic_level, is_spam, keywords, anomaly_flags, confidence

5. Handle all edge cases (empty text, VectorDB unavailable, API errors)

6. Required imports: typing, re, sys, os

Provide the complete text_analyzer.py file with proper error handling and fallback modes.
```

---

## **Prompt 5: Layer 4 - Image Classifier**

```
Create a CNN-based image classification service for 4 human-made hazards.

CREATE NEW FILE: backend/app/services/image_classifier.py

REQUIREMENTS:

1. Create ImageClassifier class

2. Constants:

   IMAGE_VALIDATION_HAZARDS = ["beached_aquatic_animal", "beached_animal", "ship_wreck", "marine_debris", "oil_spill"]
   
   HAZARD_CLASSES = ["beached_animal", "ship_wreck", "marine_debris", "oil_spill", "clean_other"]

3. Initialize method:
   def __init__(self, model_path: str = None):
   - Load ResNet50 pre-trained on ImageNet using torchvision.models
   - Replace final FC layer with Linear(in_features, 5) for 5 classes
   - If model_path exists and valid: load fine-tuned weights
   - Otherwise: use pre-trained ResNet50 with warning
   - Set model to eval mode
   - Create transform pipeline:
     * Resize(256)
     * CenterCrop(224)
     * ToTensor()
     * Normalize with ImageNet mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]

4. Methods:

   @staticmethod
   def applies_to_hazard(hazard_type: str) -> bool:
   - Check if hazard in IMAGE_VALIDATION_HAZARDS
   - Normalize hazard name

   def predict(self, image_path: str) -> Tuple[str, float, Dict[str, float]]:
   - Open image, convert to RGB
   - Apply transform, add batch dimension
   - Run model inference with torch.no_grad()
   - Apply softmax to get probabilities
   - Get max confidence and predicted class index
   - Create dict of all class probabilities
   - Return: (predicted_class_name, confidence, all_probabilities_dict)
   - Handle errors: return ("clean_other", 0.0, {})

   def validate(self, image_path: str, reported_hazard: str) -> Dict[str, Any]:
   - Check if validation applies
   - If not: return {"applies": False, "score": 1.0, ...}
   - Run predict()
   - Normalize reported hazard (beached_aquatic_animal → beached_animal)
   - Check if predicted class matches reported hazard
   - Special handling:
     * If predicted "clean_other": matches = False
     * If exact match: matches = True
     * If reported in top-2 predictions AND confidence > 0.3: matches = True
     * Otherwise: matches = False
   - Calculate score:
     * If matches: score = confidence
     * If not: score = max(0.0, 0.3 - confidence)
   - Return dict with: applies, classification, confidence, matches_report, score, reason, all_probabilities

5. Global instance:
   _image_classifier = None
   
   def get_image_classifier() -> ImageClassifier:
   - Return global instance or create new one
   - Use model_path from env var HAZARD_IMAGE_MODEL_PATH (default: "models/hazard_classifier.pth")

6. Required imports: typing, torch, torchvision. transforms, torchvision.models, PIL. Image, os

Provide the complete image_classifier.py file with proper PyTorch inference code.
```

---

## **Prompt 6: Layer 5 - Reporter Score Tracker**

```
Create a service to track and calculate reporter accuracy scores based on historical reports.

CREATE NEW FILE: backend/app/services/reporter_score. py

REQUIREMENTS:

1.  Create ReporterScoreTracker class

2. Initialize method:
   def __init__(self, db):
   - Store MongoDB database instance
   - Define collection names: "hazard_reports", "reporter_scores"

3. Methods:

   async def get_reporter_history(self, user_id: str, limit: int = 50) -> List[Dict]:
   - Query hazard_reports collection
   - Filter by: reporter_id = user_id, workflow_status in ["verified", "rejected", "auto_rejected"]
   - Sort by created_at descending
   - Limit results
   - Return list of report dicts

   async def calculate_accuracy_score(self, user_id: str) -> float:
   - Get reporter history
   - If no history: return 0.5 (neutral score)
   - Count verified vs rejected reports
   - Weight recent reports more heavily:
     * Use exponential decay: weight = 0.9 ^ report_age_in_days
     * For each report: add (1. 0 * weight) if verified, (0.0 * weight) if rejected
   - Calculate: weighted_sum / total_weights
   - Bonus for consistency: if accuracy > 0.8 AND report_count > 10: bonus = 0.05
   - Final score: min(calculated_score + bonus, 1.0)
   - Return: float (0.0 to 1. 0)

   async def update_reporter_score(self, user_id: str) -> float:
   - Calculate new accuracy score
   - Upsert to reporter_scores collection:
     {
       "user_id": user_id,
       "accuracy_score": score,
       "total_reports": count,
       "verified_reports": verified_count,
       "rejected_reports": rejected_count,
       "last_updated": datetime.utcnow()
     }
   - Return score

   async def get_score_weight(self, accuracy_score: float) -> float:
   - Convert accuracy to weight for composite scoring
   - Formula:
     * If score >= 0.8: weight = 1.2 (bonus)
     * If 0.6 <= score < 0.8: weight = 1.0 (neutral)
     * If 0. 4 <= score < 0. 6: weight = 0.8 (penalty)
     * If score < 0.4: weight = 0.5 (heavy penalty)
   - Return weight

   async def should_flag_for_review(self, user_id: str) -> Tuple[bool, str]:
   - Get reporter score
   - Rules:
     * If accuracy < 0.3: flag = True, reason = "Low accuracy score (<30%)"
     * If recent 5 reports all rejected: flag = True, reason = "Recent reports consistently rejected"
     * Otherwise: flag = False, reason = ""
   - Return (should_flag, reason)

4. Global instance function:
   def get_reporter_tracker(db) -> ReporterScoreTracker:
   - Create and return tracker instance

5. Required imports: typing, datetime, motor.motor_asyncio

Provide the complete reporter_score. py file with MongoDB async operations.
```

---

## **Prompt 7: Composite Score Calculator and Main Verification Pipeline**

```
Create the main verification pipeline that orchestrates all 6 layers and calculates the composite score.

CREATE NEW FILE: backend/app/services/verification_pipeline.py

REQUIREMENTS:

1. Import all validators:
   - from . geofence_validator import GeofenceValidator
   - from .weather_validator import WeatherValidator
   - from .text_analyzer import TextAnalyzer
   - from . image_classifier import get_image_classifier
   - from .reporter_score import get_reporter_tracker

2. Create VerificationPipeline class

3. Constants for weights:
   LAYER_WEIGHTS = {
       "geofence": 1.0,  # Binary - must pass
       "weather": 0. 25,   # Only for natural hazards
       "text": 0.25,      # All reports
       "image": 0. 20,     # Only for 4 human-made hazards
       "reporter": 0.30   # All reports
   }
   
   AUTO_APPROVAL_THRESHOLD = 75.0  # Score must be >= 75% for auto-approval

4. Initialize:
   def __init__(self, db):
   - Store database instance
   - Initialize image classifier
   - Initialize reporter tracker

5. Main method:
   async def verify_report(self, report_dict: Dict) -> Dict[str, Any]:
   
   Extract from report: hazard_type, latitude, longitude, description, image_paths, reporter_id
   
   Initialize results dict to store all layer results
   
   # LAYER 1: Geofencing (ALL reports - AUTO-REJECT if fails)
   - Call GeofenceValidator.validate(lat, lon)
   - Store result in results["geofence"]
   - If auto_reject == True:
     * Set workflow_status = "auto_rejected"
     * Set auto_rejection_reason
     * Set composite_score = 0.0
     * Return immediately (skip other layers)
   
   # LAYER 2: Weather Validation (Natural hazards only)
   - Check if WeatherValidator.applies_to_hazard(hazard_type)
   - If yes:
     * Call await WeatherValidator.validate(hazard_type, lat, lon)
     * Store result in results["weather"]
     * Store applies_weather_validation = True
   - If no:
     * Store results["weather"] = {"applies": False, "score": 1.0}
     * Store applies_weather_validation = False
   
   # LAYER 3: Text Analysis (ALL reports)
   - Call TextAnalyzer.analyze(description, hazard_type)
   - Store result in results["text"]
   - Check for spam: if is_spam == True, flag for manual review
   
   # LAYER 4: Image Classification (4 human-made hazards only)
   - Check if ImageClassifier.applies_to_hazard(hazard_type)
   - If yes AND image_paths exist:
     * Call image_classifier.validate(image_paths[0], hazard_type)
     * Store result in results["image"]
     * Store applies_image_validation = True
   - If no:
     * Store results["image"] = {"applies": False, "score": 1.0}
     * Store applies_image_validation = False
   
   # LAYER 5: Reporter Score (ALL reports)
   - Call await reporter_tracker.calculate_accuracy_score(reporter_id)
   - Call await reporter_tracker.get_score_weight(accuracy_score)
   - Store in results["reporter"]
   - Check if should_flag_for_review()
   
   # LAYER 6: Composite Score Calculation
   - Calculate weighted score using only applicable layers:
     
     total_weight = 0
     weighted_sum = 0
     
     # Weather (if applies)
     if applies_weather_validation:
         weighted_sum += results["weather"]["score"] * LAYER_WEIGHTS["weather"]
         total_weight += LAYER_WEIGHTS["weather"]
     
     # Text (always applies)
     weighted_sum += results["text"]["score"] * LAYER_WEIGHTS["text"]
     total_weight += LAYER_WEIGHTS["text"]
     
     # Image (if applies)
     if applies_image_validation:
         weighted_sum += results["image"]["score"] * LAYER_WEIGHTS["image"]
         total_weight += LAYER_WEIGHTS["image"]
     
     # Reporter (always applies, with weight modifier)
     reporter_weight = LAYER_WEIGHTS["reporter"] * results["reporter"]["weight"]
     weighted_sum += results["reporter"]["accuracy_score"] * reporter_weight
     total_weight += reporter_weight
     
     # Calculate final score (0-100)
     composite_score = (weighted_sum / total_weight) * 100
   
   # Determine workflow status
   - If composite_score >= AUTO_APPROVAL_THRESHOLD AND not flagged:
     * workflow_status = "verified"
     * auto_approval_eligible = True
     * manual_review_required = False
   - Else:
     * workflow_status = "needs_manual_review"
     * auto_approval_eligible = False
     * manual_review_required = True
     * Determine manual_review_reason from layer failures
   
   # Build verification_layers dict for database
   verification_layers = {}
   for layer_name, layer_result in results.items():
       verification_layers[layer_name] = {
           "layer_name": layer_name,
           "status": layer_result. get("status", "completed"),
           "score": layer_result.get("score", 0.0),
           "confidence": layer_result.get("confidence", 1.0),
           "reason": layer_result.get("reason", ""),
           "timestamp": datetime.utcnow(),
           "metadata": layer_result
       }
   
   # Return complete verification result
   return {
       "verification_layers": verification_layers,
       "composite_verification_score": composite_score,
       "workflow_status": workflow_status,
       "auto_approval_eligible": auto_approval_eligible,
       "manual_review_required": manual_review_required,
       "manual_review_reason": manual_review_reason if manual_review_required else None,
       "auto_rejection_reason": auto_rejection_reason if auto_rejected else None,
       
       # Individual layer fields for easy querying
       "geofence_status": results["geofence"]["status"],
       "distance_from_coastline_km": results["geofence"]["distance_km"],
       "nearest_coastal_point": results["geofence"]["nearest_coast"],
       
       "weather_criticality": results["weather"]. get("criticality"),
       "weather_validation_result": results["weather"].get("user_report"),
       "weather_score": results["weather"]["score"],
       "applies_weather_validation": applies_weather_validation,
       
       "text_analysis_score": results["text"]["score"],
       "vector_similarity_score": results["text"]["vector_similarity"],
       "vector_predicted_type": results["text"]["vector_predicted_type"],
       "panic_level": results["text"]["panic_level"],
       "is_spam": results["text"]["is_spam"],
       
       "image_classification": results["image"].get("classification"),
       "image_confidence": results["image"].get("confidence"),
       "image_matches_report": results["image"].get("matches_report"),
       "applies_image_validation": applies_image_validation,
       
       "reporter_accuracy_score": results["reporter"]["accuracy_score"]
   }

6. Required imports: typing, datetime, all validator imports

Provide the complete verification_pipeline.py file with proper async/await and error handling.
```

---

## **Prompt 8: API Endpoint Integration**

```
Integrate the verification pipeline into the hazard report submission API endpoint. 

MODIFY FILE: backend/app/api/v1/hazards. py (or wherever your hazard submission endpoint exists)

REQUIREMENTS:

1.  Import the verification pipeline:
   from app.services.verification_pipeline import VerificationPipeline

2.  Modify the POST /hazards endpoint (or similar report submission endpoint):

   Current flow:
   - User submits hazard report
   - Save to database
   - Return response
   
   New flow:
   - User submits hazard report
   - Create initial report in database with workflow_status="pending_verification"
   - Initialize VerificationPipeline(db)
   - Run verification: verification_result = await pipeline.verify_report(report_dict)
   - Update report in database with all verification fields from verification_result
   - If auto_rejected: return 400 with rejection reason
   - If needs_manual_review: return 202 (Accepted) with message about pending review
   - If auto_approved: return 201 (Created) with verification details
   - Return response with verification summary

3. Add a new GET endpoint: GET /hazards/{report_id}/verification
   - Fetch report from database
   - Return verification_layers, composite_score, workflow_status
   - Include breakdown of each layer result
   - Show auto_approval_eligible status

4. Add a new POST endpoint: POST /hazards/{report_id}/rerun-verification
   - For admins/analysts only (check role)
   - Fetch existing report
   - Re-run verification pipeline
   - Update database with new results
   - Return updated verification details

5. Update the report listing endpoint to include verification fields:
   - Add filters: workflow_status, auto_approval_eligible, manual_review_required
   - Include composite_score in response
   - Show verification summary for each report

6. Error handling:
   - Catch verification pipeline errors
   - Log errors with report_id
   - Set workflow_status = "verification_failed" if errors occur
   - Still save report but flag for manual review

Response format examples:

Auto-approved:
{
  "report_id": ".. .",
  "status": "success",
  "message": "Report verified and approved automatically",
  "workflow_status": "verified",
  "composite_score": 87.5,
  "verification_summary": {
    "geofence": "Passed - 12. 3km from Mumbai coast",
    "weather": "Warning conditions detected - matches report",
    "text": "High confidence - matches tsunami category",
    "reporter": "High accuracy score (85%)"
  }
}

Needs manual review:
{
  "report_id": ".. .",
  "status": "pending",
  "message": "Report submitted for manual review",
  "workflow_status": "needs_manual_review",
  "composite_score": 62.3,
  "manual_review_reason": "Weather validation failed - no threat detected",
  "estimated_review_time": "2-4 hours"
}

Auto-rejected:
{
  "status": "rejected",
  "message": "Report automatically rejected",
  "workflow_status": "auto_rejected",
  "auto_rejection_reason": "Location too far inland (45. 2km from nearest coast)",
  "composite_score": 0.0
}

Provide the complete updated hazards.py API file with all endpoints and proper FastAPI decorators.
```

---

## **Prompt 9: Admin Dashboard Endpoints**

```
Create API endpoints for analysts and admins to manage the manual review queue.

CREATE NEW FILE: backend/app/api/v1/verification_queue.py

REQUIREMENTS:

1. Import dependencies:
   - FastAPI router, HTTPException, Depends
   - Authentication dependencies (get_current_user, require_roles)
   - Database dependency
   - Verification pipeline

2. Create router = APIRouter(prefix="/verification-queue", tags=["Verification Queue"])

3.  Endpoints to create:

   GET /verification-queue/pending
   - Requires role: analyst or admin
   - Query params: 
     * limit: int (default 50)
     * skip: int (default 0)
     * hazard_type: Optional[str]
     * min_score: Optional[float]
     * max_score: Optional[float]
   - Query database:
     * Filter: workflow_status = "needs_manual_review"
     * Sort by: composite_score ASC (lowest scores first - most urgent)
     * Include: all verification layers, reporter info, location details
   - Return paginated list with total count
   
   GET /verification-queue/stats
   - Requires role: analyst or admin
   - Calculate and return:
     * total_pending: count of needs_manual_review
     * total_auto_approved_today: count of verified today
     * total_auto_rejected_today: count of auto_rejected today
     * avg_composite_score: average of pending reports
     * reports_by_hazard_type: count per hazard type
     * reports_by_geofence_status: inside vs outside zone
     * low_priority: score < 40 (likely false reports)
     * medium_priority: 40 <= score < 60
     * high_priority: 60 <= score < 75 (close to approval)
   
   GET /verification-queue/{report_id}/details
   - Requires role: analyst or admin
   - Fetch report with full verification details
   - Return:
     * All layer results with confidence scores
     * Environmental data used for weather validation
     * VectorDB similarity results
     * Image classification probabilities
     * Reporter history and accuracy
     * Recommended action (approve/reject) based on scores
   
   POST /verification-queue/{report_id}/approve
   - Requires role: authority or admin
   - Request body: {reason: Optional[str], create_ticket: bool}
   - Update report:
     * Set workflow_status = "verified"
     * Set verified_by = current_user_id
     * Set verified_at = now
     * Set manual_verification_reason = reason
   - If create_ticket: trigger ticket creation workflow
   - Update reporter score (positive feedback)
   - Return updated report
   
   POST /verification-queue/{report_id}/reject
   - Requires role: analyst or admin
   - Request body: {reason: str (required), notify_reporter: bool}
   - Update report:
     * Set workflow_status = "rejected"
     * Set rejected_by = current_user_id
     * Set rejected_at = now
     * Set rejection_reason = reason
   - Update reporter score (negative feedback)
   - If notify_reporter: send notification to user
   - Return updated report
   
   POST /verification-queue/{report_id}/request-info
   - Requires role: analyst or admin
   - Request body: {message: str, requested_fields: List[str]}
   - Create communication record:
     * Type: "info_request"
     * From: analyst
     * To: reporter
     * Message: message
     * Requested fields: ["additional_photos", "more_details", etc.]
   - Set report status to "awaiting_info"
   - Send notification to reporter
   - Return communication record
   
   GET /verification-queue/reporter/{user_id}/history
   - Requires role: analyst or admin
   - Get all reports from this reporter
   - Calculate statistics:
     * Total reports
     * Verified vs rejected ratio
     * Average composite score
     * Common failure reasons
     * Flagged for review count
   - Return reporter profile with stats

4. Add proper FastAPI dependencies:
   - Authentication: Depends(get_current_user)
   - Role checks: Depends(require_roles(["analyst", "admin"]))
   - Database: Depends(get_database)

5. Response models (use Pydantic):
   - PendingReportResponse
   - QueueStatsResponse
   - ReportDetailResponse
   - ApprovalResponse
   - RejectionResponse
   - ReporterHistoryResponse

6. Error handling:
   - 404 if report not found
   - 403 if insufficient permissions
   - 400 if invalid state transition (e.g., already approved)

Provide the complete verification_queue.py file with all endpoints, proper authentication, and Pydantic models.
```

---

## **Prompt 10: Frontend Integration**

```
Update the frontend to display verification status and admin review queue.

TASKS:

1. CREATE NEW COMPONENT: frontend/components/VerificationStatus.js
   - Props: report (hazard report object)
   - Display:
     * Workflow status badge (color-coded)
     * Composite score with progress bar
     * Layer-by-layer breakdown (collapsible)
     * Each layer shows: icon, status, score, reason
     * Auto-approval eligible indicator
     * Manual review reason if applicable
   - Styling: Use Tailwind with color-coded badges
     * Auto-approved: green
     * Pending review: yellow
     * Auto-rejected: red
     * Verification failed: gray

2. CREATE NEW PAGE: frontend/app/analyst/verification-queue/page.js
   - Role-gated: only accessible to analyst/admin
   - Features:
     * Stats cards at top (total pending, avg score, priority breakdown)
     * Filter sidebar: hazard type, score range, date range
     * Report list (paginated):
       - Show: thumbnail, hazard type, location, composite score, time ago
       - Color-code by priority (red < 40, yellow 40-60, green 60-75)
       - Click to expand details
     * Expanded view shows:
       - Full verification breakdown
       - Map with location
       - All submitted images
       - Reporter history
       - Action buttons: Approve, Reject, Request More Info
   
3. MODIFY: frontend/app/dashboard/page.js (citizen view)
   - Add "My Reports" tab
   - For each report, show:
     * VerificationStatus component
     * If pending review: "Your report is being reviewed"
     * If approved: "Your report has been verified"
     * If rejected: Show rejection reason
     * If info requested: Show analyst message with form to respond

4. CREATE NEW HOOK: frontend/hooks/useVerification.js
   - Functions:
     * fetchVerificationDetails(reportId)
     * approveReport(reportId, reason, createTicket)
     * rejectReport(reportId, reason)
     * requestMoreInfo(reportId, message, fields)
     * fetchQueueStats()
     * fetchPendingReports(filters)
   - Use React Query or SWR for caching

5. UPDATE: frontend/app/report/[id]/page.js
   - Add VerificationStatus section below report details
   - Show timeline of verification process
   - Display all layer results with explanations

6. CREATE COMPONENT: frontend/components/LayerBreakdown.js
   - Visual breakdown of each verification layer
   - Icons for each layer:
     * 📍 Geofencing
     * 🌤️ Weather Validation
     * 📝 Text Analysis
     * 🖼️ Image Classification
     * 👤 Reporter Score
     * 🎯 Composite Score
   - Each layer shows:
     * Pass/Fail/N/A status
     * Score percentage
     * Confidence level
     * Detailed reason (expandable)

7.  Styling guidelines:
   - Use consistent color scheme:
     * Success/Passed: green-500
     * Warning/Review: yellow-500
     * Failed/Rejected: red-500
     * N/A/Skipped: gray-400
   - Score bars: gradient based on score
   - Smooth animations for expanding/collapsing
   - Responsive design for mobile

Provide the following files:
1. VerificationStatus.js
2.  verification-queue/page.js
3. useVerification.js hook
4. LayerBreakdown.js

With proper React/Next.js code, Tailwind styling, and API integration.
```

---

## **Prompt 11: Testing and Documentation**

```
Create tests and documentation for the verification system.

TASKS:

1.  CREATE TEST FILE: backend/tests/test_verification_pipeline.py
   - Unit tests for each validator:
     * test_geofence_validator_inland_pass()
     * test_geofence_validator_inland_reject()
     * test_geofence_validator_offshore_pass()
     * test_geofence_validator_offshore_reject()
     * test_weather_validator_tsunami()
     * test_weather_validator_cyclone()
     * test_weather_validator_natural_hazard_pass()
     * test_weather_validator_not_applicable()
     * test_text_analyzer_spam_detection()
     * test_text_analyzer_panic_detection()
     * test_text_analyzer_vectordb_integration()
     * test_image_classifier_match()
     * test_image_classifier_mismatch()
     * test_reporter_score_calculation()
   
   - Integration tests:
     * test_full_pipeline_auto_approve()
     * test_full_pipeline_auto_reject()
     * test_full_pipeline_manual_review()
     * test_pipeline_with_missing_data()
   
   - Use pytest with async support
   - Mock external API calls
   - Include fixtures for sample reports

2. CREATE DOCUMENTATION: VERIFICATION_SYSTEM. md
   - Section 1: Overview
     * Purpose of verification system
     * 6-layer architecture diagram
     * Auto-approval threshold
   
   - Section 2: Layer Details
     * For each layer:
       - Purpose
       - Applies to which hazards
       - Input data requirements
       - Validation logic
       - Output format
       - Example scenarios
   
   - Section 3: Composite Score Calculation
     * Weight distribution
     * Formula explanation
     * Examples with different combinations
   
   - Section 4: Workflow States
     * pending_verification
     * verified (auto-approved)
     * needs_manual_review
     * rejected
     * auto_rejected
     * State transition diagram
   
   - Section 5: API Reference
     * All endpoints with examples
     * Request/response schemas
     * Authentication requirements
   
   - Section 6: Admin Guide
     * How to use verification queue
     * Best practices for manual review
     * Handling edge cases
   
   - Section 7: Configuration
     * Environment variables
     * Tuning thresholds
     * Weight adjustments

3. CREATE: API_EXAMPLES.md
   - cURL examples for all endpoints
   - Postman collection JSON
   - Python client examples
   - JavaScript/fetch examples

4. UPDATE: README.md (root)
   - Add "Verification System" section
   - Link to detailed documentation
   - Quick start guide for testing
   - Architecture diagram

Provide:
1. Complete test_verification_pipeline.py
2.  VERIFICATION_SYSTEM.md
3. Updated README.md section
```

---

## 🎯 **Usage Instructions**

1. **Copy each prompt one at a time** into Claude Code Opus
2. **Wait for completion** of each step before moving to the next
3. **Review the generated code** before proceeding
4. **Test each component** individually before integration
5. **Adjust** any paths or configurations based on your actual project structure

## 📌 **Important Notes**

- Prompts 1-7 build the core system
- Prompt 8 integrates into existing API
- Prompt 9 adds admin features
- Prompt 10 updates frontend
- Prompt 11 adds tests and docs

- **Dependencies to install** (add to requirements.txt):
  - `geopy` (for geofencing)
  - `torch` and `torchvision` (for image classification)
  - Additional as needed

- Make sure your MongoDB and existing services (weather_service. py, VectorDB) are functional before starting

Good luck with your implementation! 🚀
