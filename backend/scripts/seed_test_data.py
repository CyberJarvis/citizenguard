"""
Seed Test Data Script
Creates dummy hazard reports and tickets for testing the ticketing module.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
import random
import uuid

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGODB_DB_NAME", "CoastGuardian")

# Sample coastal locations in India
COASTAL_LOCATIONS = [
    {"latitude": 19.0760, "longitude": 72.8777, "address": "Marine Drive, Mumbai", "region": "Maharashtra", "district": "Mumbai"},
    {"latitude": 13.0827, "longitude": 80.2707, "address": "Marina Beach, Chennai", "region": "Tamil Nadu", "district": "Chennai"},
    {"latitude": 15.2993, "longitude": 74.1240, "address": "Calangute Beach, Goa", "region": "Goa", "district": "North Goa"},
    {"latitude": 9.9312, "longitude": 76.2673, "address": "Fort Kochi Beach, Kerala", "region": "Kerala", "district": "Ernakulam"},
    {"latitude": 17.7357, "longitude": 83.3214, "address": "RK Beach, Visakhapatnam", "region": "Andhra Pradesh", "district": "Visakhapatnam"},
    {"latitude": 21.4858, "longitude": 86.9536, "address": "Puri Beach, Odisha", "region": "Odisha", "district": "Puri"},
    {"latitude": 11.9416, "longitude": 79.8083, "address": "Paradise Beach, Puducherry", "region": "Puducherry", "district": "Puducherry"},
    {"latitude": 8.0883, "longitude": 77.5385, "address": "Kanyakumari Beach", "region": "Tamil Nadu", "district": "Kanyakumari"},
]

HAZARD_TYPES = [
    "high_waves",
    "rip_current",
    "oil_spill",
    "marine_debris",
    "jellyfish_bloom",
    "coastal_erosion",
    "water_pollution",
    "illegal_fishing"
]

SAMPLE_DESCRIPTIONS = {
    "high_waves": [
        "Extremely dangerous wave conditions observed. Waves reaching 4-5 meters. Swimmers should stay away from water.",
        "Strong waves crashing on the shore. Multiple warning signs ignored by tourists. Urgent action needed.",
        "High tide combined with strong winds creating hazardous surf conditions. Beach patrol alerted."
    ],
    "rip_current": [
        "Strong rip current spotted near the main swimming area. Already rescued two swimmers today.",
        "Visible rip current channel forming between sandbars. Red flags have been raised.",
        "Dangerous rip current conditions. Local fishermen confirming strong offshore pull."
    ],
    "oil_spill": [
        "Oil slick visible approximately 500m from shore. Dead fish washing up on beach.",
        "Suspected vessel discharge causing oil contamination. Rainbow sheen on water surface.",
        "Significant oil spill detected. Tar balls appearing on shoreline. Environmental emergency."
    ],
    "marine_debris": [
        "Large amount of plastic waste and fishing nets accumulated on the beach after storm.",
        "Ghost nets entangling sea turtles spotted near the coral area. Immediate cleanup required.",
        "Medical waste and hazardous materials found washed ashore. Beach closed for safety."
    ],
    "jellyfish_bloom": [
        "Massive jellyfish bloom observed. Multiple swimmers stung in the past hour.",
        "Portuguese man-of-war sightings confirmed. Highly venomous. Beach advisory issued.",
        "Blue bottle jellyfish covering large area near shore. First aid station overwhelmed."
    ],
    "coastal_erosion": [
        "Severe coastal erosion threatening beachfront properties. 2 meters of beach lost in past week.",
        "Cliff collapse imminent due to erosion. Safety barriers needed urgently.",
        "Storm surge has accelerated erosion. Coastal road at risk of collapse."
    ],
    "water_pollution": [
        "Sewage discharge detected entering the ocean. Strong odor and discoloration visible.",
        "Industrial effluent causing fish die-off. Water samples collected for testing.",
        "Algal bloom creating dead zones. Swimming banned until further notice."
    ],
    "illegal_fishing": [
        "Trawlers operating in prohibited zone. Damaging coral reef and marine sanctuary.",
        "Dynamite fishing heard near the coast. Marine life in danger.",
        "Illegal nets blocking turtle nesting area. Coast guard notified."
    ]
}

THREAT_LEVELS = ["warning", "alert", "watch", "no_threat"]
PRIORITIES = ["emergency", "critical", "high", "medium", "low"]

# Sample users
SAMPLE_USERS = [
    {"user_id": "USR_TEST_001", "name": "Rajesh Kumar", "email": "rajesh@test.com", "credibility": 85},
    {"user_id": "USR_TEST_002", "name": "Priya Sharma", "email": "priya@test.com", "credibility": 92},
    {"user_id": "USR_TEST_003", "name": "Amit Patel", "email": "amit@test.com", "credibility": 78},
    {"user_id": "USR_TEST_004", "name": "Sunita Reddy", "email": "sunita@test.com", "credibility": 88},
    {"user_id": "USR_TEST_005", "name": "Mohammed Ali", "email": "mohammed@test.com", "credibility": 95},
]

# Sample analysts/authorities
SAMPLE_STAFF = [
    {"user_id": "STAFF_001", "name": "Dr. Arun Menon", "role": "analyst", "email": "arun@coastguard.gov"},
    {"user_id": "STAFF_002", "name": "Commander Vikram Singh", "role": "authority", "email": "vikram@coastguard.gov"},
    {"user_id": "STAFF_003", "name": "Officer Lakshmi Nair", "role": "analyst", "email": "lakshmi@coastguard.gov"},
]


def generate_report_id():
    return f"RPT-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"


def generate_ticket_id():
    return f"TKT-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"


def generate_verification_result(score: float, hazard_type: str):
    """Generate a realistic verification result"""
    decision = "auto_approved" if score >= 75 else "manual_review" if score >= 40 else "auto_rejected"

    # Generate layer results
    layers = [
        {
            "layer_name": "geofence",
            "score": random.uniform(0.7, 1.0) if score >= 70 else random.uniform(0.3, 0.7),
            "status": "pass" if score >= 50 else "fail",
            "weight": 0.20,
            "reasoning": "Location verified within coastal zone" if score >= 50 else "Location appears inland",
            "data": {
                "is_inland": score < 50,
                "distance_to_coast_km": random.uniform(0.1, 5) if score >= 50 else random.uniform(20, 50)
            }
        },
        {
            "layer_name": "weather",
            "score": random.uniform(0.6, 1.0),
            "status": "pass",
            "weight": 0.25,
            "reasoning": "Weather conditions support reported hazard type",
            "data": {
                "conditions_match": True,
                "current_conditions": "Moderate winds, high humidity"
            }
        },
        {
            "layer_name": "text",
            "score": random.uniform(0.65, 0.95),
            "status": "pass",
            "weight": 0.25,
            "reasoning": "Description matches known hazard patterns",
            "data": {
                "similarity_score": random.uniform(0.7, 0.95),
                "predicted_hazard_type": hazard_type,
                "panic_level": random.uniform(0.3, 0.7),
                "is_spam": False
            }
        },
        {
            "layer_name": "image",
            "score": random.uniform(0.6, 0.9) if score >= 60 else random.uniform(0.2, 0.5),
            "status": "pass" if score >= 60 else "fail",
            "weight": 0.20,
            "reasoning": "Image analysis confirms hazard presence" if score >= 60 else "Image unclear or not matching",
            "data": {
                "predicted_class": hazard_type,
                "prediction_confidence": random.uniform(0.6, 0.9),
                "is_match": score >= 60
            }
        },
        {
            "layer_name": "reporter",
            "score": random.uniform(0.7, 1.0),
            "status": "pass",
            "weight": 0.10,
            "reasoning": "Reporter has good credibility history",
            "data": {
                "credibility_score": random.randint(70, 95),
                "historical_accuracy": random.uniform(0.75, 0.95),
                "total_reports": random.randint(5, 50)
            }
        }
    ]

    return {
        "verification_id": f"VER-{uuid.uuid4().hex[:12].upper()}",
        "composite_score": score,
        "decision": decision,
        "layer_results": layers,
        "processing_time_ms": random.randint(500, 2000),
        "created_at": datetime.now(timezone.utc).isoformat()
    }


def generate_hazard_classification(hazard_type: str, score: float):
    """Generate hazard classification data"""
    threat_level = "warning" if score >= 85 else "alert" if score >= 70 else "watch" if score >= 50 else "no_threat"

    return {
        "hazard_type": hazard_type,
        "threat_level": threat_level,
        "confidence": random.uniform(0.7, 0.95),
        "reasoning": f"Analysis indicates {hazard_type.replace('_', ' ')} conditions with {threat_level} level threat",
        "recommendations": [
            "Monitor the situation closely",
            "Alert local authorities if conditions worsen",
            "Keep public away from affected area",
            "Document any changes in conditions"
        ]
    }


def generate_environmental_snapshot():
    """Generate environmental snapshot data"""
    return {
        "weather": {
            "condition": random.choice(["Partly Cloudy", "Sunny", "Overcast", "Light Rain"]),
            "temp_c": random.uniform(25, 35),
            "feelslike_c": random.uniform(27, 38),
            "wind_kph": random.uniform(10, 40),
            "wind_dir": random.choice(["N", "NE", "E", "SE", "S", "SW", "W", "NW"]),
            "gust_kph": random.uniform(15, 50),
            "humidity": random.randint(60, 90),
            "vis_km": random.uniform(5, 15)
        },
        "marine": {
            "sig_ht_mt": random.uniform(0.5, 3.0),
            "swell_ht_mt": random.uniform(0.3, 2.5),
            "swell_dir_16_point": random.choice(["N", "NE", "E", "SE", "S", "SW", "W", "NW"]),
            "water_temp_c": random.uniform(24, 30)
        },
        "captured_at": datetime.now(timezone.utc).isoformat()
    }


def calculate_sla_deadlines(priority: str, created_at: datetime):
    """Calculate SLA response and resolution deadlines"""
    response_hours = {
        "emergency": 0.5,
        "critical": 2,
        "high": 4,
        "medium": 8,
        "low": 24
    }
    resolution_hours = {
        "emergency": 4,
        "critical": 12,
        "high": 24,
        "medium": 48,
        "low": 72
    }

    return {
        "response_due": created_at + timedelta(hours=response_hours.get(priority, 8)),
        "resolution_due": created_at + timedelta(hours=resolution_hours.get(priority, 48))
    }


async def create_test_reports_and_tickets(db):
    """Create test hazard reports and tickets"""

    reports_created = 0
    tickets_created = 0

    # Create 15 test reports with varying scores
    test_scenarios = [
        # High score auto-approved (will create tickets)
        {"score": 92, "status": "verified", "hazard_type": "high_waves", "priority": "critical"},
        {"score": 88, "status": "verified", "hazard_type": "rip_current", "priority": "high"},
        {"score": 85, "status": "verified", "hazard_type": "oil_spill", "priority": "emergency"},
        {"score": 82, "status": "verified", "hazard_type": "jellyfish_bloom", "priority": "high"},
        {"score": 78, "status": "verified", "hazard_type": "water_pollution", "priority": "critical"},

        # Medium score manual review
        {"score": 68, "status": "needs_manual_review", "hazard_type": "marine_debris", "priority": "medium"},
        {"score": 62, "status": "needs_manual_review", "hazard_type": "coastal_erosion", "priority": "medium"},
        {"score": 55, "status": "needs_manual_review", "hazard_type": "illegal_fishing", "priority": "low"},
        {"score": 48, "status": "needs_manual_review", "hazard_type": "high_waves", "priority": "medium"},
        {"score": 45, "status": "needs_manual_review", "hazard_type": "rip_current", "priority": "medium"},

        # Low score auto-rejected
        {"score": 35, "status": "auto_rejected", "hazard_type": "oil_spill", "priority": "low"},
        {"score": 28, "status": "auto_rejected", "hazard_type": "marine_debris", "priority": "low"},
        {"score": 22, "status": "auto_rejected", "hazard_type": "water_pollution", "priority": "low"},

        # Manually approved (will create tickets)
        {"score": 58, "status": "verified", "hazard_type": "coastal_erosion", "priority": "high", "manual": True},
        {"score": 52, "status": "verified", "hazard_type": "illegal_fishing", "priority": "medium", "manual": True},
    ]

    for i, scenario in enumerate(test_scenarios):
        user = random.choice(SAMPLE_USERS)
        location = random.choice(COASTAL_LOCATIONS)
        hazard_type = scenario["hazard_type"]
        descriptions = SAMPLE_DESCRIPTIONS.get(hazard_type, ["Hazard observed at this location."])

        report_id = generate_report_id()
        now = datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 72))

        verification_result = generate_verification_result(scenario["score"], hazard_type)
        hazard_classification = generate_hazard_classification(hazard_type, scenario["score"])

        # Create hazard report
        report = {
            "report_id": report_id,
            "user_id": user["user_id"],
            "user_name": user["name"],
            "hazard_type": hazard_type,
            "category": "natural" if hazard_type in ["high_waves", "rip_current", "coastal_erosion"] else "pollution" if hazard_type in ["oil_spill", "water_pollution"] else "wildlife" if hazard_type == "jellyfish_bloom" else "other",
            "description": random.choice(descriptions),
            "image_url": f"/uploads/hazards/test_{hazard_type}_{i+1}.jpg",
            "voice_note_url": None,
            "location": {
                "latitude": location["latitude"] + random.uniform(-0.01, 0.01),
                "longitude": location["longitude"] + random.uniform(-0.01, 0.01),
                "address": location["address"],
                "region": location["region"],
                "district": location["district"]
            },
            "verification_status": scenario["status"],
            "verification_score": scenario["score"],
            "verification_result": verification_result,
            "verification_id": verification_result["verification_id"],
            "geofence_valid": scenario["score"] >= 50,
            "geofence_distance_km": random.uniform(0.5, 5) if scenario["score"] >= 50 else random.uniform(25, 50),
            "environmental_snapshot": generate_environmental_snapshot(),
            "hazard_classification": hazard_classification,
            "verified_at": now + timedelta(minutes=random.randint(5, 30)) if scenario["status"] == "verified" else None,
            "verified_by": random.choice(SAMPLE_STAFF)["user_id"] if scenario.get("manual") else None,
            "verified_by_name": random.choice(SAMPLE_STAFF)["name"] if scenario.get("manual") else None,
            "risk_level": "high" if scenario["score"] >= 75 else "medium" if scenario["score"] >= 50 else "low",
            "urgency": scenario["priority"],
            "requires_immediate_action": scenario["priority"] in ["emergency", "critical"],
            "likes": random.randint(0, 50),
            "comments": random.randint(0, 20),
            "views": random.randint(10, 500),
            "is_active": True,
            "created_at": now,
            "updated_at": now + timedelta(minutes=random.randint(1, 60))
        }

        # Insert report
        await db.hazard_reports.insert_one(report)
        reports_created += 1
        print(f"Created report: {report_id} - {hazard_type} (Score: {scenario['score']}%, Status: {scenario['status']})")

        # Create ticket for verified reports
        if scenario["status"] == "verified":
            ticket_id = generate_ticket_id()
            sla = calculate_sla_deadlines(scenario["priority"], now)

            ticket = {
                "ticket_id": ticket_id,
                "report_id": report_id,
                "hazard_type": hazard_type,
                "title": f"[{'AUTO' if not scenario.get('manual') else 'MANUAL'}] {hazard_type.replace('_', ' ').title()} at {location['address'][:40]}",
                "description": report["description"],
                "location_latitude": location["latitude"],
                "location_longitude": location["longitude"],
                "location_address": location["address"],
                "status": random.choice(["open", "assigned", "in_progress"]) if random.random() > 0.3 else "open",
                "priority": scenario["priority"],
                "reporter_id": user["user_id"],
                "reporter_name": user["name"],
                "authority_id": random.choice(SAMPLE_STAFF)["user_id"],
                "authority_name": random.choice(SAMPLE_STAFF)["name"],
                "analyst_id": random.choice([s for s in SAMPLE_STAFF if s["role"] == "analyst"])["user_id"] if random.random() > 0.5 else None,
                "response_due": sla["response_due"],
                "resolution_due": sla["resolution_due"],
                "responded_at": now + timedelta(minutes=random.randint(10, 60)) if random.random() > 0.4 else None,
                "tags": [hazard_type, scenario["priority"], "auto" if not scenario.get("manual") else "manual"],
                "total_messages": 0,
                "metadata": {
                    "verification_score": scenario["score"],
                    "threat_level": hazard_classification["threat_level"],
                    "approval_type": "manual" if scenario.get("manual") else "auto",
                    "auto_generated": True
                },
                "created_at": now + timedelta(minutes=5),
                "updated_at": now + timedelta(minutes=random.randint(10, 120))
            }

            await db.tickets.insert_one(ticket)
            tickets_created += 1

            # Update report with ticket reference
            await db.hazard_reports.update_one(
                {"report_id": report_id},
                {"$set": {
                    "ticket_id": ticket_id,
                    "has_ticket": True,
                    "ticket_status": ticket["status"]
                }}
            )

            # Create initial system message
            message = {
                "message_id": f"MSG-{uuid.uuid4().hex[:12].upper()}",
                "ticket_id": ticket_id,
                "sender_id": "SYSTEM",
                "sender_name": "AI Verification System",
                "sender_role": "system",
                "message_type": "system",
                "content": f"""Ticket auto-generated for {'AI-approved' if not scenario.get('manual') else 'manually approved'} hazard report.

VERIFICATION SCORE: {scenario['score']:.1f}%
PRIORITY: {scenario['priority'].upper()}
THREAT LEVEL: {hazard_classification['threat_level'].upper()}

HAZARD DETAILS:
- Type: {hazard_type.replace('_', ' ').title()}
- Location: {location['address']}
- Region: {location['region']}

ENVIRONMENTAL CONDITIONS:
- Weather: {report['environmental_snapshot']['weather']['condition']}
- Temperature: {report['environmental_snapshot']['weather']['temp_c']:.1f}°C
- Wind: {report['environmental_snapshot']['weather']['wind_kph']:.1f} km/h
- Wave Height: {report['environmental_snapshot']['marine']['sig_ht_mt']:.1f}m

RECOMMENDATIONS:
{chr(10).join(['- ' + r for r in hazard_classification['recommendations']])}

SLA DEADLINES:
- Response Due: {sla['response_due'].strftime('%Y-%m-%d %H:%M UTC')}
- Resolution Due: {sla['resolution_due'].strftime('%Y-%m-%d %H:%M UTC')}""",
                "is_internal": False,
                "created_at": now + timedelta(minutes=5)
            }

            await db.ticket_messages.insert_one(message)

            # Update ticket message count
            await db.tickets.update_one(
                {"ticket_id": ticket_id},
                {"$set": {"total_messages": 1, "last_message_at": now + timedelta(minutes=5), "last_message_by": "SYSTEM"}}
            )

            # Create activity log
            activity = {
                "activity_id": f"ACT-{uuid.uuid4().hex[:12].upper()}",
                "ticket_id": ticket_id,
                "activity_type": "ticket_created",
                "performed_by_id": "SYSTEM",
                "performed_by_name": "AI Verification System",
                "performed_by_role": "system",
                "description": f"Ticket auto-generated for {'auto' if not scenario.get('manual') else 'manually'} approved report",
                "details": {
                    "report_id": report_id,
                    "priority": scenario["priority"],
                    "verification_score": scenario["score"]
                },
                "created_at": now + timedelta(minutes=5)
            }

            await db.ticket_activities.insert_one(activity)

            print(f"  -> Created ticket: {ticket_id} (Priority: {scenario['priority']}, Status: {ticket['status']})")

    return reports_created, tickets_created


async def main():
    print("=" * 60)
    print("CoastGuardians Test Data Seeder")
    print("=" * 60)

    # Connect to MongoDB
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]

    print(f"\nConnecting to MongoDB: {MONGO_URI}")
    print(f"Database: {DB_NAME}")

    # Clear existing test data (optional)
    print("\nClearing existing test data...")
    await db.hazard_reports.delete_many({"report_id": {"$regex": "^RPT-"}})
    await db.tickets.delete_many({"ticket_id": {"$regex": "^TKT-"}})
    await db.ticket_messages.delete_many({"message_id": {"$regex": "^MSG-"}})
    await db.ticket_activities.delete_many({"activity_id": {"$regex": "^ACT-"}})

    # Create test data
    print("\nCreating test hazard reports and tickets...")
    reports, tickets = await create_test_reports_and_tickets(db)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Reports created: {reports}")
    print(f"Tickets created: {tickets}")
    print("\nTest data seeding complete!")

    # Show stats
    report_count = await db.hazard_reports.count_documents({})
    ticket_count = await db.tickets.count_documents({})
    message_count = await db.ticket_messages.count_documents({})

    print(f"\nDatabase Statistics:")
    print(f"  Total hazard reports: {report_count}")
    print(f"  Total tickets: {ticket_count}")
    print(f"  Total ticket messages: {message_count}")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
