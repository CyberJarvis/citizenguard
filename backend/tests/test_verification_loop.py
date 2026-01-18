"""
Test Script for 6-Layer Verification Loop
Tests both AUTO_APPROVED and AUTO_REJECTED conditions

Run with: python -m pytest tests/test_verification_loop.py -v
Or directly: python tests/test_verification_loop.py
"""

import asyncio
import httpx
import json
from datetime import datetime
from typing import Dict, Any, Optional
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
TIMEOUT = 30.0

# Test credentials (update these with valid test user credentials)
TEST_USER_EMAIL = "test@example.com"
TEST_USER_PASSWORD = "testpassword123"

# Test data for different scenarios
TEST_SCENARIOS = {
    "auto_approved": {
        "description": "Valid coastal hazard report that should be auto-approved (score >= 75%)",
        "report_data": {
            "hazard_type": "oil_spill",
            "description": "Large oil slick observed approximately 2km off the coast near Juhu Beach. The slick appears to be spreading towards the shore. Multiple fishing boats in the area have reported the incident. The oil appears dark and viscous, likely from a ship or offshore platform leak.",
            "location": {
                "latitude": 19.0948,  # Juhu Beach - coastal location (should pass geofence)
                "longitude": 72.8267,
                "address": "Juhu Beach, Mumbai, Maharashtra"
            },
            "severity": "high"
        },
        "expected_decision": "auto_approved",
        "expected_min_score": 75.0
    },
    "auto_rejected_geofence": {
        "description": "Report from inland location that should be auto-rejected (geofence failure)",
        "report_data": {
            "hazard_type": "oil_spill",
            "description": "Oil spill detected in the area. Large amount of oil spreading.",
            "location": {
                "latitude": 28.6139,  # New Delhi - far inland (should fail geofence)
                "longitude": 77.2090,
                "address": "Connaught Place, New Delhi"
            },
            "severity": "medium"
        },
        "expected_decision": "auto_rejected",
        "expected_reason": "geofence"
    },
    "manual_review": {
        "description": "Report with moderate confidence that needs manual review (score 40-75%)",
        "report_data": {
            "hazard_type": "marine_debris",
            "description": "Some trash seen floating near the beach.",
            "location": {
                "latitude": 15.2993,  # Goa coast
                "longitude": 74.1240,
                "address": "Calangute Beach, Goa"
            },
            "severity": "low"
        },
        "expected_decision": "manual_review",
        "expected_min_score": 40.0,
        "expected_max_score": 75.0
    },
    "rejected_low_score": {
        "description": "Report with very low quality that should be rejected (score < 40%)",
        "report_data": {
            "hazard_type": "other",
            "description": "bad",  # Very short, low quality description
            "location": {
                "latitude": 13.0827,  # Chennai coast
                "longitude": 80.2707,
                "address": "Marina Beach, Chennai"
            },
            "severity": "low"
        },
        "expected_decision": "rejected",
        "expected_max_score": 40.0
    }
}


class VerificationLoopTester:
    """Test class for the 6-Layer Verification Loop"""

    def __init__(self):
        self.client: Optional[httpx.AsyncClient] = None
        self.access_token: Optional[str] = None
        self.test_results: Dict[str, Any] = {}

    async def setup(self):
        """Initialize HTTP client"""
        self.client = httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT)

    async def cleanup(self):
        """Close HTTP client"""
        if self.client:
            await self.client.aclose()

    async def authenticate(self) -> bool:
        """Authenticate and get access token"""
        print("\n" + "="*60)
        print("🔐 AUTHENTICATION")
        print("="*60)

        try:
            # Try to login with test credentials
            response = await self.client.post(
                "/auth/login",
                data={
                    "username": TEST_USER_EMAIL,
                    "password": TEST_USER_PASSWORD
                }
            )

            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token") or data.get("data", {}).get("access_token")
                print(f"✅ Authenticated successfully")
                return True
            else:
                print(f"⚠️  Login failed: {response.status_code}")
                print("   Continuing without authentication (some tests may fail)")
                return False

        except Exception as e:
            print(f"⚠️  Authentication error: {e}")
            print("   Continuing without authentication")
            return False

    def get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        headers = {"Content-Type": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    async def check_verification_health(self) -> bool:
        """Check if verification service is healthy"""
        print("\n" + "="*60)
        print("🏥 VERIFICATION SERVICE HEALTH CHECK")
        print("="*60)

        try:
            response = await self.client.get("/verification/health")
            data = response.json()

            print(f"Status: {data.get('status')}")
            print(f"Initialized: {data.get('initialized')}")
            print(f"Layers: {', '.join(data.get('layers', []))}")

            if data.get("initialized"):
                print("✅ Verification service is healthy and initialized")
                return True
            else:
                print("❌ Verification service is not initialized")
                return False

        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return False

    async def submit_hazard_report(self, report_data: Dict[str, Any]) -> Optional[str]:
        """Submit a hazard report and return the report_id"""
        try:
            response = await self.client.post(
                "/hazards/",
                json=report_data,
                headers=self.get_headers()
            )

            if response.status_code in [200, 201]:
                data = response.json()
                report_id = data.get("report_id") or data.get("data", {}).get("report_id")
                print(f"   📝 Report submitted: {report_id}")
                return report_id
            else:
                print(f"   ❌ Failed to submit report: {response.status_code}")
                print(f"      Response: {response.text[:200]}")
                return None

        except Exception as e:
            print(f"   ❌ Error submitting report: {e}")
            return None

    async def verify_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Run verification on a report"""
        try:
            response = await self.client.post(
                f"/verification/verify/{report_id}",
                headers=self.get_headers()
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("data") or data
            else:
                print(f"   ❌ Verification failed: {response.status_code}")
                print(f"      Response: {response.text[:200]}")
                return None

        except Exception as e:
            print(f"   ❌ Error during verification: {e}")
            return None

    async def get_verification_result(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Get verification result for a report"""
        try:
            response = await self.client.get(
                f"/verification/result/{report_id}",
                headers=self.get_headers()
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("data") or data
            else:
                return None

        except Exception as e:
            print(f"   ⚠️  Could not get verification result: {e}")
            return None

    def print_verification_result(self, result: Dict[str, Any]):
        """Pretty print verification result"""
        print(f"\n   📊 VERIFICATION RESULT:")
        print(f"   ├── Verification ID: {result.get('verification_id', 'N/A')}")
        print(f"   ├── Composite Score: {result.get('composite_score', 0):.2f}%")
        print(f"   ├── Decision: {result.get('decision', 'N/A')}")
        print(f"   ├── Reason: {result.get('decision_reason', 'N/A')}")
        print(f"   ├── Processing Time: {result.get('processing_time_ms', 0)}ms")

        # Print layer results
        layer_results = result.get('layer_results', [])
        if layer_results:
            print(f"   └── Layer Results:")
            for i, layer in enumerate(layer_results):
                prefix = "       ├──" if i < len(layer_results) - 1 else "       └──"
                status_icon = "✅" if layer.get('status') == 'pass' else "❌" if layer.get('status') == 'fail' else "⏭️"
                print(f"   {prefix} {layer.get('layer_name', 'unknown')}: {status_icon} {layer.get('status')} (score: {layer.get('score', 0):.2f}, weight: {layer.get('weight', 0):.2f})")

    async def run_scenario(self, scenario_name: str, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single test scenario"""
        print(f"\n   Description: {scenario['description']}")

        result = {
            "scenario": scenario_name,
            "passed": False,
            "report_id": None,
            "verification_result": None,
            "errors": []
        }

        # Step 1: Submit the report
        report_id = await self.submit_hazard_report(scenario["report_data"])
        if not report_id:
            result["errors"].append("Failed to submit report")
            return result

        result["report_id"] = report_id

        # Step 2: Run verification
        verification_result = await self.verify_report(report_id)
        if not verification_result:
            # Try to get existing result
            verification_result = await self.get_verification_result(report_id)

        if not verification_result:
            result["errors"].append("Failed to get verification result")
            return result

        result["verification_result"] = verification_result
        self.print_verification_result(verification_result)

        # Step 3: Validate the result
        actual_decision = verification_result.get("decision")
        expected_decision = scenario.get("expected_decision")
        actual_score = verification_result.get("composite_score", 0)

        # Check decision
        if actual_decision == expected_decision:
            print(f"\n   ✅ Decision matches: {actual_decision}")
            result["passed"] = True
        else:
            print(f"\n   ❌ Decision mismatch!")
            print(f"      Expected: {expected_decision}")
            print(f"      Actual: {actual_decision}")
            result["errors"].append(f"Decision mismatch: expected {expected_decision}, got {actual_decision}")

        # Check score thresholds
        if "expected_min_score" in scenario:
            if actual_score >= scenario["expected_min_score"]:
                print(f"   ✅ Score >= {scenario['expected_min_score']}%: {actual_score:.2f}%")
            else:
                print(f"   ❌ Score < {scenario['expected_min_score']}%: {actual_score:.2f}%")
                result["passed"] = False
                result["errors"].append(f"Score too low: {actual_score:.2f}% < {scenario['expected_min_score']}%")

        if "expected_max_score" in scenario:
            if actual_score <= scenario["expected_max_score"]:
                print(f"   ✅ Score <= {scenario['expected_max_score']}%: {actual_score:.2f}%")
            else:
                print(f"   ❌ Score > {scenario['expected_max_score']}%: {actual_score:.2f}%")
                result["passed"] = False
                result["errors"].append(f"Score too high: {actual_score:.2f}% > {scenario['expected_max_score']}%")

        return result

    async def run_all_tests(self):
        """Run all test scenarios"""
        print("\n" + "="*60)
        print("🧪 6-LAYER VERIFICATION LOOP TEST SUITE")
        print("="*60)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        await self.setup()

        # Check service health
        if not await self.check_verification_health():
            print("\n❌ Verification service is not available. Aborting tests.")
            await self.cleanup()
            return

        # Authenticate
        await self.authenticate()

        # Run each scenario
        for scenario_name, scenario in TEST_SCENARIOS.items():
            print("\n" + "-"*60)
            print(f"📋 TEST SCENARIO: {scenario_name.upper()}")
            print("-"*60)

            try:
                result = await self.run_scenario(scenario_name, scenario)
                self.test_results[scenario_name] = result
            except Exception as e:
                print(f"   ❌ Scenario failed with error: {e}")
                self.test_results[scenario_name] = {
                    "scenario": scenario_name,
                    "passed": False,
                    "errors": [str(e)]
                }

        # Print summary
        self.print_summary()

        await self.cleanup()

    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)

        total = len(self.test_results)
        passed = sum(1 for r in self.test_results.values() if r.get("passed"))
        failed = total - passed

        for scenario_name, result in self.test_results.items():
            status = "✅ PASSED" if result.get("passed") else "❌ FAILED"
            print(f"   {status} - {scenario_name}")
            if result.get("errors"):
                for error in result["errors"]:
                    print(f"            └── {error}")

        print("\n" + "-"*60)
        print(f"   Total: {total} | Passed: {passed} | Failed: {failed}")
        print(f"   Success Rate: {(passed/total)*100:.1f}%")
        print("="*60)

        return passed == total


async def test_verification_directly():
    """Direct API test without report submission (for quick testing)"""
    print("\n" + "="*60)
    print("🔬 DIRECT VERIFICATION API TEST")
    print("="*60)

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT) as client:
        # Test 1: Check health
        print("\n1️⃣  Testing /verification/health")
        response = await client.get("/verification/health")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Initialized: {data.get('initialized')}")
            print(f"   Layers: {data.get('layers')}")
            print("   ✅ Health check passed")
        else:
            print("   ❌ Health check failed")

        # Test 2: Check thresholds
        print("\n2️⃣  Testing /verification/thresholds")
        response = await client.get("/verification/thresholds")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            thresholds = data.get("data", data)
            print(f"   Auto-approve threshold: {thresholds.get('auto_approve_threshold')}%")
            print(f"   Manual review threshold: {thresholds.get('manual_review_threshold')}%")
            print(f"   Geofence inland limit: {thresholds.get('geofence_inland_limit_km')}km")
            print("   ✅ Thresholds retrieved")
        else:
            print("   ❌ Failed to get thresholds")

        # Test 3: Check stats
        print("\n3️⃣  Testing /verification/stats")
        response = await client.get("/verification/stats")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            stats = data.get("data", data)
            print(f"   Total verifications: {stats.get('total_verifications', 0)}")
            print(f"   Auto-approved: {stats.get('auto_approved_count', 0)}")
            print(f"   Manual review: {stats.get('manual_review_count', 0)}")
            print(f"   Rejected: {stats.get('rejected_count', 0)}")
            print(f"   Auto-rejected: {stats.get('auto_rejected_count', 0)}")
            print("   ✅ Stats retrieved")
        else:
            print("   ❌ Failed to get stats")


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Test 6-Layer Verification Loop")
    parser.add_argument("--quick", action="store_true", help="Run quick API tests only")
    parser.add_argument("--full", action="store_true", help="Run full test suite with report submission")
    args = parser.parse_args()

    if args.quick or (not args.quick and not args.full):
        # Default: run quick tests
        await test_verification_directly()

    if args.full:
        # Run full test suite
        tester = VerificationLoopTester()
        await tester.run_all_tests()


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════╗
║     COASTGUARDIAN - VERIFICATION LOOP TEST SUITE             ║
║     Testing 6-Layer Verification Pipeline                    ║
╚══════════════════════════════════════════════════════════════╝

Layers tested:
  1. Geofence Layer - Validates coastal proximity
  2. Weather Layer - Correlates with weather conditions
  3. Text Layer - NLP analysis of description
  4. Image Layer - Vision model classification
  5. Reporter Layer - User credibility scoring

Decision thresholds:
  • AUTO_APPROVED: Score >= 75%
  • MANUAL_REVIEW: Score 40-75%
  • REJECTED: Score < 40%
  • AUTO_REJECTED: Geofence failure
""")

    asyncio.run(main())
