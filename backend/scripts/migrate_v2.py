"""
V2 Migration Script - Verification & Ticketing Loop Re-engineering
Migrates existing data to new model structure.

Run: python -m scripts.migrate_v2

Changes applied:
1. HazardReport: Add approval_source, ticket_creation_status, requires_authority_confirmation fields
2. Ticket: Add assignment, approval, sla_config, sync_version fields; fix PENDING_ASSIGNMENT
3. TicketMessage: Add thread field (default: "all")
4. User: Add rejected_reports, bound credibility_score to 0-100
5. VerificationResult: Add ai_recommendation, requires_authority_confirmation fields
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()


async def get_database():
    """Get MongoDB database connection"""
    mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGODB_DB_NAME", "coastguardian")

    client = AsyncIOMotorClient(mongo_uri)
    return client[db_name]


async def migrate_hazard_reports(db):
    """Migrate HazardReport documents to V2 structure"""
    print("\n=== Migrating HazardReport documents ===")

    collection = db.hazard_reports
    total = await collection.count_documents({})
    print(f"Total documents: {total}")

    # Add new V2 fields with defaults
    update_result = await collection.update_many(
        {"approval_source": {"$exists": False}},
        {
            "$set": {
                "approval_source": None,
                "approval_source_details": None,
                "ticket_creation_status": "not_eligible",
                "ticket_creation_attempted_at": None,
                "requires_authority_confirmation": False,
                "confirmation_received_at": None,
                "confirmed_by": None,
                "confirmed_by_name": None
            }
        }
    )
    print(f"Added new fields to {update_result.modified_count} documents")

    # Set ticket_creation_status for reports that already have tickets
    update_result = await collection.update_many(
        {
            "has_ticket": True,
            "ticket_id": {"$ne": None}
        },
        {"$set": {"ticket_creation_status": "created"}}
    )
    print(f"Set ticket_creation_status='created' for {update_result.modified_count} documents with tickets")

    # Set approval_source for verified reports
    # If verified_by is set, it was manually approved
    update_result = await collection.update_many(
        {
            "verification_status": "verified",
            "verified_by": {"$ne": None},
            "approval_source": None
        },
        {"$set": {"approval_source": "authority_manual"}}
    )
    print(f"Set approval_source='authority_manual' for {update_result.modified_count} manually verified reports")

    # For auto-verified reports (verified but no verified_by)
    update_result = await collection.update_many(
        {
            "verification_status": "verified",
            "verified_by": None,
            "approval_source": None
        },
        {"$set": {"approval_source": "ai_auto"}}
    )
    print(f"Set approval_source='ai_auto' for {update_result.modified_count} auto-verified reports")


async def migrate_tickets(db):
    """Migrate Ticket documents to V2 structure"""
    print("\n=== Migrating Ticket documents ===")

    collection = db.tickets
    total = await collection.count_documents({})
    print(f"Total documents: {total}")

    # Add new V2 fields
    update_result = await collection.update_many(
        {"assignment": {"$exists": False}},
        {
            "$set": {
                "assignment": None,
                "approval": None,
                "sla_config": None,
                "sync_version": 0
            }
        }
    )
    print(f"Added V2 fields to {update_result.modified_count} tickets")

    # Fix PENDING_ASSIGNMENT - convert to structured assignment
    cursor = collection.find({
        "$or": [
            {"authority_id": "PENDING_ASSIGNMENT"},
            {"assigned_authority_id": "PENDING_ASSIGNMENT"}
        ]
    })

    fixed_count = 0
    async for ticket in cursor:
        # Build V2 assignment structure
        assignment = {
            "analyst_id": ticket.get("assigned_analyst_id"),
            "analyst_name": ticket.get("assigned_analyst_name"),
            "analyst_assigned_at": None,
            "analyst_assigned_by": None,
            "authority_id": None,  # Fix: was "PENDING_ASSIGNMENT"
            "authority_name": None,
            "authority_assigned_at": None,
            "authority_assigned_by": None,
            "status": "unassigned"
        }

        # Determine assignment status
        if assignment["analyst_id"]:
            assignment["status"] = "analyst_only"

        # Build V2 approval structure if we have approved_by info
        approval = None
        if ticket.get("approved_by"):
            approval = {
                "approval_source": "authority_manual",
                "approved_by_id": ticket.get("approved_by"),
                "approved_by_name": ticket.get("approved_by_name"),
                "approved_by_role": ticket.get("approved_by_role"),
                "ai_verification_score": None,
                "approved_at": ticket.get("created_at"),
                "approval_notes": None
            }

        await collection.update_one(
            {"_id": ticket["_id"]},
            {
                "$set": {
                    "authority_id": None,
                    "authority_name": None,
                    "assigned_authority_id": None,
                    "assigned_authority_name": None,
                    "assignment": assignment,
                    "approval": approval
                }
            }
        )
        fixed_count += 1

    print(f"Fixed {fixed_count} tickets with PENDING_ASSIGNMENT")

    # For other tickets, build assignment structure from legacy fields
    cursor = collection.find({
        "assignment": None,
        "authority_id": {"$ne": "PENDING_ASSIGNMENT"}
    })

    migrated_count = 0
    async for ticket in cursor:
        # Build V2 assignment structure
        has_analyst = ticket.get("assigned_analyst_id") is not None
        has_authority = ticket.get("assigned_authority_id") is not None and ticket.get("assigned_authority_id") != "PENDING_ASSIGNMENT"

        if has_analyst and has_authority:
            status = "fully_assigned"
        elif has_analyst:
            status = "analyst_only"
        elif has_authority:
            status = "authority_only"
        else:
            status = "unassigned"

        assignment = {
            "analyst_id": ticket.get("assigned_analyst_id"),
            "analyst_name": ticket.get("assigned_analyst_name"),
            "analyst_assigned_at": None,
            "analyst_assigned_by": None,
            "authority_id": ticket.get("assigned_authority_id") if has_authority else None,
            "authority_name": ticket.get("assigned_authority_name") if has_authority else None,
            "authority_assigned_at": None,
            "authority_assigned_by": None,
            "status": status
        }

        # Build V2 approval structure
        approval = None
        if ticket.get("approved_by"):
            approval = {
                "approval_source": "authority_manual",
                "approved_by_id": ticket.get("approved_by"),
                "approved_by_name": ticket.get("approved_by_name"),
                "approved_by_role": ticket.get("approved_by_role"),
                "ai_verification_score": None,
                "approved_at": ticket.get("created_at"),
                "approval_notes": None
            }

        await collection.update_one(
            {"_id": ticket["_id"]},
            {"$set": {"assignment": assignment, "approval": approval}}
        )
        migrated_count += 1

    print(f"Migrated {migrated_count} tickets to V2 assignment structure")


async def migrate_ticket_messages(db):
    """Migrate TicketMessage documents to V2 structure with thread support"""
    print("\n=== Migrating TicketMessage documents ===")

    collection = db.ticket_messages
    total = await collection.count_documents({})
    print(f"Total documents: {total}")

    # Add thread field with default "all"
    update_result = await collection.update_many(
        {"thread": {"$exists": False}},
        {
            "$set": {
                "thread": "all",
                "visible_to": []
            }
        }
    )
    print(f"Added thread='all' to {update_result.modified_count} messages")

    # Convert is_internal=true to thread="internal"
    update_result = await collection.update_many(
        {"is_internal": True, "thread": "all"},
        {"$set": {"thread": "internal"}}
    )
    print(f"Converted {update_result.modified_count} internal messages to thread='internal'")


async def migrate_users(db):
    """Migrate User documents to V2 structure"""
    print("\n=== Migrating User documents ===")

    collection = db.users
    total = await collection.count_documents({})
    print(f"Total documents: {total}")

    # Add rejected_reports field
    update_result = await collection.update_many(
        {"rejected_reports": {"$exists": False}},
        {"$set": {"rejected_reports": 0, "credibility_metrics": None}}
    )
    print(f"Added rejected_reports to {update_result.modified_count} users")

    # Bound credibility scores to 0-100
    # Fix scores > 100
    update_result = await collection.update_many(
        {"credibility_score": {"$gt": 100}},
        {"$set": {"credibility_score": 100}}
    )
    print(f"Bounded {update_result.modified_count} users with credibility > 100")

    # Fix scores < 0
    update_result = await collection.update_many(
        {"credibility_score": {"$lt": 0}},
        {"$set": {"credibility_score": 0}}
    )
    print(f"Bounded {update_result.modified_count} users with credibility < 0")

    # Initialize credibility_score where missing
    update_result = await collection.update_many(
        {"credibility_score": None},
        {"$set": {"credibility_score": 50}}
    )
    print(f"Initialized credibility_score for {update_result.modified_count} users")


async def migrate_verification_results(db):
    """Migrate VerificationResult documents to V2 structure"""
    print("\n=== Migrating VerificationResult documents ===")

    collection = db.verification_results
    if collection is None:
        print("verification_results collection not found, skipping...")
        return

    total = await collection.count_documents({})
    print(f"Total documents: {total}")

    # Add V2 fields
    update_result = await collection.update_many(
        {"ai_recommendation": {"$exists": False}},
        {
            "$set": {
                "ai_recommendation": None,
                "requires_authority_confirmation": False,
                "authority_confirmation": None
            }
        }
    )
    print(f"Added V2 fields to {update_result.modified_count} verification results")

    # Compute ai_recommendation from score for existing documents
    cursor = collection.find({"ai_recommendation": None})
    updated_count = 0

    async for doc in cursor:
        score = doc.get("composite_score", 0)
        decision = doc.get("decision", "")

        # Determine AI recommendation based on score
        if decision == "auto_rejected":
            recommendation = "reject"
            requires_confirmation = False
        elif score >= 85:
            recommendation = "approve"
            requires_confirmation = False
        elif score >= 75:
            recommendation = "recommend"
            requires_confirmation = True
        elif score >= 40:
            recommendation = "review"
            requires_confirmation = False
        else:
            recommendation = "reject"
            requires_confirmation = False

        await collection.update_one(
            {"_id": doc["_id"]},
            {
                "$set": {
                    "ai_recommendation": recommendation,
                    "requires_authority_confirmation": requires_confirmation
                }
            }
        )
        updated_count += 1

    print(f"Computed ai_recommendation for {updated_count} verification results")


async def create_indexes(db):
    """Create indexes for V2 fields"""
    print("\n=== Creating indexes ===")

    # HazardReport indexes
    await db.hazard_reports.create_index("approval_source")
    await db.hazard_reports.create_index("ticket_creation_status")
    await db.hazard_reports.create_index("requires_authority_confirmation")
    print("Created HazardReport indexes")

    # Ticket indexes
    await db.tickets.create_index("assignment.status")
    await db.tickets.create_index("approval.approval_source")
    print("Created Ticket indexes")

    # TicketMessage indexes
    await db.ticket_messages.create_index("thread")
    await db.ticket_messages.create_index([("ticket_id", 1), ("thread", 1)])
    print("Created TicketMessage indexes")


async def run_migration():
    """Run the full V2 migration"""
    print("=" * 60)
    print("V2 Migration - Verification & Ticketing Loop Re-engineering")
    print("=" * 60)
    print(f"Started at: {datetime.now(timezone.utc).isoformat()}")

    try:
        db = await get_database()
        print(f"\nConnected to database: {db.name}")

        # Run migrations
        await migrate_hazard_reports(db)
        await migrate_tickets(db)
        await migrate_ticket_messages(db)
        await migrate_users(db)
        await migrate_verification_results(db)
        await create_indexes(db)

        print("\n" + "=" * 60)
        print("Migration completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\nMigration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(run_migration())
    sys.exit(exit_code)
