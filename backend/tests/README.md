# CoastGuardians Verification System Test Suite

Comprehensive test suite for the 6-layer hazard verification system.

## Overview

This test suite validates the CoastGuardians verification pipeline which processes coastal hazard reports through multiple validation layers:

1. **Geofence Layer** (20% weight) - Validates location is within India's coastal EEZ
2. **Weather Layer** (25% weight) - Cross-references with weather data
3. **Text Analysis Layer** (25% weight) - Analyzes description for hazard indicators
4. **Image Analysis Layer** (20% weight) - Validates images using vision AI
5. **Reporter Trust Layer** (10% weight) - Evaluates reporter credibility
6. **Final Decision** - Aggregates scores and makes verification decision

## Quick Start

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov pytest-xdist Pillow

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific hazard type tests
pytest -m "hazard_type(tsunami)"

# Run only unit tests
pytest -m unit

# Run in parallel (faster)
pytest -n auto
```

## Test Structure

```
tests/
├── conftest.py                           # Shared fixtures and configuration
├── pytest.ini                            # Pytest configuration (in parent dir)
├── test_hazard_verification_scenarios.py # Main test file with all scenarios
├── test_verification_complete.py         # Legacy complete workflow tests
├── test_verification_loop.py             # Legacy loop tests
├── generate_test_images.py               # Test image generator script
├── fixtures/
│   ├── __init__.py                       # Fixture exports
│   ├── locations.py                      # Coastal/inland location data
│   ├── hazard_data.py                    # Hazard descriptions and keywords
│   ├── reporter_data.py                  # Reporter profile fixtures
│   └── images/                           # Generated test images
└── README.md                             # This file
```

## Test Categories

### By Hazard Type (10 categories)

**Natural Hazards:**
- `TestTsunamiVerification` - Tsunami detection and verification
- `TestCycloneVerification` - Cyclone/tropical storm verification
- `TestHighWavesVerification` - Abnormal wave verification
- `TestFloodedCoastlineVerification` - Coastal flooding verification
- `TestRipCurrentVerification` - Rip current danger verification

**Human-Made Hazards:**
- `TestBeachedAnimalVerification` - Marine animal stranding
- `TestShipWreckVerification` - Maritime vessel incidents
- `TestMarineDebrisVerification` - Plastic/debris pollution
- `TestOilSpillVerification` - Oil contamination events
- `TestOtherHazardVerification` - Miscellaneous coastal hazards

### Special Test Classes

- `TestEdgeCases` - Boundary conditions and unusual inputs
- `TestPerformance` - Speed and throughput tests
- `TestIntegration` - Full workflow integration tests

## Test Markers

```bash
# Run by marker
pytest -m slow              # Long-running tests
pytest -m integration       # Integration tests only
pytest -m unit              # Unit tests only
pytest -m natural_hazard    # Natural disaster tests
pytest -m human_made_hazard # Human-caused hazard tests
pytest -m edge_case         # Edge case tests
pytest -m performance       # Performance benchmarks
```

## Fixtures

### Location Fixtures

```python
# Coastal locations (valid)
@pytest.fixture
def coastal_locations():
    return {
        "mumbai_coast": {"latitude": 18.9388, "longitude": 72.8354, ...},
        "chennai_marina": {"latitude": 13.0499, "longitude": 80.2824, ...},
        # ... 15 coastal locations
    }

# Inland locations (should fail geofence)
@pytest.fixture
def inland_locations():
    return {
        "delhi": {"latitude": 28.6139, "longitude": 77.2090, ...},
        # ... 7 inland locations
    }
```

### Reporter Fixtures

```python
@pytest.fixture
def reporter_profiles():
    return {
        "verified_authority": {"trust_score": 0.95, ...},
        "trusted_analyst": {"trust_score": 0.85, ...},
        "experienced_citizen": {"trust_score": 0.75, ...},
        "new_citizen": {"trust_score": 0.50, ...},
        "suspected_spammer": {"trust_score": 0.10, ...},
    }
```

### Weather Fixtures

```python
@pytest.fixture
def weather_conditions():
    return {
        "tsunami_conditions": {"wave_height": 8.5, "alerts": ["TSUNAMI_WARNING"], ...},
        "cyclone_conditions": {"wind_speed": 120, "alerts": ["CYCLONE_WARNING"], ...},
        "calm_conditions": {"wave_height": 0.5, "alerts": [], ...},
    }
```

## Verification Thresholds

The system uses these decision thresholds:

| Final Score | Decision |
|-------------|----------|
| >= 75% | Auto-approve |
| 40-75% | Manual review |
| < 40% | Auto-reject |
| Geofence fail | Immediate reject |

## Layer Weights

| Layer | Weight | Notes |
|-------|--------|-------|
| Geofence | 20% | Pass/fail, must pass for continuation |
| Weather | 25% | Corroborates natural hazard reports |
| Text Analysis | 25% | Keyword and context analysis |
| Image Analysis | 20% | Vision AI validation |
| Reporter Trust | 10% | Historical credibility |

**Note:** If a layer is skipped (e.g., no image provided), its weight is redistributed proportionally to other layers.

## Test Scenarios

### Auto-Approve Scenarios
- Authority reports emergency with supporting weather data
- High-quality report with all layers passing

### Manual Review Scenarios
- New user submits valid-looking report
- Mixed signals from different layers

### Auto-Reject Scenarios
- Report from inland location (geofence fail)
- Spam content detected
- All layers return low scores

### Edge Cases
- Borderline locations (just inside/outside EEZ)
- Minimal text descriptions
- Missing image with image-required hazard type
- Contrary weather conditions
- Rapid successive reports (spam detection)

## Generating Test Images

```bash
# Generate test images for all hazard types
python tests/generate_test_images.py

# Images saved to tests/fixtures/images/
```

Generated images include:
- Standard (1920x1080)
- Mobile portrait (1080x1920)
- Low resolution (640x480)
- Edge cases (tiny, blurred, dark, etc.)

## Coverage Requirements

Target coverage: **70%** minimum

Key areas to cover:
- All 10 hazard types
- All verification layers
- All decision paths (approve/review/reject)
- Error handling
- Edge cases

## Running Tests in CI/CD

```yaml
# Example GitHub Actions workflow
test:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-asyncio pytest-cov
    - name: Run tests
      run: pytest --cov=app --cov-report=xml
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

## Writing New Tests

### Test Template

```python
@pytest.mark.hazard_type("new_hazard")
class TestNewHazardVerification:
    """Tests for new hazard type verification."""

    @pytest.mark.asyncio
    async def test_basic_detection(self, create_test_report, mock_db):
        """Test basic hazard detection."""
        report = create_test_report(
            hazard_type="new_hazard",
            location_key="mumbai_coast",
            description_quality="high_quality"
        )

        result = await verify_report(report, mock_db)

        assert result.status in ["verified", "pending_review"]
        assert result.geofence_passed == True

    @pytest.mark.asyncio
    async def test_rejection_scenario(self, create_test_report, mock_db):
        """Test rejection for invalid report."""
        report = create_test_report(
            hazard_type="new_hazard",
            location_key="delhi",  # Inland - should fail
            description_quality="low_quality"
        )

        result = await verify_report(report, mock_db)

        assert result.status == "rejected"
        assert result.rejection_reason == "outside_coastal_zone"
```

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure you're running from the backend directory
   ```bash
   cd backend
   pytest tests/
   ```

2. **Async test failures**: Make sure `pytest-asyncio` is installed
   ```bash
   pip install pytest-asyncio
   ```

3. **Image generation fails**: Install Pillow
   ```bash
   pip install Pillow
   ```

4. **Database mock issues**: Use the `mock_db` fixture from conftest.py

### Debug Mode

```bash
# Run with verbose output
pytest -v --tb=long

# Run single test with print statements
pytest tests/test_hazard_verification_scenarios.py::TestTsunamiVerification::test_basic_detection -s
```

## Contributing

1. Add tests for any new hazard types
2. Maintain minimum 70% coverage
3. Use appropriate markers for new tests
4. Update fixtures when adding new test data
5. Document edge cases discovered during testing
