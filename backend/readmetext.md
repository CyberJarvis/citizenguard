# 🌊 CoastGuardian - Layered Verification & Ticketing System

## Complete Technical Documentation (Conceptual Overview)

---

## 📋 TABLE OF CONTENTS

1. [Verification System Architecture](#verification-system-architecture)
2.  [Layered Verification Explanation](#layered-verification-explanation)
3. [Ticketing System Architecture](#ticketing-system-architecture)
4. [Workflow & User Journeys](#workflow--user-journeys)
5.  [Data Models & Relationships](#data-models--relationships)
6. [Security & Permissions](#security--permissions)
7.  [Real-time Communication](#real-time-communication)
8. [Notification System](#notification-system)
9. [Analytics & Reporting](#analytics--reporting)
10. [Deployment Strategy](#deployment-strategy)

---

## 🎯 VERIFICATION SYSTEM ARCHITECTURE

### System Purpose
The verification system acts as an intelligent gatekeeper that automatically validates hazard reports using 6 distinct layers of analysis.  This multi-layered approach reduces false reports, identifies genuine threats, and triages reports for manual review when needed.

### Core Principles

**1. Automated First-Line Defense**
- Every submitted report goes through automated verification immediately
- No human intervention needed for clear-cut cases (>75% score = auto-approve, outside geofence = auto-reject)
- Reduces analyst workload by 60-70%

**2. Conditional Layer Application**
- Not all verification layers apply to all hazard types
- Weather validation only for natural hazards (Tsunami, Cyclone, High Waves, Flooded Coastline, Rip Current)
- Image classification only for specific human-made hazards (Beached Animal, Ship Wreck, Marine Debris, Oil Spill)
- Dynamic weight redistribution when layers don't apply

**3. Multi-Signal Integration**
- Combines geospatial data, real-time weather/ocean conditions, semantic text analysis, computer vision, and historical user behavior
- Each layer provides independent verification signal
- Composite score calculated using weighted average

**4. Transparent Scoring**
- Every layer produces a score (0. 0 to 1.0), confidence level, and human-readable reason
- Full audit trail maintained
- Users can see exactly why their report was approved, rejected, or flagged for review

---

## 🔍 LAYERED VERIFICATION EXPLANATION

### Layer 1: Geofencing Validation (ALL Reports - 20% Weight)

**Purpose**: Ensure reports are from valid coastal areas

**How It Works**:
- Calculates distance from report location to nearest coastal reference point (100+ points covering entire Indian coastline)
- Uses reverse geocoding to determine if location is on land or water
- Compares against thresholds: 20km inland limit, 30km offshore limit

**Decision Logic**:
- **PASS**: Location within 20km inland OR within 30km offshore
- **AUTO-REJECT**: Location beyond both limits

**Why Auto-Reject**:
- Reports from Delhi, Bangalore, or other inland cities are immediately invalid
- Prevents spam and irrelevant reports from entering the system
- No human review needed - geographical validation is objective

**Example Scenarios**:
- Mumbai beach (19. 07°N, 72.87°E) → Distance to coast: 0.5km → **PASS**
- Delhi (28.61°N, 77.20°E) → Distance to coast: 200km inland → **AUTO-REJECT**
- 100km offshore in Arabian Sea → Distance to coast: 100km → **AUTO-REJECT** (too far offshore)

---

### Layer 2: Weather Parameter Validation (Natural Hazards Only - 25% Weight)

**Purpose**: Validate reported natural hazards against real-time environmental data

**Applies To**: 
- Tsunami
- Cyclone  
- High Waves
- Flooded Coastline
- Rip Current

**Does NOT Apply To**:
- Oil Spill (human-made)
- Ship Wreck (human-made)
- Beached Animal (visual identification)
- Marine Debris (human-made)
- Other hazards

**How It Works**:

**Data Sources Integrated**:
1. **USGS Earthquake API**: Real-time seismic data for tsunami validation
2. **Weather API**: Wind speed, atmospheric pressure, precipitation, visibility
3. **Marine API** (StormGlass): Wave height, swell period, tide information

**Validation Rules by Hazard Type**:

**Tsunami Validation**:
- **Warning Level**: Earthquake magnitude ≥8.0 AND depth ≤50km, OR tide height >1. 5m boost
- **Alert Level**: Magnitude 7.0-7.9 AND depth ≤70km
- **Watch Level**: Magnitude 6.0-6.9 offshore
- **No Threat**: Magnitude <6.0 OR depth >100km

**Cyclone Validation**:
- **Warning Level**: Wind ≥90 kph OR gust ≥110 kph OR pressure <985mb OR (heavy rain ≥30mm AND visibility ≤2km)
- **Alert Level**: Wind 70-89 kph OR pressure 985-994mb OR rain 20-29mm
- **Watch Level**: Wind 50-69 kph OR pressure 995-1004mb
- **No Threat**: Wind <50 kph AND pressure ≥1005mb

**High Waves Validation**:
- **Warning Level**: Wave height >4m OR swell height >3m OR swell period >18 seconds OR (tide >2m AND high tide)
- **Alert Level**: Wave 3-4m OR swell 2-3m OR period 15-18s OR tide 1.5-2m
- **Watch Level**: Wave 2-3m OR swell 1.5-2m OR period 12-15s

**Flooded Coastline Validation**:
- **Warning Level**: (Tide >2m AND rain ≥20mm) OR (rain ≥30mm AND visibility ≤2km)
- **Alert Level**: (Tide 1.5-2m AND rain 10-19mm) OR rain 20-29mm
- **Watch Level**: Tide 0.8-1.5m OR rain 10-20mm

**Rip Current Validation**:
- **Warning Level**: Swell period >18s AND swell height >2m
- **Alert Level**: Period 15-18s AND height 1.5-2m
- **Watch Level**: Period 12-15s AND height 1-1.5m

**Scoring**:
- **Warning** detected → Score: 1.0 (100%)
- **Alert** detected → Score: 0.85 (85%)
- **Watch** detected → Score: 0. 70 (70%)
- **No Threat** → Score: 0.0 (0%)

**Example**:
- User reports: "Cyclone approaching Mumbai"
- System fetches: Wind speed = 95 kph, pressure = 982 mb, rain = 35mm
- Analysis: Wind ≥90 kph ✓ AND pressure <985mb ✓ → **Warning Level**
- Result: **VALID REPORT** - Score: 1.0

**What Happens When Layer Doesn't Apply**:
- For Oil Spill report: Weather layer status = "skipped"
- Weight (25%) redistributed proportionally to other active layers
- No penalty for skipped layers

---

### Layer 3: Text Analysis (ALL Reports - 25% Weight)

**Purpose**: Semantic analysis of report description using AI vector database

**Applies To**: ALL hazard types

**Technology**: 
- FAISS (Facebook AI Similarity Search) vector database
- Sentence Transformers (multilingual model)
- Pre-trained on marine disaster corpus (existing system)

**How It Works**:

**Step 1: Text Encoding**
- User's description converted to 384-dimensional vector embedding
- Captures semantic meaning, not just keywords
- Language-agnostic (works for English, Hindi, regional languages)

**Step 2: Similarity Search**
- Vector compared against reference database of known hazard descriptions
- Finds top-K most similar examples (K=10)
- Each similarity scored 0.0 to 1.0

**Step 3: Weighted Classification**
- Similar examples vote for hazard type
- Votes weighted by similarity scores (higher similarity = stronger vote)
- Predicts most likely hazard type with confidence score

**Step 4: Anomaly Detection**
- **Spam Detection**: Keywords like "buy", "click", "link", "subscribe" → Flagged
- **Panic Level**: Excessive exclamation marks, ALL CAPS, panic keywords → Scored 0-1
- **Mismatch Detection**: If predicted type doesn't match reported type with high confidence → Flagged

**Scoring Components**:
- **Vector Similarity** (50%): Average similarity to top-3 matching examples
- **Classification Confidence** (30%): Confidence in predicted hazard type
- **Inverse Panic Level** (20%): Lower panic = higher score

**Example Scenario**:

**Report Text**: "Massive waves crashing on shore, water level rising rapidly, people evacuating"

**Vector Analysis**:
- Top Match #1: "Tsunami waves approaching Mumbai coast" (similarity: 0.82)
- Top Match #2: "Giant waves hitting shore, evacuation orders" (similarity: 0.78)
- Top Match #3: "Large scale coastal flooding from ocean" (similarity: 0.65)
- Predicted Type: Tsunami (confidence: 0.85)
- Panic Level: 0.3 (moderate urgency language, not hysterical)

**Score Calculation**:
- Similarity: (0.82 + 0.78 + 0.65) / 3 = 0. 75
- Final Score: (0.75 × 0.5) + (0.85 × 0.3) + ((1-0.3) × 0.2) = 0.77

**Result**: High-quality description, semantically matches tsunami patterns → **PASS**

**Spam Example**:
"Check out this amazing beach!  Click link for prizes!  Free vacation! Follow now!"
- Spam keywords detected: 5
- Classification: "none" (confidence: 0.95)
- Final Score: 0.0
- Flagged: Spam/promotional content

---

### Layer 4: Image Classification (4 Human-Made Hazards Only - 20% Weight)

**Purpose**: Visual validation that uploaded image matches reported hazard

**Applies To ONLY**:
- Beached Aquatic Animal (whale, dolphin, sea turtle stranded on beach)
- Ship Wreck (damaged/sunken vessel visible)
- Marine Debris (garbage, plastic waste in water/beach)
- Oil Spill (black/brown discoloration in water)

**Does NOT Apply To**:
- Tsunami (dynamic event, hard to capture in photo)
- Cyclone (weather condition, not single object)
- High Waves (subjective, hard to classify from still image)
- Rip Current (invisible in photos)
- Flooded Coastline (context-dependent)

**Technology**:
- Convolutional Neural Network (CNN) - ResNet50 architecture
- Transfer learning from ImageNet
- Fine-tuned on custom coastal hazard dataset

**Classification Classes**:
1.  Beached Animal
2. Ship Wreck
3. Marine Debris
4. Oil Spill
5. Clean/Other (no hazard or different hazard)

**How It Works**:

**Step 1: Image Preprocessing**
- Resize to 224×224 pixels (standard CNN input)
- Normalize pixel values
- Apply center crop

**Step 2: Feature Extraction**
- Image passed through 50 layers of neural network
- Extracts visual features (shapes, textures, colors, patterns)
- Generates high-dimensional feature vector

**Step 3: Classification**
- Final layer maps features to 5 classes
- Softmax produces probability distribution
- Returns predicted class + confidence score

**Step 4: Validation Against Report**
- Compare predicted class with reported hazard
- Check if match or in top-2 predictions
- Generate TRUE/FALSE validation result

**Scoring**:
- **Match** (predicted = reported): Score = confidence level (e.g., 0.87)
- **No Match**: Score = max(0.0, 0.3 - confidence)
- **Clean/Other** predicted: Score = 0.0 (image doesn't show reported hazard)

**Example Scenarios**:

**Scenario 1: Beached Whale Report**
- User uploads: Photo of large marine mammal on sand
- CNN Prediction: Beached Animal (confidence: 0.92)
- Reported Hazard: Beached Aquatic Animal
- Match: YES ✓
- Score: 0.92
- Result: **VALID** - Image confirms report

**Scenario 2: Oil Spill Report with Wrong Image**
- User uploads: Photo of normal blue seawater
- CNN Prediction: Clean/Other (confidence: 0. 78)
- Reported Hazard: Oil Spill
- Match: NO ✗
- Score: 0.0
- Reason: "Image shows clean/normal conditions, not oil spill"
- Result: **INVALID** - Likely false report or wrong image uploaded

**Scenario 3: Ship Wreck Report**
- User uploads: Photo showing rusted metal structure in water
- CNN Prediction: Ship Wreck (confidence: 0.65)
- Reported Hazard: Ship Wreck
- Match: YES ✓
- Score: 0.65
- Result: **VALID** - Moderate confidence but matches report

**What Happens When Layer Doesn't Apply**:
- For Tsunami report: Image layer status = "skipped"
- Reason: "Image validation not applicable for this hazard type"
- Weight (20%) redistributed to active layers
- Full score (1.0) assigned since layer doesn't apply

**Why Only These 4 Hazards?**:
1. **Visually Identifiable**: Can be recognized in a single photo
2. **Static Objects**: Don't require video or temporal context
3. **Distinct Visual Features**: Clear visual differences from normal conditions
4. **Training Data Available**: Can collect labeled images for model training

---

### Layer 5: Reporter Credibility Score (ALL Reports - 10% Weight)

**Purpose**: Consider historical accuracy of the reporter

**Applies To**: ALL reports

**How It Works**:

**Data Points**:
- **Total Reports Submitted**: Lifetime count
- **Verified Reports**: Number of reports marked as "verified" by analysts/authorities
- **Rejected Reports**: Number marked as "rejected"
- **Current Credibility Score**: Dynamic score (0-100) in user profile

**Calculation Methods**:

**New User** (0 reports):
- Uses default credibility score (50%)
- Everyone starts with benefit of doubt
- No penalty for being new

**Experienced User** (≥1 report):
- Historical Accuracy = Verified Reports ÷ Total Reports
- Final Score = (Accuracy × 70%) + (Credibility Score × 30%)

**Example Calculations**:

**Trusted Reporter**:
- Total Reports: 20
- Verified: 18
- Rejected: 2
- Credibility Score: 85
- Calculation: (18/20 × 0.7) + (85/100 × 0.3) = 0.63 + 0.255 = **0.885** (88.5%)

**Questionable Reporter**:
- Total Reports: 10
- Verified: 3
- Rejected: 7
- Credibility Score: 30
- Calculation: (3/10 × 0.7) + (30/100 × 0.3) = 0.21 + 0.09 = **0.30** (30%)

**Scoring Impact**:
- Score ≥0.6 (60%) → Green flag (trusted)
- Score 0.4-0.6 (40-60%) → Yellow flag (neutral)
- Score <0.4 (40%) → Red flag (questionable)

**Gamification Benefits**:
- Encourages quality reporting
- Users build reputation over time
- High-credibility users get faster approval
- Low-credibility users trigger manual review

**Fairness Considerations**:
- Weight is only 10% (lowest of all layers)
- Even low-credibility users can submit valid reports
- Other layers (geofence, weather, text, image) carry more weight
- New users aren't penalized

---

### Layer 6: Composite Score Calculation (Final Decision)

**Purpose**: Combine all layer scores into single verification score

**Dynamic Weighting System**:

**Base Weights** (all layers apply):
- Geofencing: 20%
- Weather: 25%
- Text Analysis: 25%
- Image Classification: 20%
- Reporter Score: 10%

**Adjusted Weights** (some layers don't apply):

**Example 1: Tsunami Report** (Natural hazard - no image validation)
- Geofencing: 20% → 24% (redistributed)
- Weather: 25% → 30%
- Text: 25% → 30%
- Image: 20% → 0% (skipped)
- Reporter: 10% → 12%

**Example 2: Oil Spill Report** (Human-made - no weather validation)
- Geofencing: 20% → 24%
- Weather: 25% → 0% (skipped)
- Text: 25% → 30%
- Image: 20% → 24%
- Reporter: 10% → 12%

**Score Calculation Formula**:

Composite Score = (Geofence × W₁) + (Weather × W₂) + (Text × W₃) + (Image × W₄) + (Reporter × W₅)

Where W₁... W₅ are dynamic weights (sum = 1.0), multiplied by 100 for percentage

**Decision Thresholds**:

- **≥75%** → Auto-Approved (Status: "verified")
  - High confidence in report validity
  - Directly visible to public
  - May create ticket if authority deems necessary

- **40-75%** → Manual Review Required (Status: "needs_manual_review")
  - Uncertain case, needs human judgment
  - Routed to analyst queue
  - Analyst examines all layer details and makes decision

- **<40%** → Recommended Rejection (Status: "rejected")
  - Low confidence, likely false report
  - Still goes to analyst for final confirmation
  - Can be appealed by reporter

- **Geofence Fail** → Auto-Rejected (Status: "auto_rejected")
  - Immediate rejection, no further processing
  - Outside valid coastal zone
  - Cannot be appealed (objective geographic fact)

**Full Workflow Example**:

**Report: "Oil Spill Near Mumbai Port"**

**Layer 1 - Geofencing**:
- Location: 19.08°N, 72.88°E (Mumbai Harbor)
- Distance to coast: 2km
- Status: PASS ✓
- Score: 1.0
- Weight: 24% (adjusted)

**Layer 2 - Weather**:
- Hazard Type: Oil Spill (human-made)
- Status: SKIPPED
- Score: 1.0 (no penalty)
- Weight: 0%

**Layer 3 - Text Analysis**:
- Description: "Black thick oil covering water surface near port, strong petroleum smell"
- Vector Match: "Oil spill spotted near Kochi port" (similarity: 0.81)
- Predicted Type: Oil Spill (confidence: 0.88)
- Panic Level: 0.2 (calm, descriptive)
- Status: PASS ✓
- Score: 0.84
- Weight: 30% (adjusted)

**Layer 4 - Image Classification**:
- CNN Prediction: Oil Spill (confidence: 0.76)
- Matches Report: YES ✓
- Status: PASS ✓
- Score: 0.76
- Weight: 24% (adjusted)

**Layer 5 - Reporter Score**:
- User History: 8 reports, 7 verified
- Accuracy: 87. 5%
- Credibility: 78
- Status: PASS ✓
- Score: 0.85
- Weight: 12% (adjusted)

**Composite Score Calculation**:
= (1.0 × 24) + (0.84 × 30) + (0.76 × 24) + (0.85 × 12)
= 24 + 25.2 + 18.24 + 10.2
= **77.64%**

**Final Decision**: **AUTO-APPROVED** ✓
- Score >75% threshold
- All applicable layers passed
- High-quality report with supporting evidence
- Status: "verified"
- Visible to public immediately

---

## 🎫 TICKETING SYSTEM ARCHITECTURE

### System Purpose

The ticketing system enables **structured three-way communication** between Reporter (Citizen), Analyst, and Authority after a hazard report has been verified and approved. It serves as:

1. **Communication Hub**: Real-time threaded conversations
2. **Accountability Tool**: Track who said what, when, and why
3. **Resolution Tracker**: Monitor progress from report to resolution
4. **Knowledge Base**: Historical record of how similar incidents were handled

---

### When Tickets Are Created

**Trigger Conditions**:
- Hazard report must be **verified** (status = "verified")
- Authority must **approve** the report for action
- Only authorities have permission to create tickets

**Why This Flow**:
- Prevents ticket spam from unverified reports
- Ensures only actionable incidents get tickets
- Maintains separation between verification (automated) and action (human decision)

**Workflow**:
1.  Citizen submits report → Verification pipeline runs
2. Report auto-approved (score >75%) OR analyst manually approves
3. Authority reviews verified report
4. Authority decides: "This needs action/communication" → Creates ticket
5. Ticket becomes active communication channel

---

### Three-Way Communication Model

**Participant Roles**:

**1. Reporter (Citizen)**:
- **Can View**: All non-internal messages
- **Can Send**: Questions, updates, clarifications, photos
- **Can Do**: Request escalation, provide feedback
- **Cannot See**: Internal messages between analyst and authority
- **Example Messages**:
  - "The oil spill has spread to the north beach area"
  - "When will cleanup start?"
  - "I can provide more photos if needed"

**2.  Analyst (Verification Specialist)**:
- **Can View**: All messages including internal
- **Can Send**: Updates, requests for info, analysis notes, internal notes
- **Can Do**: Assign ticket, change priority, mark resolved
- **Responsibilities**: 
  - Verify additional information
  - Coordinate between reporter and authority
  - Provide technical analysis
- **Example Messages**:
  - "Analysis confirms oil spill is crude oil, likely from tanker leak"
  - [INTERNAL] "Need Coast Guard involvement for offshore containment"
  - "Reporter, can you check if wildlife has been affected?"

**3.  Authority (Decision Maker)**:
- **Can View**: All messages including internal
- **Can Send**: Directives, action plans, official statements, internal coordination
- **Can Do**: Assign resources, escalate, resolve ticket, close ticket
- **Responsibilities**:
  - Issue directives to response teams
  - Coordinate with external agencies
  - Make policy decisions
  - Approve resolutions
- **Example Messages**:
  - "Deploying oil spill response team to location within 2 hours"
  - "Coast Guard alerted, containment booms being deployed"
  - [INTERNAL] "Need ₹5L budget approval from headquarters"
  - "Situation contained.  Cleanup will take 3-4 days."

**Message Types**:

1. **Text Messages**: Regular conversation
2. **Status Updates**: "Ticket assigned to Marine Analyst Team"
3. **Assignments**: "Ticket assigned to Dr.  Sharma (Authority)"
4. **Escalations**: "Escalated to Regional Director - requires immediate attention"
5. **Resolution Notes**: "Oil spill contained, cleanup 80% complete"
6. **System Notes**: Automatic timestamps, status changes

**Internal vs. External Messages**:

**Internal** (Analyst ↔ Authority only):
- Budget discussions
- Sensitive operational details
- Personnel assignments
- Political considerations
- Legal concerns

**External** (Visible to Reporter):
- Action updates
- Timeline estimates
- Information requests
- Public statements
- Resolution status

---

### Ticket Lifecycle States

**1.  OPEN**
- Just created by authority
- Awaiting assignment
- No analyst assigned yet
- Reporter can already send messages

**2. ASSIGNED**
- Analyst assigned to ticket
- Not yet actively worked on
- In analyst's queue

**3. IN_PROGRESS**
- Analyst actively working
- Investigation ongoing
- Multiple messages exchanged
- Action being taken

**4. AWAITING_RESPONSE**
- Waiting for information from reporter
- Or waiting for external agency response
- Temporary pause

**5. ESCALATED**
- Moved to higher authority
- Priority automatically upgraded to CRITICAL
- Senior management involved
- Expedited handling

**6. RESOLVED**
- Issue addressed
- Resolution notes documented
- Actions taken recorded
- Awaiting final closure

**7. CLOSED**
- Completely finished
- Reporter satisfaction recorded
- No further action needed
- Archived for reference

**8. REOPENED**
- Previously resolved but issue recurred
- Or new information emerged
- Returns to IN_PROGRESS state

---

### Ticket Priority System

**Priority Levels**:

**EMERGENCY**:
- Life-threatening situation
- Massive environmental disaster
- Response Due: 1 hour
- Resolution Due: 4 hours
- Examples: Tsunami warning, major ship collision with casualties

**CRITICAL**:
- Severe threat to life/environment
- Large scale impact
- Response Due: 2 hours
- Resolution Due: 8 hours
- Examples: Major oil spill, cyclone approaching populated area

**HIGH**:
- Significant threat
- Moderate scale impact
- Response Due: 4 hours
- Resolution Due: 1 day
- Examples: Beached whale, ship grounding, localized oil leak

**MEDIUM**:
- Important but not immediately dangerous
- Limited impact area
- Response Due: 8 hours
- Resolution Due: 2 days
- Examples: Marine debris accumulation, minor pollution

**LOW**:
- Non-urgent monitoring needed
- Informational
- Response Due: 1 day
- Resolution Due: 5 days
- Examples: Routine observations, follow-up checks

**SLA (Service Level Agreement) Tracking**:
- System automatically calculates deadlines based on priority
- Visual indicators show time remaining
- Alerts sent when deadlines approaching
- Escalation triggered if SLA breached

---

### Real-Time Features

**1. Message Threading**
- All messages in chronological order
- Threaded conversations (can reply to specific messages)
- Timestamps in user's local timezone
- "Typing..." indicators when someone is composing

**2. Read Receipts**
- "Delivered" when message sent
- "Read by [Name]" when opened
- Individual read timestamps per participant
- Unread count badge on ticket list

**3. Presence Indicators**
- "Online" - Active in last 5 minutes
- "Away" - Active 5-30 minutes ago
- "Offline" - Last seen >30 minutes ago
- "Last seen: [timestamp]"

**4. Real-Time Updates**
- WebSocket connection for instant message delivery
- No page refresh needed
- Push notifications for new messages
- Badge updates automatically

**5. Attachments**
- Photos: Before/after images, evidence photos
- Documents: Reports, permits, certificates
- Videos: Situation footage, drone surveys
- File size limit: 10MB per file
- Automatic thumbnail generation for images

**6. Emoji Reactions**
- Quick reactions to messages (👍, ❤️, ⚠️, ✅)
- Multiple users can react
- Shows who reacted with what

---

### Activity Logging & Audit Trail

**What Gets Logged**:
- Every message sent (who, what, when)
- Status changes (open → assigned → resolved)
- Priority changes (medium → critical)
- Assignments (analyst/authority changes)
- Escalations (reason, to whom)
- File uploads (who uploaded what)
- Ticket creation/closure
- Resolution documentation

**Audit Log Entry Structure**:
- **Action**: What happened
- **Performed By**: User ID + name
- **Timestamp**: Exact time (UTC + local)
- **Details**: Additional context (JSON object)
- **IP Address**: For security
- **Device Info**: Browser, OS

**Use Cases**:
- Accountability: Who made what decision
- Compliance: Regulatory reporting
- Performance: Response time analysis
- Training: Review how tickets were handled
- Dispute Resolution: Exact record of communication

**Example Audit Trail**:

```
[2025-01-20 10:15:30] ticket_created
- By: Authority_Mumbai_01 (Priya Sharma)
- Report: RPT-20250120-ABC123
- Priority: CRITICAL

[2025-01-20 10:17:45] ticket_assigned
- By: Authority_Mumbai_01
- Assigned To: Analyst_Marine_05 (Dr. Ravi Kumar)

[2025-01-20 10:22:10] message_added
- By: Analyst_Marine_05
- Type: TEXT
- Internal: NO

[2025-01-20 11:05:33] priority_changed
- By: Analyst_Marine_05
- From: CRITICAL → EMERGENCY
- Reason: Oil spill spreading rapidly

[2025-01-20 11:10:22] ticket_escalated
- By: Analyst_Marine_05
- To: Regional_Director_West
- Reason: Requires Coast Guard coordination

[2025-01-20 14:30:15] status_changed
- By: Authority_Regional_Director
- From: ESCALATED → IN_PROGRESS
- Notes: Coast Guard deployed, containment booms active

[2025-01-21 09:15:00] ticket_resolved
- By: Authority_Mumbai_01
- Resolution: Oil spill contained, cleanup 90% complete
- Actions Taken: [1] Coast Guard deployment, [2] Oil boom placement... 

[2025-01-21 16:00:00] ticket_closed
- By: System
- Reporter Satisfaction: 5/5
```

---

### Escalation Mechanism

**When to Escalate**:
- Situation worsening beyond initial assessment
- Resources needed exceed local authority
- SLA deadlines missed
- Multiple jurisdictions involved
- Political/media attention
- Reporter requests escalation

**Escalation Process**:

**Step 1: Request Escalation**
- Analyst or Reporter clicks "Escalate"
- Provides reason (required)
- Suggests escalation target (optional)

**Step 2: Automatic Actions**
- Priority upgraded to CRITICAL
- Status changed to ESCALATED
- New SLA deadlines calculated (more aggressive)
- Senior authorities notified immediately

**Step 3: Review & Assignment**
- Higher authority reviews escalation reason
- Decides to accept or send back
- If accepted, takes ownership of ticket
- Original analyst remains as support

**Step 4: Escalated Handling**
- Higher authority coordinates response
- Can assign additional analysts
- Can create sub-tickets for specific tasks
- Original reporter kept informed

**Example Escalation Flow**:

**Initial Report**: Minor oil sheen near fishing harbor (Priority: MEDIUM)
↓
**Hour 2**: Oil spreading faster than expected
↓
**Hour 4**: Analyst escalates: "Oil source identified as underwater pipeline leak, require marine engineers"
↓
**Hour 4.5**: Escalated to Port Authority Director
↓
**Hour 5**: Additional resources mobilized, Coast Guard notified
↓
**Hour 6**: Multi-agency response in progress

**Escalation Triggers**:
- Manual: Analyst/reporter requests
- Automatic: SLA breach (response/resolution deadline missed)
- Priority-based: EMERGENCY tickets auto-notify senior management
- Geographic: Cross-jurisdiction incidents auto-escalate to regional authority

---

### Reporter Feedback & Satisfaction

**When Collected**:
- After ticket marked RESOLVED
- Before ticket closed
- Optional but encouraged

**Feedback Components**:

**1. Satisfaction Rating** (1-5 stars):
- 5 ⭐⭐⭐⭐⭐ - Excellent, exceeded expectations
- 4 ⭐⭐⭐⭐ - Good, satisfied with response
- 3 ⭐⭐⭐ - Acceptable, met basic expectations
- 2 ⭐⭐ - Poor, delayed or inadequate response
- 1 ⭐ - Very poor, no effective action

**2. Text Feedback** (optional):
- What went well? 
- What could be improved? 
- Additional comments

**3. Specific Aspects** (optional checkboxes):
- [ ] Response time was good
- [ ] Communication was clear
- [ ] Issue was resolved effectively
- [ ] Analyst was helpful
- [ ] Authority took appropriate action

**Use of Feedback**:
- Analyst performance evaluation
- System improvement identification
- Training needs assessment
- Public transparency metrics
- Success story highlights (with permission)

**Feedback Dashboard** (For Authorities):
- Average satisfaction: 4.2/5. 0
- Response time trend: Improving ↗️
- Resolution rate: 87%
- Top complaints: "Slow initial response"
- Top praises: "Clear communication"

---

### Ticket Analytics & Metrics

**Performance Metrics**:

**1. Response Time**:
- Time from ticket creation to first analyst/authority message
- Target: Within SLA deadline
- Tracked per priority level
- Aggregated by region/department

**2. Resolution Time**:
- Time from creation to resolved status
- Average: 18 hours (target: <24 for MEDIUM priority)
- Trend analysis: Week-over-week comparison

**3. Message Volume**:
- Average messages per ticket: 8. 5
- Messages by role: Reporter (45%), Analyst (35%), Authority (20%)
- Peak messaging hours: 9 AM - 12 PM

**4. Escalation Rate**:
- Percentage of tickets escalated: 12%
- Common escalation reasons: Resource requirements (40%), Urgency (35%), Cross-jurisdiction (25%)

**5. Satisfaction Trends**:
- Overall satisfaction: 4.3/5.0
- Improving over last 3 months
- Correlation: Faster response = higher satisfaction

**6.  Ticket Volume by Type**:
- Oil Spill: 25%
- Marine Debris: 20%
- Ship Incidents: 18%
- Natural Hazards: 15%
- Wildlife: 12%
- Other: 10%

**Dashboard Views**:

**For Citizens**:
- My tickets status
- Average response time for my reports
- My satisfaction history

**For Analysts**:
- Tickets assigned to me
- My performance metrics
- Pending tasks/deadlines

**For Authorities**:
- Department-wide statistics
- Active critical tickets
- Resource allocation overview
- Trend analysis

**For Admins**:
- System-wide health
- User activity
- Performance benchmarks
- Comparative analysis (region vs region)

---

### Related Tickets & Cross-Referencing

**Use Cases**:
- Multiple reports of same incident
- Follow-up on previous incident
- Related hazards (e.g., cyclone → flooding)

**Linking Tickets**:

**Duplicate Detection**:
- Same location (within 1km) + similar hazard type + within 2 hours
- Auto-suggest: "This might be related to Ticket TKT-20250120-ABC123"
- Authority can merge or link

**Parent-Child Relationships**:
- Parent: Major oil spill incident
- Child 1: Oil containment sub-task
- Child 2: Wildlife rescue sub-task
- Child 3: Cleanup coordination sub-task

**Sequential Incidents**:
- Ticket A: Oil tanker grounding (RESOLVED)
- Ticket B: Oil leakage from same tanker (LINKED to A)
- Historical context immediately available

**Benefits**:
- Avoid duplicate effort
- Learn from previous handling
- Track long-term incidents
- Pattern identification

---

### Notification System Integration

**Notification Triggers**:

**For Reporter**:
- Ticket created for your report
- New message from analyst/authority
- Status changed (assigned, in progress, resolved)
- Request for more information
- Ticket resolved/closed

**For Analyst**:
- Ticket assigned to you
- New message in your tickets
- SLA deadline approaching
- Escalation from reporter
- New report in your jurisdiction

**For Authority**:
- Critical ticket created
- Ticket escalated to you
- Resolution approval needed
- Citizen feedback received

**Notification Channels**:

**1. In-App Notifications**:
- Bell icon with unread count
- Dropdown list of recent notifications
- Click to open relevant ticket

**2. Email Notifications**:
- Immediate for CRITICAL/EMERGENCY
- Batched digest for MEDIUM/LOW
- Customizable frequency

**3. SMS Notifications** (Optional):
- Only for CRITICAL/EMERGENCY
- Opt-in required
- Character-limited summary

**4. Push Notifications** (Mobile App):
- Real-time on mobile device
- Works even when app closed
- Actionable: "Reply" button opens chat

**5. WebSocket Push**:
- Real-time in browser
- No polling needed
- Instant message delivery

**Notification Preferences**:
- Users can customize per channel
- Quiet hours: "Don't notify 10 PM - 7 AM"
- Priority filtering: "Only notify for HIGH+"
- Digest mode: "Batch notifications every 2 hours"

---

### Security & Data Privacy

**Access Control**:

**Principle of Least Privilege**:
- Users only see tickets they're involved in
- Reporter: Only their own tickets
- Analyst: Only assigned tickets
- Authority: Tickets in jurisdiction + all escalated
- Admin: All tickets

**Data Encryption**:
- Messages encrypted in transit (TLS 1.3)
- Sensitive attachments encrypted at rest
- Message content not indexed for search (privacy)

**Audit Logging**:
- Every access logged (who viewed what, when)
- IP address tracking
- Suspicious activity alerts (e.g., rapid access of many tickets)

**Data Retention**:
- Active tickets: Retained indefinitely
- Closed tickets: Archived after 90 days
- Archived tickets: Moved to cold storage, searchable
- Deleted after 7 years (compliance requirement)

**GDPR/Privacy Compliance**:
- Reporter can request data export (JSON format)
- Reporter can request account deletion (tickets anonymized)
- Personal info (phone, email) visible only to authorities
- Public stats don't reveal individual identities

---

### Mobile Responsiveness

**Mobile-First Design**:
- 70% of reporters use mobile devices
- Touch-optimized interfaces
- Swipe gestures for navigation
- Voice input for messages

**Offline Capabilities**:
- Draft messages saved locally
- Auto-sync when connection restored
- Offline indicator visible
- Queued actions: "Will send when online"

**Mobile-Specific Features**:
- Quick reply templates ("Okay", "On my way", "Need more time")
- Voice messages (audio recording)
- Photo capture directly from camera
- Location sharing (current location button)

---

### Integration with Main System

**Hazard Report → Ticket Flow**:
1.  Citizen submits report via frontend
2.  Verification pipeline processes report
3. Composite score calculated
4. If verified, report visible to authorities
5. Authority reviews and decides to create ticket
6. Ticket automatically linked to original report
7. Report data pre-fills ticket (hazard type, location, description)
8. Reporter automatically added as participant

**Data Synchronization**:
- Report updates reflected in ticket
- Ticket status updates report metadata
- Bidirectional linking maintained

**Unified Dashboard**:
- Citizens see: My Reports + My Tickets (tab view)
- Analysts see: Pending Verifications + My Tickets
- Authorities see: Verified Reports + Active Tickets

---

## 📊 COMPLETE USER JOURNEY EXAMPLES

### Journey 1: Auto-Approved Report with Ticket

**Day 1, 9:00 AM** - Report Submission
- **Actor**: Fisherman Raj from Mumbai
- **Action**: Reports oil spill via mobile app
  - Captures photo of black water
  - Auto-detects location (Mumbai Harbor)
  - Describes: "Black oil covering 50m² area near Sassoon Dock"
  - Submits report

**Day 1, 9:00:15 AM** - Verification Pipeline
- **Layer 1 - Geofence**: Mumbai Harbor (2km from coast) → PASS ✓
- **Layer 2 - Weather**: Oil Spill (human-made) → SKIPPED
- **Layer 3 - Text**: Vector match "oil spill", confidence 0.89 → PASS ✓
- **Layer 4 - Image**: CNN detects oil spill, confidence 0.82 → PASS ✓
- **Layer 5 - Reporter**: Raj has 5 previous verified reports, score 0.92 → PASS ✓
- **Composite Score**: 84. 2%
- **Decision**: AUTO-APPROVED ✓

**Day 1, 9:01 AM** - Notification
- Raj receives: "Your report has been verified!  Thank you for your vigilance."

**Day 1, 10:30 AM** - Authority Review
- **Actor**: Mumbai Port Authority Officer, Priya
- **Action**: Reviews verified reports dashboard
  - Sees Raj's oil spill report (high score, credible reporter)
  - Decides action needed
  - Clicks "Create Ticket"
  - Assigns to Marine Analyst Dr. Kumar
  - Priority: HIGH

**Day 1, 10:31 AM** - Ticket Created
- **Ticket ID**: TKT-20250120-MUM001
- **Notifications sent**:
  - Raj: "A ticket has been created for your report.  You can track progress."
  - Dr. Kumar: "New HIGH priority ticket assigned to you"

**Day 1, 11:00 AM** - Analyst Investigation
- **Actor**: Dr. Kumar (Analyst)
- **Messages**:
  - To Raj: "Thank you for the report. Can you tell me if you noticed any ships nearby?"
  - To Priya [INTERNAL]: "Checking satellite imagery for source identification"

**Day 1, 11:15 AM** - Reporter Response
- **Actor**: Raj
- **Message**: "Yes, tanker ship 'MV Sea Prince' was anchored 200m away.  Left 30 minutes after I noticed oil."

**Day 1, 11:45 AM** - Analyst Update
- **Actor**: Dr. Kumar
- **Messages**:
  - To Priya [INTERNAL]: "Identified source: MV Sea Prince, IMO 9876543.  Checking with Port Control for vessel details."
  - To Raj: "We've identified the source vessel. Coast Guard has been alerted."

**Day 1, 14:30 PM** - Authority Action
- **Actor**: Priya (Authority)
- **Message** (visible to Raj): "Coast Guard response team deployed. Oil containment booms being placed. Cleanup will commence within 2 hours."
- **Status**: IN_PROGRESS

**Day 1, 17:00 PM** - Progress Update
- **Actor**: Dr.  Kumar
- **Message**: "Cleanup 30% complete. Oil spread contained. No wildlife affected so far.  Will monitor overnight."

**Day 2, 10:00 AM** - Resolution
- **Actor**: Priya
- **Action**: Marks ticket as RESOLVED
- **Resolution Notes**: "Oil spill successfully contained and cleaned.  Approximately 200L crude oil recovered. Ship owner identified and penalized.  No environmental damage."
- **Message to Raj**: "Situation fully resolved. Thank you for your prompt reporting, which enabled quick action!"

**Day 2, 10:30 AM** - Feedback Request
- **Actor**: Raj
- **Action**: Receives satisfaction survey
  - Rating: 5/5 stars ⭐⭐⭐⭐⭐
  - Comment: "Very impressed with quick response.  Kept me informed throughout.  Thank you!"

**Day 2, 11:00 AM** - Ticket Closed
- **System Action**: Auto-closed after positive feedback
- **Raj's Credibility**: Increased from 92% to 95%
- **Report Count**: 6 verified, 0 rejected

---

### Journey 2: Manual Review with Escalation

**Day 1, 6:30 AM** - Report Submission
- **Actor**: Tourist Maya from Chennai
- **Action**: Reports "Beached Whale" at Marina Beach
  - Uploads blurry photo (taken from distance)
  - Location detected correctly
  - Description: "Big fish on beach, not moving"

**Day 1, 6:30:15 AM** - Verification Pipeline
- **Layer 1 - Geofence**: Marina Beach (0.5km from coast) → PASS ✓
- **Layer 2 - Weather**: Beached Animal (not natural hazard) → SKIPPED
- **Layer 3 - Text**: Vector match uncertain, "big fish" vs "beached whale" → Score 0.52
- **Layer 4 - Image**: CNN classification unclear (blurry), confidence 0.48 → Score 0.48
- **Layer 5 - Reporter**: Maya is new user (first report), score 0.50 → NEUTRAL
- **Composite Score**: 56.3%
- **Decision**: NEEDS MANUAL REVIEW

**Day 1, 6:31 AM** - Notification
- Maya receives: "Your report is under review by our analysts. We'll update you soon."

**Day 1, 9:00 AM** - Analyst Review
- **Actor**: Wildlife Analyst Arjun
- **Action**: Reviews report in queue
  - Examines blurry photo: "Could be whale, dolphin, or large debris"
  - Checks Marina Beach webcam (public): Sees crowd gathering
  - Checks social media: Multiple posts about "whale on beach"
  - Decision: VERIFIED (cross-reference confirms)
  - Adds note: "Confirmed via multiple sources. Appears to be pilot whale."

**Day 1, 9:15 AM** - Authority Notification
- **Actor**: Chennai Forest Department (Wildlife Authority), Officer Meena
- **Action**: Sees verified beached whale report (CRITICAL for wildlife)
  - Creates ticket immediately
  - Priority: CRITICAL (endangered species)
  - Assigns to Arjun (already investigated)

**Day 1, 9:20 AM** - Ticket Active
- **Ticket ID**: TKT-20250120-CHN012
- **Message** (Meena to Maya): "Thank you for reporting!  This is a pilot whale. Our rescue team is en route.  ETA 30 minutes."

**Day 1, 9:45 AM** - Situation Worsens
- **Actor**: Maya
- **Message**: "Whale looks distressed. Water level dropping. Sun getting hot. Many people touching it!"

**Day 1, 9:50 AM** - Escalation
- **Actor**: Arjun
- **Action**: Escalates ticket
  - Reason: "Whale survival critical, public safety concern, need police + fire brigade for water spraying"
  - Escalate to: Regional Wildlife Director

**Day 1, 9:52 AM** - Auto-Actions
- Priority: CRITICAL → EMERGENCY
- Status: ESCALATED
- Regional Director alerted via SMS + email + push notification

**Day 1, 10:05 AM** - Senior Authority Response
- **Actor**: Regional Wildlife Director, Dr. Patel
- **Takes ownership**
- **Messages**:
  - To Maya: "Help is on the way. Please keep public away from whale.  Do NOT let anyone touch it."
  - To Arjun [INTERNAL]: "Coordinate with police for crowd control. Fire brigade for water.  Marine ambulance dispatched from port."
  - To Meena [INTERNAL]: "Activate emergency protocol WL-001. Contact nearby aquarium for holding facility."

**Day 1, 10:30 AM** - Multi-Agency Response
- **Actors**: Police, Fire Brigade, Marine Rescue Team, Veterinarians
- **Updates**:
  - Arjun: "Rescue team on site. Whale being kept wet.  Crowd controlled."
  - Arjun: "Veterinary assessment: Young pilot whale, 3m, dehydrated but alive. Preparing transport to sea."

**Day 1, 11:45 AM** - Success Update
- **Actor**: Dr.  Patel
- **Message** (to Maya): "GOOD NEWS! Whale successfully transported and released 5km offshore in deeper water. Swimming normally.  Thank you for your quick reporting - you saved a life today!  🐋"

**Day 1, 12:00 PM** - Media Coverage
- **News**: "Tourist's quick thinking saves beached whale in Chennai"
- Maya's name (with permission) featured in news

**Day 1, 14:00 PM** - Resolution
- **Actor**: Dr. Patel
- **Status**: RESOLVED
- **Resolution Notes**: "Pilot whale successfully rescued and released. Animal appeared healthy upon release. Public awareness campaign initiated to educate about proper response to beached marine animals.  Tourist Maya awarded 'Wildlife Guardian' certificate."

**Day 1, 14:30 PM** - Feedback
- **Actor**: Maya
- **Rating**: 5/5 stars
- **Comment**: "Incredible response! I just wanted to help and the team did amazing work. Proud to have contributed!"
- **Maya's Credibility**: New user → 85% (reward for critical report)

---

### Journey 3: False Report - Spam Detection

**Day 1, 2:00 PM** - Suspicious Submission
- **Actor**: Unknown user "PromoUser123"
- **Action**: Submits "Oil Spill" report
  - Location: Random beach coordinates
  - Photo: Stock image from internet (not original)
  - Description: "URGENT! !! OIL EVERYWHERE! !! Click link for details www.scamsite.com Buy cleanup products NOW!!  50% discount!! !"

**Day 1, 2:00:10 PM** - Verification Pipeline
- **Layer 1 - Geofence**: Valid coastal location → PASS ✓
- **Layer 2 - Weather**: Oil Spill (human-made) → SKIPPED
- **Layer 3 - Text Analysis**:
  - Spam keywords detected: "Click link", "Buy", "discount"
  - Panic level: 0.95 (excessive caps, exclamation)
  - URL detected: External link (red flag)
  - Vector match: "none" (promotional content)
  - Score: 0.0 ❌
- **Layer 4 - Image**: 
  - Reverse image search: Stock photo found on 15 websites
  - Not original capture
  - Score: 0.0 ❌
- **Layer 5 - Reporter**: New user, no history → Score: 0.5
- **Composite Score**: 18.2%
- **Decision**: LIKELY SPAM - REJECTED

**Day 1, 2:00:30 PM** - Analyst Review
- **Actor**: Fraud Detection Analyst
- **Action**: Flags account
  - Checks IP: VPN/proxy detected
  - Checks device: Automated submission pattern
  - Decision: SPAM CONFIRMED
  - Account suspended

**Day 1, 2:01 PM** - Notification
- "Your report could not be verified. Please contact support if you believe this is an error."
- No ticket created
- Report not visible publicly

**System Action**: Account flagged, future reports auto-rejected

---

### Journey 4: Outside Geofence - Auto-Rejection

**Day 1, 11:00 AM** - Invalid Location
- **Actor**: Confused user "Inland User"
- **Action**: Submits "High Waves" report
  - Location: Delhi (28. 61°N, 77.20°E) - 200km inland
  - Photo: Actually shows flooded street (monsoon rain)
  - Description: "Huge water waves in my street!"

**Day 1, 11:00:05 AM** - Verification Pipeline
- **Layer 1 - Geofence**:
  - Nearest coastal point: 237km away
  - Inland limit: 20km
  - Status: OUTSIDE ZONE ❌
  - Score: 0.0
  - **AUTO-REJECT TRIGGERED**

**Day 1, 11:00:10 AM** - Immediate Response
- **Pipeline STOPPED** (no further layers processed)
- **Status**: AUTO-REJECTED
- **Notification**: "Report rejected: Your location is outside the valid coastal zone (20km inland / 30km offshore). This system is for coastal hazards only.  For inland flooding, please contact local municipal authorities."

**Result**:
- No analyst review needed
- No resources wasted
- Clear explanation provided to user
- User educated about system scope

---

## 🔒 SECURITY & PERMISSIONS MATRIX

### Role-Based Access Control (RBAC)

| **Action** | **Citizen** | **Analyst** | **Authority** | **Admin** |
|------------|------------|------------|--------------|-----------|
| Submit hazard report | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| View own reports | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| View all reports | ❌ No | ⚠️ Assigned only | ⚠️ Jurisdiction only | ✅ Yes |
| View verification scores | ✅ Own only | ✅ Assigned only | ✅ All verified | ✅ Yes |
| Create tickets | ❌ No | ❌ No | ✅ Yes | ✅ Yes |
| View tickets | ⚠️ Own only | ⚠️ Assigned only | ⚠️ Jurisdiction | ✅ Yes |
| Send messages | ⚠️ In own tickets | ⚠️ In assigned tickets | ⚠️ In jurisdiction | ✅ Yes |
| Send internal messages | ❌ No | ✅ Yes | ✅ Yes | ✅ Yes |
| Assign tickets | ❌ No | ⚠️ Limited | ✅ Yes | ✅ Yes |
| Change priority | ❌ No | ⚠️ Limited | ✅ Yes | ✅ Yes |
| Resolve tickets | ❌ No | ⚠️ Limited | ✅ Yes | ✅ Yes |
| Close tickets | ❌ No | ❌ No | ✅ Yes | ✅ Yes |
| Escalate tickets | ⚠️ Request only | ✅ Yes | ✅ Yes | ✅ Yes |
| View internal messages | ❌ No | ✅ Yes | ✅ Yes | ✅ Yes |
| Export data | ⚠️ Own data | ⚠️ Assigned data | ⚠️ Jurisdiction data | ✅ All data |
| View analytics | ⚠️ Own stats | ⚠️ Team stats | ⚠️ Dept stats | ✅ All stats |

**Legend**:
- ✅ Yes: Full access
- ❌ No: No access
- ⚠️: Conditional access (see description)

---

## 📈 SYSTEM SCALABILITY & PERFORMANCE

### Expected Load

**Daily Metrics** (at full deployment):
- **Reports Submitted**: 500-1000/day
- **Auto-Approved**: 350-450/day (65%)
- **Manual Review**: 150-200/day (25%)
- **Auto-Rejected**: 50-100/day (10%)
- **Tickets Created**: 100-150/day
- **Messages Sent**: 1500-2500/day
- **Concurrent Users**: 500-800 peak hours

### Performance Targets

| **Metric** | **Target** | **Critical Threshold** |
|------------|-----------|----------------------|
| Verification Pipeline | <5 seconds | <10 seconds |
| Geofence Check | <200ms | <500ms |
| Weather API Call | <2 seconds | <5 seconds |
| Text Analysis (VectorDB) | <1 second | <3 seconds |
| Image Classification | <2 seconds | <5 seconds |
| Composite Score Calculation | <100ms | <500ms |
| Message Delivery | <500ms | <2 seconds |
| Real-time Update (WebSocket) | <100ms | <500ms |
| Database Query (indexed) | <50ms | <200ms |
| Page Load Time | <2 seconds | <5 seconds |

### Optimization Strategies

**1. Database Optimization**:
- Indexed fields: ticket_id, report_id, user_id, status, priority, created_at
- Geospatial index on location (2dsphere)
- Compound indexes for common queries
- Archive old tickets (>90 days) to separate collection

**2. Caching Strategy**:
- Coastal reference points: Cached in memory (rarely changes)
- User profiles: Redis cache (5 min TTL)
- Vector embeddings: Pre-computed and cached
- Weather data: Cached (5 min TTL, shared across nearby locations)

**3. Async Processing**:
- Verification layers run in parallel (not sequential)
- External API calls (weather, marine, USGS) use async/await
- Message delivery uses background queue
- Notifications sent asynchronously

**4. CDN & Static Assets**:
- Images served via CDN
- Frontend assets (JS, CSS) cached
- API responses (read-only) cached at edge

**5. Load Balancing**:
- Multiple backend instances behind load balancer
- Database read replicas for queries
- Write operations to primary only

---

## 🚀 DEPLOYMENT CONSIDERATIONS

### Infrastructure Requirements

**Backend Servers**:
- **Production**: 4 servers (2 active, 2 standby)
- **Staging**: 2 servers
- **CPU**: 4 cores minimum per server
- **RAM**: 16GB minimum per server
- **Storage**: 500GB SSD per server

**Database**:
- **MongoDB Atlas**: M30 tier or higher
- **Cluster**: 3-node replica set
- **Backups**: Automated daily, retained 30 days

**Caching**:
- **Redis**: 8GB memory
- **Cluster**: 2-node for redundancy

**File Storage**:
- **S3 or equivalent**: 1TB initial
- **CDN**: CloudFlare or AWS CloudFront

### Environment Variables

**Critical Configuration**:
- `SECRET_KEY`: Application secret (32+ chars)
- `JWT_SECRET_KEY`: Token signing key (32+ chars)
- `MONGODB_URI`: Database connection string
- `REDIS_HOST`, `REDIS_PORT`: Cache configuration
- `WEATHER_API_KEY`: Weather service API key
- `MARINE_API_KEY`: Marine/tide service API key (optional)
- `SMTP_*`: Email notification settings
- `FCM_KEY`: Push notification key
- `FRONTEND_URL`: CORS allowed origin

### Monitoring & Alerts

**Health Checks**:
- `/health` endpoint: Overall system health
- `/health/db`: Database connectivity
- `/health/redis`: Cache connectivity
- `/health/apis`: External API status

**Alert Triggers**:
- **Critical**: API response time >5s
- **Warning**: API response time >2s
- **Critical**: Error rate >5%
- **Warning**: Error rate >1%
- **Critical**: Database connection failure
- **Warning**: Cache miss rate >50%

**Monitoring Dashboards**:
- System metrics: CPU, RAM, disk usage
- Application metrics: Request rate, response time, error rate
- Business metrics: Reports/day, approval rate, ticket volume
- User metrics: Active users, session duration

---

## 📚 FUTURE ENHANCEMENTS

### Phase 2 Features (Next 3-6 Months)

**1. AI Improvements**:
- Train custom image classification model on Indian coastal hazards
- Multi-language text analysis (Hindi, Tamil, Bengali support)
- Automated hazard severity prediction
- Duplicate report detection using AI

**2. Advanced Ticketing**:
- Video calls between participants (for complex coordination)
- Automated status updates from IoT sensors
- Integration with emergency response systems (108, Coast Guard)
- SMS-based ticket updates (for users without smartphones)

**3. Public Features**:
- Public map of verified hazards (privacy-preserving)
- Hazard alert subscriptions (by location/type)
- Community reporting statistics
- Educational content about hazard types

**4. Analytics**:
- Predictive modeling: "Cyclone likely in 48 hours based on patterns"
- Hotspot identification: "This area has 5x more oil spills"
- Seasonal trend analysis
- Reporter leaderboard (gamification)

### Phase 3 Features (6-12 Months)

**1. Mobile Apps**:
- Native iOS and Android apps
- Offline report drafting
- Background location tracking (opt-in)
- Camera integration with auto-focus on hazards

**2. IoT Integration**:
- Weather stations auto-create reports
- Coastal cameras with AI detection
- Buoy sensors for wave/oil detection
- Drone footage integration

**3. Inter-Agency**:
- National hazard database (share with IMD, INCOIS, Coast Guard)
- Cross-border coordination (Sri Lanka, Maldives)
- International standards compliance (ISO, UN)

**4. Research**:
- Historical data API for researchers
- Anonymized dataset publication
- Academic collaborations
- ML model benchmarking platform

---

## 📖 GLOSSARY OF TERMS

- **Verification Pipeline**: Automated 6-layer system that validates hazard reports
- **Composite Score**: Final percentage (0-100%) calculated from all verification layers
- **Geofencing**: Geographic boundary validation (20km inland, 30km offshore)
- **VectorDB**: FAISS-based semantic search database for text analysis
- **CNN**: Convolutional Neural Network for image classification
- **SLA**: Service Level Agreement - target response/resolution times
- **Ticket**: Communication thread linking reporter, analyst, and authority
- **Escalation**: Raising a ticket to higher authority level
- **Internal Message**: Message visible only to analysts and authorities
- **Read Receipt**: Confirmation that message was viewed
- **Auto-Reject**: Immediate rejection by system (geofence failure)
- **Manual Review**: Human analyst examines report (score 40-75%)
- **Auto-Approve**: Automatic verification by system (score >75%)
- **Reporter Score**: User's historical accuracy percentage
- **Dynamic Weighting**: Adjusting layer importance based on applicability

---

## ✅ SUCCESS METRICS

### System Success Indicators

**Verification Accuracy**:
- **Target**: >90% of auto-approved reports are genuine
- **Target**: <5% false rejection rate
- **Measurement**: Analyst override rate

**Efficiency**:
- **Target**: 65% reports auto-approved (no human review needed)
- **Target**: Manual review completed within 4 hours
- **Measurement**: Time savings vs. full manual review

**User Satisfaction**:
- **Target**: >4.0/5. 0 average satisfaction rating
- **Target**: >80% reports result in action taken
- **Measurement**: Feedback surveys, completion rates

**Response Time**:
- **Target**: Critical tickets first response <1 hour
- **Target**: 80% tickets resolved within SLA
- **Measurement**: Timestamp analysis

**Community Engagement**:
- **Target**: 500+ active reporters
- **Target**: 10+ reports/day after 6 months
- **Measurement**: User registration, report submission rate

---

This comprehensive documentation provides all conceptual details needed to understand and implement the layered verification and ticketing systems. The architecture balances automation (reducing workload) with human oversight (ensuring accuracy) while maintaining transparency and user trust. 
