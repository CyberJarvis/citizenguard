"""
Hazard Test Data Fixtures
Contains hazard descriptions, keywords, and weather conditions for testing.
"""

# =============================================================================
# HAZARD DESCRIPTIONS BY TYPE AND QUALITY
# =============================================================================

HAZARD_DESCRIPTIONS = {
    "tsunami": {
        "high_quality": """URGENT: Massive tsunami wave approaching! Witnessed huge water
        withdrawal from shore followed by 10+ meter wall of water. Destruction along
        2km of coastline. Multiple buildings damaged. Immediate evacuation needed!
        Location: Marina Beach, Chennai. Time: 14:30 IST. Many people trapped.
        Water receding rapidly then surging back with tremendous force.""",

        "medium_quality": """Big wave came and flooded the beach area. Lot of water
        came very fast. Some boats damaged. People running away. Very scary.""",

        "low_quality": """wave big water bad help""",

        "spam": """FREE IPHONE CLICK HERE tsunami tsunami tsunami BUY NOW"""
    },
    "cyclone": {
        "high_quality": """EMERGENCY: Category 4 cyclone making landfall! Winds exceeding
        180 km/h. Heavy rainfall, storm surge of 4 meters expected. Trees uprooted,
        power lines down. Roof of several houses blown away. District: Puri, Odisha.
        Evacuation shelters full. Need immediate rescue operations. Eye of storm
        visible. Barometric pressure dropping rapidly to 950 hPa.""",

        "medium_quality": """Very strong storm hitting coastal area. Strong winds
        damaging houses. Heavy rain. Many trees fallen on roads. No electricity.""",

        "low_quality": """storm wind rain bad""",

        "spam": """MAKE MONEY FROM HOME cyclone alert fake news CLICK HERE"""
    },
    "high_waves": {
        "high_quality": """WARNING: Abnormally high waves of 5-6 meters observed at
        Kovalam Beach. Several tourists caught off-guard. One person swept away.
        Fishermen advised not to venture into sea. Coast guard patrolling area.
        Expected to continue for next 6 hours due to distant storm system.
        Wave period approximately 12 seconds. Breaking waves very powerful.""",

        "medium_quality": """Very big waves at beach today. Higher than normal.
        Some people got wet. Dangerous to swim. Lifeguards warning everyone.""",

        "low_quality": """waves big water""",

        "spam": """HIGH WAVES of PROFIT! Invest now! big waves at beach"""
    },
    "flooded_coastline": {
        "high_quality": """ALERT: Severe coastal flooding in Sundarbans area.
        Embankments breached in 3 locations. Saltwater inundation affecting
        5 villages. Estimated 2000 hectares of farmland submerged.
        Relief camps being set up. Fresh water shortage reported.
        Floodwater level 1.5 meters above normal high tide mark.""",

        "medium_quality": """Water flooding into village from sea side. Many houses
        have water inside. Roads not passable. People moving to higher ground.""",

        "low_quality": """water everywhere flood""",

        "spam": """FLOODED with CASH! Work from home! coastal flood maybe"""
    },
    "rip_current": {
        "high_quality": """DANGER: Strong rip current identified at Palolem Beach,
        Goa. Width approximately 10 meters, extending 100 meters offshore.
        Two swimmers rescued this morning. Lifeguards on alert. Red flags deployed.
        Current strongest during low tide, between 2-5 PM. Visible foam line
        and discolored water channel indicating rip location.""",

        "medium_quality": """Dangerous water current at beach pulling people out.
        Swimmers getting dragged away. Lifeguard made rescue. Be careful.""",

        "low_quality": """water pulling strong""",

        "spam": """RIP CURRENT prices! Sale sale sale! current in water maybe"""
    },
    "beached_animal": {
        "high_quality": """WILDLIFE EMERGENCY: Pod of 15 pilot whales stranded at
        Tiruchendur Beach, Tamil Nadu. 8 adults, 7 juveniles. Most still alive
        but stressed. Marine biologists contacted. Volunteers keeping whales wet.
        Immediate help needed for refloating operation before high tide at 18:00.
        Animals showing signs of dehydration. GPS coordinates shared with wildlife dept.""",

        "medium_quality": """Found big whale on beach. It's still breathing but
        can't move. Some other dolphins also nearby. Please send help quickly.""",

        "low_quality": """big fish beach help""",

        "spam": """BEACHED whale of DEALS! Shop now! animal on beach maybe"""
    },
    "ship_wreck": {
        "high_quality": """MARITIME EMERGENCY: Cargo vessel MV Ocean Star capsized
        near Mandvi Port, Gujarat. 12 crew members, 5 rescued, 7 missing.
        Vessel carrying 500 tons of cargo, possible fuel leak detected.
        Coast Guard and Navy dispatched. Coordinates: 22.8408N, 69.3520E.
        Weather deteriorating, rescue operations challenging. Ship listing 45 degrees.""",

        "medium_quality": """Ship sinking near port area. Can see it tilting badly.
        Some people in water. Rescue boats going. Oil visible in water around ship.""",

        "low_quality": """boat sink water people""",

        "spam": """SINKING prices! Ship your orders FREE! boat accident maybe"""
    },
    "marine_debris": {
        "high_quality": """POLLUTION ALERT: Massive plastic debris accumulation at
        Versova Beach, Mumbai. Estimated 50 tons of plastic waste washed ashore
        after monsoon. Includes fishing nets, plastic bottles, medical waste.
        Wildlife entanglement reported - 3 sea turtles affected. Beach cleanup
        drive organized for weekend. Marine ecosystem severely impacted.
        Debris spread across 2km stretch of shoreline.""",

        "medium_quality": """Lots of plastic and garbage on beach. Dead fish also
        seen. Smell is very bad. Need cleanup soon. Tourism affected.""",

        "low_quality": """garbage beach dirty""",

        "spam": """DEBRIS-FREE lifestyle! Buy our products! garbage on beach"""
    },
    "oil_spill": {
        "high_quality": """ENVIRONMENTAL EMERGENCY: Major oil spill detected 15km
        off Mumbai coast. Source: Suspected tanker leak. Oil slick spreading,
        currently 3km x 500m. Tar balls reaching Juhu Beach. Strong petroleum odor.
        Marine life affected - dead fish washing up. Immediate containment required.
        ONGC and Coast Guard notified. Wind pushing slick towards shore.""",

        "medium_quality": """Oil in water near beach. Black sticky substance on
        sand. Bad smell. Some dead fish. People complaining of headaches from smell.""",

        "low_quality": """black water oil bad""",

        "spam": """OIL your investments! Slippery deals! oil spill maybe happening"""
    },
    "other": {
        "high_quality": """UNUSUAL SIGHTING: Large unidentified floating structure
        spotted 5km off Kochi coast. Appears to be abandoned fishing platform.
        Approximately 20x15 meters. Partially submerged, navigation hazard.
        No visible markings or ownership indicators. Drifting towards shore.
        Coast guard informed. Requesting investigation of origin and ownership.""",

        "medium_quality": """Something strange floating in sea near beach.
        Looks like some kind of structure. Could be dangerous for boats passing by.""",

        "low_quality": """strange thing water""",

        "spam": """STRANGE but true! Make money online! something in water"""
    }
}

# =============================================================================
# HAZARD KEYWORDS FOR TEXT ANALYSIS
# =============================================================================

HAZARD_KEYWORDS = {
    "tsunami": [
        "tsunami", "tidal wave", "giant wave", "water wall", "sea withdrawal",
        "earthquake wave", "massive flooding", "coastal surge", "ocean surge",
        "seismic wave", "harbor wave", "mega wave"
    ],
    "cyclone": [
        "cyclone", "hurricane", "typhoon", "tropical storm", "severe storm",
        "high winds", "storm surge", "eye of storm", "wind speed", "landfall",
        "low pressure", "rotating storm", "violent storm"
    ],
    "high_waves": [
        "high waves", "big waves", "rough sea", "dangerous waves", "surf warning",
        "wave height", "swell", "breakers", "powerful waves", "abnormal waves",
        "sea state", "wave period"
    ],
    "flooded_coastline": [
        "flood", "flooding", "inundation", "water level", "breach", "overflow",
        "submerged", "waterlogged", "coastal flooding", "tidal flooding",
        "high tide", "embankment failure", "saltwater intrusion"
    ],
    "rip_current": [
        "rip current", "undertow", "rip tide", "strong current", "pulled out",
        "dragged out", "dangerous current", "swimmer rescue", "water channel",
        "foam line", "escape current", "lateral current"
    ],
    "beached_animal": [
        "beached", "stranded", "whale", "dolphin", "sea turtle", "marine animal",
        "washed up", "stuck on beach", "marine mammal", "cetacean", "rescue animal",
        "wildlife emergency", "pod stranding"
    ],
    "ship_wreck": [
        "ship", "vessel", "boat", "sinking", "capsized", "wreck", "maritime",
        "crew", "rescue", "coast guard", "navy", "mayday", "distress",
        "collision", "grounded", "listing"
    ],
    "marine_debris": [
        "plastic", "garbage", "debris", "pollution", "waste", "trash", "litter",
        "fishing net", "ghost net", "microplastic", "marine pollution",
        "beach cleanup", "ocean garbage", "marine litter"
    ],
    "oil_spill": [
        "oil", "spill", "leak", "petroleum", "tar ball", "slick", "contamination",
        "fuel leak", "tanker", "pipeline", "crude oil", "diesel", "bunker fuel",
        "hydrocarbon", "oily sheen"
    ]
}

# =============================================================================
# WEATHER CONDITIONS BY SCENARIO
# =============================================================================

WEATHER_CONDITIONS = {
    "tsunami_conditions": {
        "wave_height": 8.5,
        "wind_speed": 45,
        "sea_state": "very rough",
        "pressure": 990,
        "visibility": 5000,
        "alerts": ["TSUNAMI_WARNING"],
        "temperature": 28,
        "humidity": 85,
        "description": "Post-earthquake tsunami conditions"
    },
    "cyclone_conditions": {
        "wave_height": 6.0,
        "wind_speed": 120,
        "sea_state": "phenomenal",
        "pressure": 960,
        "visibility": 2000,
        "alerts": ["CYCLONE_WARNING", "STORM_SURGE"],
        "temperature": 26,
        "humidity": 95,
        "description": "Active cyclone landfall"
    },
    "high_wave_conditions": {
        "wave_height": 4.5,
        "wind_speed": 35,
        "sea_state": "rough",
        "pressure": 1005,
        "visibility": 8000,
        "alerts": ["HIGH_WAVE_ALERT"],
        "temperature": 29,
        "humidity": 75,
        "description": "Distant storm causing high waves"
    },
    "flood_conditions": {
        "wave_height": 2.5,
        "wind_speed": 25,
        "sea_state": "moderate",
        "pressure": 1000,
        "visibility": 4000,
        "alerts": ["FLOOD_WARNING"],
        "temperature": 27,
        "humidity": 90,
        "rainfall_24h": 150,
        "description": "Monsoon flooding conditions"
    },
    "rip_current_conditions": {
        "wave_height": 2.0,
        "wind_speed": 20,
        "sea_state": "moderate",
        "pressure": 1010,
        "visibility": 10000,
        "alerts": ["RIP_CURRENT_RISK"],
        "temperature": 30,
        "humidity": 70,
        "description": "Beach conditions favoring rip currents"
    },
    "calm_conditions": {
        "wave_height": 0.5,
        "wind_speed": 8,
        "sea_state": "calm",
        "pressure": 1015,
        "visibility": 15000,
        "alerts": [],
        "temperature": 31,
        "humidity": 65,
        "description": "Fair weather conditions"
    },
    "monsoon_conditions": {
        "wave_height": 3.0,
        "wind_speed": 40,
        "sea_state": "rough",
        "pressure": 995,
        "visibility": 3000,
        "alerts": ["MONSOON_ACTIVE"],
        "temperature": 25,
        "humidity": 95,
        "rainfall_24h": 100,
        "description": "Active monsoon conditions"
    },
    "contrary_conditions": {
        "wave_height": 0.3,
        "wind_speed": 5,
        "sea_state": "calm",
        "pressure": 1020,
        "visibility": 20000,
        "alerts": [],
        "temperature": 32,
        "humidity": 60,
        "description": "Perfect weather - contradicts severe hazard reports"
    }
}

# =============================================================================
# SEVERITY LEVELS
# =============================================================================

SEVERITY_LEVELS = {
    "critical": {
        "level": 5,
        "response_time_minutes": 15,
        "requires_evacuation": True,
        "multi_agency": True
    },
    "severe": {
        "level": 4,
        "response_time_minutes": 30,
        "requires_evacuation": True,
        "multi_agency": True
    },
    "high": {
        "level": 3,
        "response_time_minutes": 60,
        "requires_evacuation": False,
        "multi_agency": False
    },
    "moderate": {
        "level": 2,
        "response_time_minutes": 120,
        "requires_evacuation": False,
        "multi_agency": False
    },
    "low": {
        "level": 1,
        "response_time_minutes": 240,
        "requires_evacuation": False,
        "multi_agency": False
    }
}

# =============================================================================
# HAZARD TYPE CONFIGURATIONS
# =============================================================================

HAZARD_TYPE_CONFIG = {
    "tsunami": {
        "category": "natural",
        "typical_severity": "critical",
        "weather_dependent": True,
        "requires_image": False,
        "expected_keywords_min": 2
    },
    "cyclone": {
        "category": "natural",
        "typical_severity": "critical",
        "weather_dependent": True,
        "requires_image": False,
        "expected_keywords_min": 2
    },
    "high_waves": {
        "category": "natural",
        "typical_severity": "high",
        "weather_dependent": True,
        "requires_image": True,
        "expected_keywords_min": 1
    },
    "flooded_coastline": {
        "category": "natural",
        "typical_severity": "severe",
        "weather_dependent": True,
        "requires_image": True,
        "expected_keywords_min": 2
    },
    "rip_current": {
        "category": "natural",
        "typical_severity": "high",
        "weather_dependent": True,
        "requires_image": False,
        "expected_keywords_min": 1
    },
    "beached_animal": {
        "category": "human_made",
        "typical_severity": "moderate",
        "weather_dependent": False,
        "requires_image": True,
        "expected_keywords_min": 2
    },
    "ship_wreck": {
        "category": "human_made",
        "typical_severity": "critical",
        "weather_dependent": False,
        "requires_image": True,
        "expected_keywords_min": 2
    },
    "marine_debris": {
        "category": "human_made",
        "typical_severity": "moderate",
        "weather_dependent": False,
        "requires_image": True,
        "expected_keywords_min": 2
    },
    "oil_spill": {
        "category": "human_made",
        "typical_severity": "severe",
        "weather_dependent": False,
        "requires_image": True,
        "expected_keywords_min": 2
    },
    "other": {
        "category": "other",
        "typical_severity": "low",
        "weather_dependent": False,
        "requires_image": True,
        "expected_keywords_min": 0
    }
}
