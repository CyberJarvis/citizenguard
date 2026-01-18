"""
Location Test Fixtures
Contains predefined coastal and non-coastal locations for testing.
"""

# Valid coastal locations within India's EEZ
COASTAL_LOCATIONS = {
    "mumbai_coast": {
        "latitude": 18.9388,
        "longitude": 72.8354,
        "name": "Mumbai Coast",
        "state": "Maharashtra",
        "is_coastal": True
    },
    "chennai_marina": {
        "latitude": 13.0499,
        "longitude": 80.2824,
        "name": "Chennai Marina Beach",
        "state": "Tamil Nadu",
        "is_coastal": True
    },
    "goa_calangute": {
        "latitude": 15.5449,
        "longitude": 73.7533,
        "name": "Calangute Beach",
        "state": "Goa",
        "is_coastal": True
    },
    "kerala_kovalam": {
        "latitude": 8.3988,
        "longitude": 76.9789,
        "name": "Kovalam Beach",
        "state": "Kerala",
        "is_coastal": True
    },
    "andaman_port_blair": {
        "latitude": 11.6234,
        "longitude": 92.7265,
        "name": "Port Blair",
        "territory": "Andaman and Nicobar",
        "is_coastal": True
    },
    "vishakhapatnam": {
        "latitude": 17.6868,
        "longitude": 83.2185,
        "name": "Vishakhapatnam Coast",
        "state": "Andhra Pradesh",
        "is_coastal": True
    },
    "sundarbans": {
        "latitude": 21.9497,
        "longitude": 88.8950,
        "name": "Sundarbans Delta",
        "state": "West Bengal",
        "is_coastal": True
    },
    "lakshadweep_kavaratti": {
        "latitude": 10.5669,
        "longitude": 72.6411,
        "name": "Kavaratti Island",
        "territory": "Lakshadweep",
        "is_coastal": True
    },
    "puri_beach": {
        "latitude": 19.7983,
        "longitude": 85.8249,
        "name": "Puri Beach",
        "state": "Odisha",
        "is_coastal": True
    },
    "diu_beach": {
        "latitude": 20.7144,
        "longitude": 70.9871,
        "name": "Diu Beach",
        "territory": "Daman and Diu",
        "is_coastal": True
    },
    "kanyakumari": {
        "latitude": 8.0883,
        "longitude": 77.5385,
        "name": "Kanyakumari",
        "state": "Tamil Nadu",
        "is_coastal": True
    },
    "digha_beach": {
        "latitude": 21.6278,
        "longitude": 87.5197,
        "name": "Digha Beach",
        "state": "West Bengal",
        "is_coastal": True
    },
    "karwar_beach": {
        "latitude": 14.8133,
        "longitude": 74.1295,
        "name": "Karwar Beach",
        "state": "Karnataka",
        "is_coastal": True
    },
    "mandvi_beach": {
        "latitude": 22.8371,
        "longitude": 69.3540,
        "name": "Mandvi Beach",
        "state": "Gujarat",
        "is_coastal": True
    },
    "pondicherry_beach": {
        "latitude": 11.9139,
        "longitude": 79.8145,
        "name": "Pondicherry Beach",
        "territory": "Puducherry",
        "is_coastal": True
    }
}

# Invalid inland locations (for geofence rejection tests)
INLAND_LOCATIONS = {
    "delhi": {
        "latitude": 28.6139,
        "longitude": 77.2090,
        "name": "New Delhi",
        "state": "Delhi",
        "is_coastal": False
    },
    "jaipur": {
        "latitude": 26.9124,
        "longitude": 75.7873,
        "name": "Jaipur",
        "state": "Rajasthan",
        "is_coastal": False
    },
    "lucknow": {
        "latitude": 26.8467,
        "longitude": 80.9462,
        "name": "Lucknow",
        "state": "Uttar Pradesh",
        "is_coastal": False
    },
    "nagpur": {
        "latitude": 21.1458,
        "longitude": 79.0882,
        "name": "Nagpur",
        "state": "Maharashtra",
        "is_coastal": False
    },
    "bangalore": {
        "latitude": 12.9716,
        "longitude": 77.5946,
        "name": "Bangalore",
        "state": "Karnataka",
        "is_coastal": False
    },
    "hyderabad": {
        "latitude": 17.3850,
        "longitude": 78.4867,
        "name": "Hyderabad",
        "state": "Telangana",
        "is_coastal": False
    },
    "bhopal": {
        "latitude": 23.2599,
        "longitude": 77.4126,
        "name": "Bhopal",
        "state": "Madhya Pradesh",
        "is_coastal": False
    }
}

# International waters / outside EEZ
INTERNATIONAL_WATERS = {
    "mid_indian_ocean": {
        "latitude": 0.0,
        "longitude": 75.0,
        "name": "Mid Indian Ocean",
        "is_coastal": False,
        "is_eez": False
    },
    "near_maldives": {
        "latitude": 4.1755,
        "longitude": 73.5093,
        "name": "Near Maldives",
        "is_coastal": False,
        "is_eez": False
    },
    "arabian_sea_deep": {
        "latitude": 15.0,
        "longitude": 65.0,
        "name": "Deep Arabian Sea",
        "is_coastal": False,
        "is_eez": False
    },
    "bay_of_bengal_deep": {
        "latitude": 10.0,
        "longitude": 88.0,
        "name": "Deep Bay of Bengal",
        "is_coastal": False,
        "is_eez": False
    }
}

# Borderline locations (for edge case testing)
BORDERLINE_LOCATIONS = {
    "just_inside_eez": {
        "latitude": 18.0,
        "longitude": 71.5,
        "name": "Just Inside EEZ",
        "is_coastal": True,
        "distance_from_boundary_km": 5
    },
    "just_outside_eez": {
        "latitude": 18.0,
        "longitude": 70.0,
        "name": "Just Outside EEZ",
        "is_coastal": False,
        "distance_from_boundary_km": 5
    },
    "coastal_boundary": {
        "latitude": 19.0,
        "longitude": 72.8,
        "name": "Near Coast Boundary",
        "is_coastal": True,
        "distance_from_coast_km": 0.5
    }
}
