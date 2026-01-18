"""
Coast Guardian LLM Client - Groq Cloud API
Production-ready LLM integration for social media analysis
"""
import requests
import json
import os
from typing import Dict, List, Optional
import logging

class CoastGuardianLLM:
    def __init__(self,
                 groq_api_key: str = None,
                 model_name: str = "llama-3.1-8b-instant"):
        """
        Initialize LLM client with Groq Cloud API

        Args:
            groq_api_key: Groq API key (defaults to GROQ_API_KEY env var)
            model_name: Model to use (default: llama-3.1-8b-instant)
        """
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        if not self.groq_api_key:
            self.logger.warning("GROQ_API_KEY not set - LLM features will use mock responses")
        self.groq_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model_name = model_name
        self.logger = logging.getLogger(__name__)

        # Available Groq models (updated Dec 2025)
        self.groq_models = [
            "llama-3.1-8b-instant",      # Fast, good for classification (default)
            "llama-3.3-70b-versatile",   # Most powerful
            "mixtral-8x7b-32768",        # Good balance
            "gemma2-9b-it",              # Google's model
        ]

    def is_available(self) -> bool:
        """Check if Groq API is available"""
        try:
            headers = {
                "Authorization": f"Bearer {self.groq_api_key}",
                "Content-Type": "application/json"
            }
            response = requests.get(
                "https://api.groq.com/openai/v1/models",
                headers=headers,
                timeout=5
            )
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def list_models(self) -> List[Dict]:
        """List available Groq models"""
        return [{"name": m, "provider": "groq"} for m in self.groq_models]

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate text using Groq API"""
        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json"
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1024,
        }

        try:
            response = requests.post(
                self.groq_url,
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                self.logger.error(f"Groq API error: {response.status_code} - {response.text}")
                return self._get_mock_response(prompt)

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Groq request error: {e}")
            return self._get_mock_response(prompt)

    def _get_mock_response(self, prompt: str) -> str:
        """Mock response for development when model is unavailable"""
        prompt_lower = prompt.lower()

        # Enhanced disaster type detection
        if any(word in prompt_lower for word in ["tsunami", "wave", "waves", "evacuate", "coast", "coastal", "flood"]):
            return """{
                "relevance_score": 9,
                "disaster_type": "tsunami",
                "urgency": "critical",
                "sentiment": "negative",
                "keywords": ["tsunami", "waves", "warning", "coast", "evacuate"],
                "credibility_indicators": ["urgent_language", "location_specific"]
            }"""
        elif any(word in prompt_lower for word in ["cyclone", "hurricane", "storm", "wind", "tropical"]):
            return """{
                "relevance_score": 8,
                "disaster_type": "cyclone",
                "urgency": "high",
                "sentiment": "negative",
                "keywords": ["cyclone", "storm", "wind", "warning"],
                "credibility_indicators": ["weather_related"]
            }"""
        elif any(word in prompt_lower for word in ["oil", "spill", "pollution", "environmental", "contamination"]):
            return """{
                "relevance_score": 8,
                "disaster_type": "oil_spill",
                "urgency": "high",
                "sentiment": "negative",
                "keywords": ["oil", "spill", "environmental"],
                "credibility_indicators": ["environmental_keywords"]
            }"""
        elif any(word in prompt_lower for word in ["earthquake", "tremor", "seismic", "quake", "magnitude"]):
            return """{
                "relevance_score": 7,
                "disaster_type": "earthquake",
                "urgency": "high",
                "sentiment": "negative",
                "keywords": ["earthquake", "seismic", "magnitude"],
                "credibility_indicators": ["geological_event"]
            }"""
        elif any(word in prompt_lower for word in ["flooding", "flood", "water", "rain", "overflow"]):
            return """{
                "relevance_score": 7,
                "disaster_type": "flooding",
                "urgency": "medium",
                "sentiment": "negative",
                "keywords": ["flooding", "water", "rain"],
                "credibility_indicators": ["weather_event"]
            }"""
        else:
            return """{
                "relevance_score": 2,
                "disaster_type": "none",
                "urgency": "low",
                "sentiment": "neutral",
                "keywords": [],
                "credibility_indicators": []
            }"""

    def analyze_social_post(self, post_text: str, language: str = "en") -> Dict:
        """Analyze a social media post for marine disaster relevance"""
        system_prompt = f"""
You are CoastGuardian, an AI system that analyzes social media posts for marine disaster relevance.
Analyze posts in {language} language and respond in JSON format with:
- relevance_score: 0-10 (marine disaster relevance)
- disaster_type: tsunami|cyclone|oil_spill|flooding|earthquake|none
- urgency: low|medium|high|critical
- sentiment: negative|neutral|positive
- keywords: list of relevant keywords found
- credibility_indicators: factors affecting post credibility
"""

        prompt = f"""
Analyze this social media post:
Text: {post_text}
Language: {language}

Provide analysis in JSON format.
"""

        response = self.generate_text(prompt, system_prompt)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {
                "relevance_score": 0,
                "disaster_type": "none",
                "urgency": "low",
                "sentiment": "neutral",
                "keywords": [],
                "credibility_indicators": []
            }

    def generate_social_media_post(self, disaster_type: str = "random", platform: str = "twitter",
                                  language: str = "english", location: str = "random", include_geolocation: bool = True) -> Dict:
        """Generate realistic social media posts for marine disasters"""
        import random

        # Define disaster types and locations
        disaster_types = ["tsunami", "cyclone", "oil_spill", "flooding", "earthquake"]
        locations = ["Mumbai", "Chennai", "Kolkata", "Kochi", "Visakhapatnam", "Mangalore",
                    "Paradip", "Kandla", "Tuticorin", "Ennore", "Goa"]
        platforms = ["twitter", "facebook", "instagram", "news", "reddit"]
        languages = ["english", "hindi", "tamil", "telugu", "kannada", "malayalam"]

        # Randomize if needed
        if disaster_type == "random":
            import random
            disaster_type = random.choice(disaster_types)
        if location == "random":
            import random
            location = random.choice(locations)
        if platform == "random":
            import random
            platform = random.choice(platforms)

        system_prompt = f"""
You are a social media content generator for Coast Guardian marine disaster simulation.
Generate realistic {platform} posts about {disaster_type} disasters in {location} in {language} language.

Create posts that vary in:
- Urgency levels (critical/high/medium/low)
- Post types (eyewitness reports, official warnings, community updates, news)
- Tone (urgent, informative, concerned, factual)
- Detail level (brief alerts to detailed reports)

Include relevant hashtags, mentions, and platform-specific formatting.
Generate diverse, realistic content that marine disaster systems would encounter.
"""

        prompt = f"""
Generate a realistic {platform} post about a {disaster_type} affecting {location} in {language} language.

Post should be:
- Platform: {platform}
- Disaster: {disaster_type}
- Location: {location}
- Language: {language}

Return ONLY the post text (no quotes, no extra formatting).
"""

        try:
            response = self.generate_text(prompt, system_prompt)
            post_data = {
                "text": response.strip(),
                "platform": platform,
                "disaster_type": disaster_type,
                "location": location,
                "language": language,
                "generated": True
            }

            # Add geolocation if requested
            if include_geolocation:
                coordinates = self.get_coordinates_for_location(location)
                post_data["geolocation"] = {
                    "enabled": True,
                    "coordinates": coordinates,
                    "location_name": location,
                    "accuracy_meters": random.randint(10, 100)
                }

            return post_data
        except Exception as e:
            # Fallback to template-based generation
            return self._get_template_post(disaster_type, platform, location, language, include_geolocation)

    def _get_template_post(self, disaster_type: str, platform: str, location: str, language: str, include_geolocation: bool = False) -> Dict:
        """Fallback template-based post generation"""
        import random

        templates = {
            "tsunami": [
                f"🌊 URGENT: Tsunami warning issued for {location} coast! Waves 3-5m high approaching. Evacuate immediately! #TsunamiAlert #{location}",
                f"Breaking: Massive tsunami waves detected near {location}. Coastal areas evacuating. Stay safe! #Tsunami #Emergency",
                f"Can confirm tsunami waves hitting {location} marina. Water rising rapidly. Please evacuate coastal areas NOW! #TsunamiAlert",
                f"ALERT: {location} under tsunami threat. All boats return to harbor. Coastal residents move to higher ground. #MarineAlert"
            ],
            "cyclone": [
                f"🌪️ Severe cyclone approaching {location}! Wind speeds 150+ kmph. Fishermen advised not to venture. #CycloneAlert #{location}",
                f"Breaking: Category 4 cyclone heading towards {location} coast. Storm surge expected. Prepare for evacuation! #Cyclone",
                f"Update: Cyclone intensifying near {location}. Coastal areas on high alert. Schools closed tomorrow. #WeatherAlert",
                f"URGENT: Super cyclone 200km from {location}. Navy ships returning to port. Massive storm surge expected! #CycloneWarning"
            ],
            "oil_spill": [
                f"Major oil spill reported near {location} port! 500 tonnes crude oil leaked. Marine life at risk. #OilSpill #{location}",
                f"Environmental emergency: Large oil spill in {location} waters. Cleanup operations underway. Fishing banned. #OilSpill",
                f"Witnessed oil spill near {location} coast. Black water everywhere. Please report to authorities! #MarinePollution",
                f"ALERT: Oil tanker accident near {location}. Massive spill spreading. Beach cleanup volunteers needed! #OilSpillCleanup"
            ],
            "flooding": [
                f"🌊 Flash floods in {location} coastal areas! Tide + rainfall causing severe waterlogging. Stay indoors! #FloodAlert",
                f"Breaking: {location} experiencing unprecedented coastal flooding. Several areas submerged. Rescue ops active. #Floods",
                f"Storm surge flooding {location} marina district. Water level 2ft above normal. Evacuations ongoing. #FloodWarning",
                f"Update: {location} coastal roads flooded. Traffic diverted. High tide making situation worse. #FloodUpdate"
            ],
            "earthquake": [
                f"🚨 Earthquake felt in {location}! Magnitude 6.2. Checking for tsunami risk. Stay away from coast! #Earthquake",
                f"Breaking: Strong earthquake near {location}. Buildings shaking. Tsunami watch issued. Move to safety! #EarthquakeAlert",
                f"Felt strong tremors in {location}. Earthquake confirmed. Coastal areas evacuating as precaution. #QuakeAlert",
                f"ALERT: Underwater earthquake near {location}. Tsunami possibility. Marine warnings issued. #EarthquakeTsunami"
            ]
        }

        post_templates = templates.get(disaster_type, templates["tsunami"])
        selected_post = random.choice(post_templates)

        post_data = {
            "text": selected_post,
            "platform": platform,
            "disaster_type": disaster_type,
            "location": location,
            "language": language,
            "generated": True
        }

        # Add geolocation if requested
        if include_geolocation:
            coordinates = self.get_coordinates_for_location(location)
            post_data["geolocation"] = {
                "enabled": True,
                "coordinates": coordinates,
                "location_name": location,
                "accuracy_meters": random.randint(10, 100)
            }

        return post_data

    def get_coordinates_for_location(self, location: str) -> Dict[str, float]:
        """Get latitude and longitude for Indian coastal cities"""
        coordinates = {
            "Mumbai": {"lat": 19.0760, "lng": 72.8777},
            "Chennai": {"lat": 13.0827, "lng": 80.2707},
            "Kolkata": {"lat": 22.5726, "lng": 88.3639},
            "Kochi": {"lat": 9.9312, "lng": 76.2673},
            "Visakhapatnam": {"lat": 17.6868, "lng": 83.2185},
            "Mangalore": {"lat": 12.9141, "lng": 74.8560},
            "Paradip": {"lat": 20.3155, "lng": 86.6084},
            "Kandla": {"lat": 23.0355, "lng": 70.2066},
            "Tuticorin": {"lat": 8.7642, "lng": 78.1348},
            "Ennore": {"lat": 13.2175, "lng": 80.3242},
            "Goa": {"lat": 15.2993, "lng": 74.1240},
            "New Mangalore": {"lat": 12.8683, "lng": 74.8420},
            "Haldia": {"lat": 22.0588, "lng": 88.0580},
            "JNPT": {"lat": 18.9528, "lng": 72.9479},
            "Port Blair": {"lat": 11.6234, "lng": 92.7265},
            "Kakinada": {"lat": 16.9891, "lng": 82.2475},
            "Daman": {"lat": 20.4283, "lng": 72.8397},
            "Bhavnagar": {"lat": 21.7645, "lng": 72.1519},
            "Veraval": {"lat": 20.9077, "lng": 70.3665}
        }
        return coordinates.get(location, {"lat": 19.0760, "lng": 72.8777})  # Default to Mumbai

    def generate_user_profile(self, platform: str = "twitter", location: str = None) -> Dict:
        """Generate realistic user profiles for social media posts with enhanced diversity"""
        import random
        from datetime import datetime, timedelta

        # Enhanced user types with realistic social media usernames
        user_types = {
            "government_official": {
                "usernames": ["IndianCoastGuard", "ChennaiMetDept", "MumbaiPolice_Official", "ODDisaster", "TamilNaduGov",
                             "KeralaGovt", "GujaratEmergency", "WBDisasterMgmt", "APCoastGuard", "GoaGovOfficial"],
                "verified": True,
                "followers": [50000, 250000, 100000, 75000, 180000, 120000, 95000, 85000, 200000, 65000],
                "bio_templates": ["Official Government Account", "Emergency Services {}", "Disaster Management Authority",
                                "Coast Guard Operations", "Marine Safety Division"]
            },
            "news_media": {
                "usernames": ["TimesNowNews", "IndiaToday", "NDTV", "ANI", "ZeeNews",
                             "NewsLive24x7", "CNNNews18", "RepublicTV", "DDNews", "ABPLive"],
                "verified": True,
                "followers": [500000, 750000, 300000, 150000, 400000, 620000, 280000, 1200000, 890000, 950000],
                "bio_templates": ["Breaking news and updates", "Marine and coastal news", "24x7 news coverage",
                                "National news network", "Live news updates"]
            },
            "local_journalist": {
                "usernames": ["priya_reporter", "mumbai_journalist", "coastal_watcher", "marine_eye", "rahul_newsguy",
                             "goa_localNews", "kochi_reporter", "vizag_news", "kolkata_live", "mangalore_times"],
                "verified": False,
                "followers": [25000, 50000, 15000, 30000, 45000, 18000, 22000, 35000, 28000, 20000],
                "bio_templates": ["Local correspondent", "Marine safety advocate", "Coastal community reporter",
                                "Independent journalist", "Field reporter"]
            },
            "fisherman": {
                "usernames": ["ramesh_fisherman", "captain_suresh", "sailor_mukesh", "nets_kumar", "trawler_boss",
                             "fisherman_kiran", "sea_trader", "boat_driver23", "marine_worker", "deep_sea_hunter"],
                "verified": False,
                "followers": [150, 300, 450, 220, 180, 350, 280, 190, 160, 240],
                "bio_templates": ["Traditional fisherman", "Boat owner and operator", "Deep sea fishing",
                                "Fishing community member", "Marine livelihood"]
            },
            "marine_scientist": {
                "usernames": ["dr_ocean_research", "prof_marine", "coastal_scientist", "sea_studies_india", "wave_expert",
                             "climate_coast", "marine_ecology", "ocean_watch_in", "tide_expert", "sealevel_study"],
                "verified": False,
                "followers": [5000, 8000, 3500, 6200, 4800, 7500, 5500, 4200, 6800, 3800],
                "bio_templates": ["Marine researcher", "Oceanography expert", "Coastal studies professor",
                                "Climate and sea level specialist", "Marine ecosystem researcher"]
            },
            "tourist_visitor": {
                "usernames": ["travel_addict_23", "beach_hopper_in", "wanderlust_soul", "vacation_mode", "nomad_life",
                             "trip_diary_blog", "explorer_india", "backpack_adventures", "travel_bug_in", "coastal_explorer"],
                "verified": False,
                "followers": [800, 1500, 1200, 2000, 900, 1800, 1100, 750, 950, 1300],
                "bio_templates": ["Travel enthusiast", "Exploring India's coast", "Beach lover",
                                "Adventure seeker", "Travel blogger"]
            },
            "local_resident": {
                "usernames": ["mumbai_localite", "chennai_guy_23", "kochi_resident", "goa_native", "vizag_life",
                             "coastal_living_in", "beachtown_guy", "port_city_girl", "seashore_life", "marina_local"],
                "verified": False,
                "followers": [500, 1200, 800, 2000, 350, 650, 1100, 750, 900, 1300],
                "bio_templates": ["Proud resident of {}", "Born and raised here", "Local community member",
                                "Coastal city dweller", "Hometown pride"]
            },
            "emergency_responder": {
                "usernames": ["first_responder_in", "ems_coastal", "rescue_team_24", "emergency_ops", "safety_first_in",
                             "fire_coastal", "police_patrol", "medical_team_er", "rescue_squad_in", "emergency_svc"],
                "verified": False,
                "followers": [3000, 4500, 2800, 5200, 3800, 4200, 6500, 3500, 4800, 5500],
                "bio_templates": ["Emergency services", "First responder", "Rescue operations",
                                "Public safety officer", "Emergency medical services"]
            },
            "influencer": {
                "usernames": ["coast_lifestyle", "beach_vibes_in", "social_sea_life", "trendy_coast", "viral_waves",
                             "insta_seaside", "coast_content_cr", "beach_blogger_in", "shore_influencer", "ocean_creator"],
                "verified": True,
                "followers": [50000, 85000, 120000, 95000, 150000, 75000, 110000, 65000, 90000, 125000],
                "bio_templates": ["Coastal lifestyle influencer", "Beach and travel content", "Marine conservation advocate",
                                "Coastal photography", "Ocean awareness creator"]
            }
        }

        user_type = random.choice(list(user_types.keys()))
        user_data = user_types[user_type]

        # Generate more realistic names with variations
        base_username = random.choice(user_data["usernames"])

        # Common realistic username patterns for social media
        username_variations = []

        # Add base username as-is
        username_variations.append(base_username)

        # Add numbered variations
        username_variations.extend([
            f"{base_username}{random.randint(1, 99)}",
            f"{base_username}{random.randint(100, 999)}",
            f"{base_username}_{random.randint(1, 999)}",
            f"{base_username}{random.randint(2010, 2024)}",
        ])

        # Add underscore variations
        if "_" not in base_username:
            username_variations.extend([
                f"{base_username}_in",
                f"{base_username}_india",
                f"{base_username}_official",
                f"{base_username}_real",
                f"{base_username}_live",
                f"{base_username}_news"
            ])

        # Add dot variations (for platforms that support it)
        username_variations.extend([
            base_username.replace("_", "."),
            base_username.lower(),
            base_username.upper() if len(base_username) <= 8 else base_username.title()
        ])

        # For certain user types, add profession-specific suffixes
        if user_type == "fisherman":
            username_variations.extend([
                f"{base_username}_fisher",
                f"{base_username}_boat",
                f"{base_username}_sea"
            ])
        elif user_type == "local_journalist":
            username_variations.extend([
                f"{base_username}_media",
                f"{base_username}_press",
                f"{base_username}_news"
            ])
        elif user_type == "marine_scientist":
            username_variations.extend([
                f"{base_username}_phd",
                f"{base_username}_research",
                f"{base_username}_marine"
            ])

        final_username = random.choice(username_variations)

        # Account age variation
        account_age_days = random.randint(30, 3650)  # 1 month to 10 years
        account_created = (datetime.now() - timedelta(days=account_age_days)).strftime("%Y-%m-%d")

        # Add location-specific details
        profile_location = location or random.choice(["Mumbai", "Chennai", "Kolkata", "Kochi", "Goa"])
        coordinates = self.get_coordinates_for_location(profile_location)

        return {
            "username": final_username,
            "display_name": self._generate_display_name(user_type),
            "verified": user_data["verified"] and random.random() > 0.3,  # Not all verified accounts
            "follower_count": random.choice(user_data["followers"]) + random.randint(-20, 50),
            "following_count": random.randint(50, 2000),
            "bio": random.choice(user_data["bio_templates"]).format(profile_location),
            "location": profile_location,
            "coordinates": coordinates,
            "account_created": account_created,
            "user_type": user_type,
            "posts_count": random.randint(10, 5000),
            "engagement_rate": round(random.uniform(1.0, 8.0), 2),
            "profile_image_url": f"https://api.dicebear.com/7.x/avataaars/svg?seed={base_username}",
            "is_private": random.random() < 0.1,  # 10% private accounts
            "language_preference": self._get_language_for_location(profile_location)
        }

    def _generate_display_name(self, user_type: str) -> str:
        """Generate realistic display names based on user type"""
        import random

        names = {
            "government_official": ["Official Account", "Govt. Services", "Emergency Dept", "Coast Guard", "Disaster Mgmt"],
            "news_media": ["News Network", "Breaking News", "Live Updates", "News Channel", "Media House"],
            "local_journalist": ["Local Reporter", "News Correspondent", "Field Journalist", "Community News", "City Reporter"],
            "fisherman": ["Sea Worker", "Fisherman", "Boat Owner", "Marine Worker", "Fishing Community"],
            "marine_scientist": ["Dr. Marine", "Ocean Researcher", "Prof. Coastal", "Marine Expert", "Sea Scientist"],
            "tourist_visitor": ["Travel Enthusiast", "Explorer", "Beach Lover", "Wanderer", "Adventure Seeker"],
            "local_resident": ["Local Resident", "City Native", "Community Member", "Hometown Hero", "Local Guide"],
            "emergency_responder": ["First Responder", "Emergency Services", "Rescue Team", "Safety Officer", "Emergency Ops"],
            "influencer": ["Content Creator", "Lifestyle Influencer", "Beach Blogger", "Social Media Star", "Digital Creator"]
        }

        return random.choice(names.get(user_type, ["User"]))

    def _get_language_for_location(self, location: str) -> str:
        """Get primary language based on location"""
        location_languages = {
            "Mumbai": "marathi",
            "Chennai": "tamil",
            "Kolkata": "bengali",
            "Kochi": "malayalam",
            "Visakhapatnam": "telugu",
            "Mangalore": "kannada",
            "Goa": "english",
            "Kandla": "gujarati",
            "Tuticorin": "tamil"
        }
        return location_languages.get(location, "english")

    def generate_post_metadata(self, disaster_type: str, user_type: str, platform: str, post_text: str) -> Dict:
        """Generate realistic engagement metadata for social media posts"""
        import random
        from datetime import datetime, timedelta

        # Base engagement rates by platform and user type
        platform_multipliers = {
            "twitter": 1.0,
            "facebook": 1.2,
            "instagram": 1.5,
            "reddit": 0.8,
            "news": 2.0
        }

        user_engagement_rates = {
            "government_official": {"likes": (100, 1000), "shares": (50, 300), "comments": (20, 150)},
            "news_media": {"likes": (500, 5000), "shares": (200, 1000), "comments": (50, 400)},
            "local_journalist": {"likes": (50, 500), "shares": (20, 100), "comments": (10, 80)},
            "fisherman": {"likes": (5, 50), "shares": (2, 15), "comments": (1, 10)},
            "marine_scientist": {"likes": (20, 200), "shares": (10, 50), "comments": (5, 30)},
            "tourist_visitor": {"likes": (10, 100), "shares": (3, 20), "comments": (2, 15)},
            "local_resident": {"likes": (15, 150), "shares": (5, 30), "comments": (3, 25)},
            "emergency_responder": {"likes": (100, 800), "shares": (50, 200), "comments": (20, 100)},
            "influencer": {"likes": (500, 2000), "shares": (100, 500), "comments": (30, 200)}
        }

        # Disaster urgency multipliers
        disaster_urgency = {
            "tsunami": 3.0,
            "cyclone": 2.5,
            "earthquake": 2.8,
            "oil_spill": 1.8,
            "flooding": 2.2,
            "none": 1.0
        }

        # Get base rates
        base_rates = user_engagement_rates.get(user_type, {"likes": (10, 100), "shares": (5, 50), "comments": (2, 20)})
        platform_mult = platform_multipliers.get(platform, 1.0)
        urgency_mult = disaster_urgency.get(disaster_type, 1.0)

        # Calculate engagement
        total_multiplier = platform_mult * urgency_mult

        likes_range = base_rates["likes"]
        shares_range = base_rates["shares"]
        comments_range = base_rates["comments"]

        likes = int(random.randint(*likes_range) * total_multiplier)
        shares = int(random.randint(*shares_range) * total_multiplier)
        comments = int(random.randint(*comments_range) * total_multiplier)

        # Generate timestamp (recent posts)
        hours_ago = random.randint(1, 48)
        post_time = datetime.now() - timedelta(hours=hours_ago)

        # Calculate engagement rate
        total_engagement = likes + shares + comments
        post_reach = likes * random.uniform(2.0, 5.0)  # Estimate reach
        engagement_rate = round((total_engagement / max(post_reach, 1)) * 100, 2)

        # Generate comment samples for high-engagement posts
        comment_samples = []
        if comments > 10:
            comment_templates = {
                "tsunami": ["Stay safe everyone!", "This is terrifying", "Praying for all affected", "When will this end?"],
                "cyclone": ["Hope everyone evacuated", "Nature is so powerful", "Stay indoors!", "Scary weather"],
                "earthquake": ["Felt the tremors here too", "Hope no one is hurt", "Stay alert!", "Aftershocks possible"],
                "oil_spill": ["Environmental disaster", "Poor marine life", "Who's responsible?", "Cleanup needed now"],
                "flooding": ["Roads are completely flooded", "Water everywhere", "Rescue teams working", "Stay on high ground"],
                "none": ["Thanks for sharing", "Interesting", "Good to know", "Stay safe"]
            }
            templates = comment_templates.get(disaster_type, comment_templates["none"])
            comment_samples = random.sample(templates, min(3, len(templates)))

        return {
            "engagement": {
                "likes": likes,
                "shares": shares,
                "comments": comments,
                "views": int(likes * random.uniform(5.0, 15.0)),
                "engagement_rate": engagement_rate
            },
            "timing": {
                "posted_at": post_time.isoformat(),
                "hours_ago": hours_ago,
                "is_trending": total_engagement > 500,
                "peak_engagement_hour": random.randint(8, 22)
            },
            "reach_metrics": {
                "estimated_reach": int(post_reach),
                "impression_count": int(post_reach * random.uniform(1.2, 2.0)),
                "click_through_rate": round(random.uniform(1.5, 8.0), 2),
                "save_count": int(likes * random.uniform(0.1, 0.3))
            },
            "content_analysis": {
                "character_count": len(post_text),
                "word_count": len(post_text.split()),
                "hashtag_count": post_text.count('#'),
                "mention_count": post_text.count('@'),
                "has_media": random.choice([True, False]),
                "urgency_score": round(urgency_mult, 1)
            },
            "user_interaction": {
                "comment_samples": comment_samples,
                "top_reaction": random.choice(["😱", "🙏", "😢", "😰", "❤️", "👍"]),
                "is_verified_source": user_type in ["government_official", "news_media", "emergency_responder"],
                "credibility_score": round(random.uniform(6.0, 10.0), 1) if user_type in ["government_official", "news_media"] else round(random.uniform(4.0, 8.0), 1)
            }
        }

# Test function
def test_llm_connection():
    """Test LLM connection with Groq API"""
    llm = CoastGuardianLLM()
    print(f"Model: {llm.model_name}")
    print(f"Groq API Available: {llm.is_available()}")

    if llm.is_available():
        models = llm.list_models()
        print(f"Available models: {len(models)}")
        for model in models[:5]:
            print(f"  - {model.get('name', 'Unknown')}")

        # Test analysis
        print("\nTesting post analysis...")
        test_post = "Huge waves hitting the coast! Tsunami warning issued for coastal areas."
        result = llm.analyze_social_post(test_post)
        print(f"Analysis result: {json.dumps(result, indent=2)}")

        # Test post generation
        print("\nTesting post generation...")
        generated = llm.generate_social_media_post(disaster_type="cyclone", location="Chennai")
        print(f"Generated post: {generated['text'][:100]}...")
    else:
        print("LLM not available - will use mock responses")

if __name__ == "__main__":
    test_llm_connection()
