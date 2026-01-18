"""
Reporter Test Data Fixtures
Contains predefined reporter profiles for testing verification scoring.
"""

import uuid

# =============================================================================
# REPORTER PROFILES
# =============================================================================

REPORTER_PROFILES = {
    # High trust reporters
    "verified_authority": {
        "id": str(uuid.uuid4()),
        "role": "authority",
        "verified": True,
        "reports_count": 50,
        "verified_reports": 45,
        "spam_reports": 0,
        "trust_score": 0.95,
        "email": "authority@coastguard.gov.in",
        "organization": "Indian Coast Guard",
        "expected_score_contribution": 0.095  # 10% weight * 0.95 trust
    },
    "coast_guard_official": {
        "id": str(uuid.uuid4()),
        "role": "authority",
        "verified": True,
        "reports_count": 100,
        "verified_reports": 98,
        "spam_reports": 0,
        "trust_score": 0.98,
        "email": "official@coastguard.gov.in",
        "organization": "Indian Coast Guard",
        "expected_score_contribution": 0.098
    },
    "navy_personnel": {
        "id": str(uuid.uuid4()),
        "role": "authority",
        "verified": True,
        "reports_count": 30,
        "verified_reports": 29,
        "spam_reports": 0,
        "trust_score": 0.97,
        "email": "naval@navy.gov.in",
        "organization": "Indian Navy",
        "expected_score_contribution": 0.097
    },

    # Medium-high trust reporters
    "trusted_analyst": {
        "id": str(uuid.uuid4()),
        "role": "analyst",
        "verified": True,
        "reports_count": 100,
        "verified_reports": 85,
        "spam_reports": 2,
        "trust_score": 0.85,
        "email": "analyst@example.com",
        "expected_score_contribution": 0.085
    },
    "senior_analyst": {
        "id": str(uuid.uuid4()),
        "role": "analyst",
        "verified": True,
        "reports_count": 200,
        "verified_reports": 180,
        "spam_reports": 3,
        "trust_score": 0.90,
        "email": "senior.analyst@example.com",
        "expected_score_contribution": 0.090
    },

    # Medium trust reporters
    "experienced_citizen": {
        "id": str(uuid.uuid4()),
        "role": "citizen",
        "verified": True,
        "reports_count": 20,
        "verified_reports": 15,
        "spam_reports": 1,
        "trust_score": 0.75,
        "email": "citizen@example.com",
        "expected_score_contribution": 0.075
    },
    "active_volunteer": {
        "id": str(uuid.uuid4()),
        "role": "citizen",
        "verified": True,
        "reports_count": 40,
        "verified_reports": 30,
        "spam_reports": 2,
        "trust_score": 0.70,
        "email": "volunteer@example.com",
        "expected_score_contribution": 0.070
    },
    "fisherman_reporter": {
        "id": str(uuid.uuid4()),
        "role": "citizen",
        "verified": True,
        "reports_count": 25,
        "verified_reports": 22,
        "spam_reports": 0,
        "trust_score": 0.80,
        "email": "fisherman@example.com",
        "occupation": "Fisherman",
        "expected_score_contribution": 0.080
    },

    # Low trust reporters
    "new_citizen": {
        "id": str(uuid.uuid4()),
        "role": "citizen",
        "verified": True,
        "reports_count": 2,
        "verified_reports": 1,
        "spam_reports": 0,
        "trust_score": 0.50,
        "email": "newuser@example.com",
        "expected_score_contribution": 0.050
    },
    "first_time_reporter": {
        "id": str(uuid.uuid4()),
        "role": "citizen",
        "verified": True,
        "reports_count": 0,
        "verified_reports": 0,
        "spam_reports": 0,
        "trust_score": 0.40,
        "email": "firsttime@example.com",
        "expected_score_contribution": 0.040
    },
    "unverified_user": {
        "id": str(uuid.uuid4()),
        "role": "citizen",
        "verified": False,
        "reports_count": 0,
        "verified_reports": 0,
        "spam_reports": 0,
        "trust_score": 0.30,
        "email": "unverified@example.com",
        "expected_score_contribution": 0.030
    },

    # Problematic reporters
    "suspected_spammer": {
        "id": str(uuid.uuid4()),
        "role": "citizen",
        "verified": True,
        "reports_count": 15,
        "verified_reports": 2,
        "spam_reports": 10,
        "trust_score": 0.10,
        "email": "spammer@example.com",
        "expected_score_contribution": 0.010
    },
    "known_false_reporter": {
        "id": str(uuid.uuid4()),
        "role": "citizen",
        "verified": True,
        "reports_count": 8,
        "verified_reports": 0,
        "spam_reports": 6,
        "trust_score": 0.05,
        "email": "falsereporter@example.com",
        "expected_score_contribution": 0.005
    },
    "banned_user": {
        "id": str(uuid.uuid4()),
        "role": "citizen",
        "verified": False,
        "reports_count": 20,
        "verified_reports": 0,
        "spam_reports": 18,
        "trust_score": 0.00,
        "email": "banned@example.com",
        "is_banned": True,
        "expected_score_contribution": 0.000
    },

    # Special cases
    "tourist_reporter": {
        "id": str(uuid.uuid4()),
        "role": "citizen",
        "verified": True,
        "reports_count": 1,
        "verified_reports": 1,
        "spam_reports": 0,
        "trust_score": 0.55,
        "email": "tourist@example.com",
        "is_tourist": True,
        "expected_score_contribution": 0.055
    },
    "local_resident": {
        "id": str(uuid.uuid4()),
        "role": "citizen",
        "verified": True,
        "reports_count": 10,
        "verified_reports": 9,
        "spam_reports": 0,
        "trust_score": 0.82,
        "email": "local@example.com",
        "is_local": True,
        "expected_score_contribution": 0.082
    }
}

# =============================================================================
# REPORTER TRUST SCORE CALCULATION
# =============================================================================

def calculate_expected_trust_score(reporter_profile: dict) -> float:
    """
    Calculate expected trust score based on reporter history.
    Mirrors the actual verification system logic.
    """
    reports_count = reporter_profile.get("reports_count", 0)
    verified_reports = reporter_profile.get("verified_reports", 0)
    spam_reports = reporter_profile.get("spam_reports", 0)
    is_verified = reporter_profile.get("verified", False)
    role = reporter_profile.get("role", "citizen")

    # Base score by role
    base_scores = {
        "authority": 0.90,
        "analyst": 0.70,
        "citizen": 0.50
    }
    base_score = base_scores.get(role, 0.50)

    # Verification bonus
    if is_verified:
        base_score += 0.05

    # History-based adjustment
    if reports_count > 0:
        accuracy_rate = verified_reports / reports_count
        spam_rate = spam_reports / reports_count

        # Accuracy bonus (up to +0.15)
        base_score += accuracy_rate * 0.15

        # Spam penalty (up to -0.30)
        base_score -= spam_rate * 0.30

        # Experience bonus (up to +0.10)
        experience_bonus = min(reports_count / 100, 0.10)
        base_score += experience_bonus

    # Clamp to valid range
    return max(0.0, min(1.0, base_score))


# =============================================================================
# REPORTER SCENARIOS
# =============================================================================

REPORTER_SCENARIOS = {
    "trusted_emergency_report": {
        "profile": "verified_authority",
        "expected_outcome": "high_trust_contribution",
        "description": "Authority reporting emergency - should get high trust score"
    },
    "new_user_valid_report": {
        "profile": "first_time_reporter",
        "expected_outcome": "low_trust_contribution",
        "description": "New user with valid report - low trust but not rejected"
    },
    "spammer_report": {
        "profile": "suspected_spammer",
        "expected_outcome": "very_low_trust_contribution",
        "description": "Known spammer - very low trust score"
    },
    "local_knowledge": {
        "profile": "local_resident",
        "expected_outcome": "moderate_high_trust",
        "description": "Local resident with area knowledge - higher trust"
    },
    "professional_fisherman": {
        "profile": "fisherman_reporter",
        "expected_outcome": "high_trust_for_marine",
        "description": "Fisherman reporting marine hazard - extra credibility"
    }
}
