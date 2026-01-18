"""
Coast Guardian Misinformation Detection Service
Advanced fake news detection and credibility scoring for marine disaster posts
"""

import re
import time
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass

from api.models import SocialMediaPost, DisasterAnalysis

@dataclass
class MisinformationFlags:
    """Flags indicating potential misinformation"""
    suspicious_language: List[str]
    credibility_issues: List[str]
    fact_check_warnings: List[str]
    source_reliability: str
    confidence_score: float

class CoastGuardianMisinformationDetector:
    """Advanced misinformation detection for marine disaster intelligence"""

    def __init__(self):
        # Misinformation patterns specific to disaster scenarios
        self.suspicious_patterns = {
            'sensational_keywords': [
                'breaking', 'urgent', 'emergency', 'disaster', 'catastrophe',
                'unprecedented', 'massive', 'devastating', 'apocalyptic',
                'end of world', 'biblical', 'never seen before'
            ],
            'exaggeration_markers': [
                'hundreds dead', 'thousands missing', 'total destruction',
                'completely wiped out', 'nothing left', 'everything destroyed',
                'worst ever', 'historic disaster', 'never happened before'
            ],
            'conspiracy_terms': [
                'cover up', 'government hiding', 'media blackout', 'conspiracy',
                'they dont want you to know', 'secret', 'hidden truth',
                'wake up people', 'open your eyes', 'think for yourself'
            ],
            'emotional_manipulation': [
                'share before deleted', 'must watch', 'shocking truth',
                'you wont believe', 'mainstream media lies', 'real truth',
                'please share', 'spread the word', 'before its too late'
            ]
        }

        # Credibility indicators
        self.credibility_indicators = {
            'positive': {
                'official_sources': [
                    'indian meteorological department', 'imd', 'ndrf', 'coast guard',
                    'incois', 'ministry of earth sciences', 'disaster management',
                    'pib', 'press information bureau', 'government', 'official'
                ],
                'verified_accounts': [
                    'verified', 'blue tick', 'official account', 'ministry',
                    'department', 'bureau', 'commission', 'authority'
                ],
                'specific_details': [
                    'coordinates', 'lat long', 'exact time', 'specific location',
                    'magnitude', 'wind speed', 'wave height', 'barometric pressure'
                ],
                'multiple_sources': [
                    'confirmed by', 'multiple reports', 'various sources',
                    'cross verified', 'independently confirmed'
                ]
            },
            'negative': {
                'vague_sources': [
                    'sources say', 'insider info', 'someone told me',
                    'i heard', 'rumor has it', 'word is', 'they say'
                ],
                'no_verification': [
                    'unconfirmed', 'not verified', 'alleged', 'reportedly',
                    'claims suggest', 'sources suggest', 'possibly'
                ],
                'emotional_appeal': [
                    'heart breaking', 'devastating footage', 'shocking images',
                    'you will cry', 'so sad', 'tragic scenes'
                ],
                'urgent_sharing': [
                    'share immediately', 'urgent share', 'before deleted',
                    'share fast', 'quick share', 'share now'
                ]
            }
        }

        # Factual consistency patterns for marine disasters
        self.fact_patterns = {
            'tsunami': {
                'realistic_heights': (1, 30),  # meters
                'realistic_speeds': (10, 800),  # km/h
                'warning_systems': ['incois', 'tsunami warning', 'seismic alert']
            },
            'cyclone': {
                'realistic_winds': (62, 250),  # km/h
                'seasons': ['april', 'may', 'june', 'october', 'november', 'december'],
                'warning_systems': ['imd', 'cyclone warning', 'weather alert']
            },
            'oil_spill': {
                'realistic_volumes': (1, 100000),  # tonnes
                'sources': ['ship', 'tanker', 'rig', 'pipeline', 'refinery'],
                'impacts': ['marine life', 'fishing', 'beaches', 'mangroves']
            }
        }

        # Language-specific misinformation patterns
        self.language_patterns = {
            'hindi': {
                'sensational': ['खतरनाक', 'भयंकर', 'विनाशकारी', 'अप्रत्याशित'],
                'conspiracy': ['साजिश', 'छुपाया गया', 'सच्चाई', 'सरकार झूठ']
            },
            'tamil': {
                'sensational': ['அபாயகரமான', 'பயங்கரமான', 'அழிவுகரமான'],
                'conspiracy': ['மறைக்கப்பட்ட', 'உண்மை', 'அரசு பொய்']
            },
            'telugu': {
                'sensational': ['ప్రమాదకరమైన', 'భయంకరమైన', 'వినాశకరమైన'],
                'conspiracy': ['దాచిన', 'నిజం', 'ప్రభుత్వం అబద్ధం']
            }
        }

    def detect_misinformation(self, post: SocialMediaPost, analysis: DisasterAnalysis) -> MisinformationFlags:
        """Comprehensive misinformation detection for a post"""

        suspicious_language = []
        credibility_issues = []
        fact_check_warnings = []

        # 1. Language-based detection
        suspicious_language.extend(self._detect_suspicious_language(post))

        # 2. Credibility assessment
        credibility_issues.extend(self._assess_credibility_issues(post))

        # 3. Fact consistency checking
        fact_check_warnings.extend(self._check_factual_consistency(post, analysis))

        # 4. Source reliability assessment
        source_reliability = self._assess_source_reliability(post)

        # 5. Calculate overall confidence score
        confidence_score = self._calculate_misinformation_confidence(
            suspicious_language, credibility_issues, fact_check_warnings, post
        )

        return MisinformationFlags(
            suspicious_language=suspicious_language,
            credibility_issues=credibility_issues,
            fact_check_warnings=fact_check_warnings,
            source_reliability=source_reliability,
            confidence_score=confidence_score
        )

    def _detect_suspicious_language(self, post: SocialMediaPost) -> List[str]:
        """Detect suspicious language patterns"""
        flags = []
        text_lower = post.text.lower()

        # Check for sensational keywords
        sensational_count = 0
        for keyword in self.suspicious_patterns['sensational_keywords']:
            if keyword in text_lower:
                sensational_count += 1

        if sensational_count >= 3:
            flags.append("excessive_sensational_language")
        elif sensational_count >= 2:
            flags.append("moderate_sensational_language")

        # Check for exaggeration markers
        for marker in self.suspicious_patterns['exaggeration_markers']:
            if marker in text_lower:
                flags.append("exaggerated_claims")
                break

        # Check for conspiracy terms
        for term in self.suspicious_patterns['conspiracy_terms']:
            if term in text_lower:
                flags.append("conspiracy_language")
                break

        # Check for emotional manipulation
        for term in self.suspicious_patterns['emotional_manipulation']:
            if term in text_lower:
                flags.append("emotional_manipulation")
                break

        # Language-specific patterns
        if post.language in self.language_patterns:
            lang_patterns = self.language_patterns[post.language]

            # Check sensational terms in local language
            for term in lang_patterns.get('sensational', []):
                if term in post.text:
                    flags.append(f"sensational_language_{post.language}")
                    break

            # Check conspiracy terms in local language
            for term in lang_patterns.get('conspiracy', []):
                if term in post.text:
                    flags.append(f"conspiracy_language_{post.language}")
                    break

        # Check for excessive caps and exclamation marks
        caps_ratio = sum(1 for c in post.text if c.isupper()) / max(len(post.text), 1)
        if caps_ratio > 0.3:
            flags.append("excessive_caps")

        exclamation_count = post.text.count('!')
        if exclamation_count > 5:
            flags.append("excessive_exclamation")

        return flags

    def _assess_credibility_issues(self, post: SocialMediaPost) -> List[str]:
        """Assess credibility issues with the post"""
        issues = []
        text_lower = post.text.lower()

        # Check for positive credibility indicators
        has_positive_indicators = False
        for category, indicators in self.credibility_indicators['positive'].items():
            for indicator in indicators:
                if indicator in text_lower:
                    has_positive_indicators = True
                    break
            if has_positive_indicators:
                break

        # Check for negative credibility indicators
        negative_indicators = []
        for category, indicators in self.credibility_indicators['negative'].items():
            for indicator in indicators:
                if indicator in text_lower:
                    negative_indicators.append(category)
                    break

        # User credibility assessment
        if post.user:
            if not post.user.verified:
                issues.append("unverified_account")

            if post.user.follower_count < 100:
                issues.append("low_follower_count")

            username_lower = post.user.username.lower()
            suspicious_username_patterns = [
                'news', 'breaking', 'alert', 'truth', 'real', 'insider'
            ]
            if any(pattern in username_lower for pattern in suspicious_username_patterns):
                if not any(official in username_lower for official in ['official', 'govt', 'ministry']):
                    issues.append("suspicious_username_pattern")

        # Content credibility issues
        if negative_indicators:
            issues.extend([f"negative_indicator_{indicator}" for indicator in negative_indicators])

        if not has_positive_indicators:
            issues.append("no_authoritative_source")

        # Check for vague temporal references
        vague_time_patterns = [
            'recently', 'just now', 'moments ago', 'earlier today',
            'this morning', 'last night', 'some time ago'
        ]
        if any(pattern in text_lower for pattern in vague_time_patterns):
            issues.append("vague_temporal_reference")

        return issues

    def _check_factual_consistency(self, post: SocialMediaPost, analysis: DisasterAnalysis) -> List[str]:
        """Check factual consistency with known disaster patterns"""
        warnings = []
        text_lower = post.text.lower()

        disaster_type = analysis.disaster_type
        if disaster_type in self.fact_patterns:
            patterns = self.fact_patterns[disaster_type]

            # Check tsunami-specific facts
            if disaster_type == 'tsunami':
                # Check for unrealistic wave heights
                height_matches = re.findall(r'(\d+)\s*(?:meter|metre|m)\s*(?:high|tall|wave)', text_lower)
                for height_str in height_matches:
                    height = float(height_str)
                    min_h, max_h = patterns['realistic_heights']
                    if height < min_h or height > max_h:
                        warnings.append(f"unrealistic_tsunami_height_{height}m")

                # Check for unrealistic speeds
                speed_matches = re.findall(r'(\d+)\s*(?:km/h|kmph|mph)\s*(?:speed|fast)', text_lower)
                for speed_str in speed_matches:
                    speed = float(speed_str)
                    min_s, max_s = patterns['realistic_speeds']
                    if speed < min_s or speed > max_s:
                        warnings.append(f"unrealistic_tsunami_speed_{speed}kmh")

            # Check cyclone-specific facts
            elif disaster_type == 'cyclone':
                # Check for unrealistic wind speeds
                wind_matches = re.findall(r'(\d+)\s*(?:km/h|kmph|mph)\s*(?:wind|gust)', text_lower)
                for wind_str in wind_matches:
                    wind_speed = float(wind_str)
                    min_w, max_w = patterns['realistic_winds']
                    if wind_speed < min_w or wind_speed > max_w:
                        warnings.append(f"unrealistic_wind_speed_{wind_speed}kmh")

                # Check seasonal consistency (basic)
                current_month = datetime.now(timezone.utc).strftime('%B').lower()
                if current_month not in patterns['seasons']:
                    warnings.append("unusual_cyclone_season")

            # Check oil spill facts
            elif disaster_type == 'oil_spill':
                # Check for unrealistic volumes
                volume_matches = re.findall(r'(\d+)\s*(?:tonnes?|tons?|barrels?)\s*(?:oil|spilled)', text_lower)
                for volume_str in volume_matches:
                    volume = float(volume_str)
                    min_v, max_v = patterns['realistic_volumes']
                    if volume > max_v:
                        warnings.append(f"extremely_large_spill_volume_{volume}")

        # Check for impossible timelines
        timeline_patterns = [
            r'happened (\d+) seconds ago',
            r'just (\d+) minutes after',
            r'(\d+) hour warning'
        ]

        for pattern in timeline_patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                time_value = int(match)
                if 'seconds ago' in pattern and time_value < 30:
                    warnings.append("impossible_immediate_reporting")
                elif 'minutes after' in pattern and time_value < 5:
                    warnings.append("unrealistic_response_time")

        # Check for contradictory information
        contradictory_pairs = [
            (['no casualties', 'no injuries'], ['deaths', 'died', 'killed', 'injured']),
            (['minor damage', 'small'], ['massive', 'devastating', 'total destruction']),
            (['under control', 'contained'], ['spreading', 'out of control', 'escalating'])
        ]

        for safe_terms, danger_terms in contradictory_pairs:
            has_safe = any(term in text_lower for term in safe_terms)
            has_danger = any(term in text_lower for term in danger_terms)

            if has_safe and has_danger:
                warnings.append("contradictory_information")
                break

        return warnings

    def _assess_source_reliability(self, post: SocialMediaPost) -> str:
        """Assess the reliability of the source"""
        score = 0.5  # Base score

        text_lower = post.text.lower()

        # Positive factors
        if post.user and post.user.verified:
            score += 0.3

        # Check for official source mentions
        official_mentions = [
            'imd', 'incois', 'ndrf', 'coast guard', 'ministry',
            'government', 'official', 'press release', 'statement'
        ]
        if any(mention in text_lower for mention in official_mentions):
            score += 0.2

        # Check for specific details
        if re.search(r'\d{1,2}:\d{2}', post.text):  # Time mentions
            score += 0.1

        if post.location or any(loc in text_lower for loc in [
            'mumbai', 'chennai', 'kolkata', 'kochi', 'visakhapatnam'
        ]):
            score += 0.1

        # Negative factors
        sharing_urgency = [
            'share immediately', 'please share', 'spread the word',
            'before deleted', 'share fast'
        ]
        if any(term in text_lower for term in sharing_urgency):
            score -= 0.2

        # Sensational language penalty
        sensational_count = sum(1 for term in self.suspicious_patterns['sensational_keywords']
                               if term in text_lower)
        score -= min(sensational_count * 0.05, 0.3)

        # Convert to reliability category
        score = max(0.0, min(1.0, score))

        if score >= 0.8:
            return "high_reliability"
        elif score >= 0.6:
            return "moderate_reliability"
        elif score >= 0.4:
            return "low_reliability"
        else:
            return "very_low_reliability"

    def _calculate_misinformation_confidence(
        self,
        suspicious_language: List[str],
        credibility_issues: List[str],
        fact_check_warnings: List[str],
        post: SocialMediaPost
    ) -> float:
        """Calculate confidence score for misinformation detection"""

        # Start with neutral confidence
        confidence = 0.5

        # Language factors
        language_penalty = len(suspicious_language) * 0.05
        confidence += min(language_penalty, 0.3)

        # Credibility factors
        credibility_penalty = len(credibility_issues) * 0.03
        confidence += min(credibility_penalty, 0.25)

        # Fact-checking factors
        fact_penalty = len(fact_check_warnings) * 0.1
        confidence += min(fact_penalty, 0.2)

        # User factors
        if post.user:
            if not post.user.verified:
                confidence += 0.05
            if post.user.follower_count < 100:
                confidence += 0.1
            elif post.user.follower_count < 1000:
                confidence += 0.05

        # Content length factor (very short posts are suspicious)
        if len(post.text) < 50:
            confidence += 0.05

        # Very long posts with lots of details might be more credible
        if len(post.text) > 500:
            confidence -= 0.05

        return max(0.0, min(1.0, confidence))

    def generate_misinformation_report(
        self,
        post: SocialMediaPost,
        analysis: DisasterAnalysis,
        flags: MisinformationFlags
    ) -> Dict[str, Any]:
        """Generate comprehensive misinformation analysis report"""

        # Determine overall assessment
        if flags.confidence_score >= 0.7:
            risk_level = "high_misinformation_risk"
            recommendation = "Manual review required before sharing"
        elif flags.confidence_score >= 0.5:
            risk_level = "moderate_misinformation_risk"
            recommendation = "Verify with official sources before sharing"
        elif flags.confidence_score >= 0.3:
            risk_level = "low_misinformation_risk"
            recommendation = "Exercise normal caution"
        else:
            risk_level = "minimal_misinformation_risk"
            recommendation = "Appears credible based on automated analysis"

        return {
            "misinformation_assessment": {
                "risk_level": risk_level,
                "confidence_score": round(flags.confidence_score, 3),
                "recommendation": recommendation
            },
            "detected_issues": {
                "suspicious_language_flags": flags.suspicious_language,
                "credibility_concerns": flags.credibility_issues,
                "fact_check_warnings": flags.fact_check_warnings,
                "source_reliability": flags.source_reliability
            },
            "analysis_details": {
                "total_flags": len(flags.suspicious_language) + len(flags.credibility_issues) + len(flags.fact_check_warnings),
                "language_issues": len(flags.suspicious_language),
                "credibility_issues": len(flags.credibility_issues),
                "factual_concerns": len(flags.fact_check_warnings)
            },
            "verification_suggestions": self._generate_verification_suggestions(analysis.disaster_type),
            "processed_at": datetime.now(timezone.utc).isoformat()
        }

    def _generate_verification_suggestions(self, disaster_type: str) -> List[str]:
        """Generate verification suggestions based on disaster type"""
        base_suggestions = [
            "Check official government sources (IMD, INCOIS, NDRF)",
            "Cross-reference with multiple reliable news sources",
            "Look for official timestamps and location data",
            "Verify with local authorities or emergency services"
        ]

        disaster_specific = {
            "tsunami": [
                "Check INCOIS (Indian National Centre for Ocean Information Services)",
                "Verify with Pacific Tsunami Warning Center",
                "Look for seismic activity reports from IMD"
            ],
            "cyclone": [
                "Check IMD (India Meteorological Department) forecasts",
                "Verify cyclone tracking data and wind speed measurements",
                "Cross-check with satellite imagery if available"
            ],
            "oil_spill": [
                "Verify with Coast Guard or Maritime Authority",
                "Check for official environmental impact statements",
                "Look for shipping or port authority confirmations"
            ],
            "flooding": [
                "Check with local disaster management authorities",
                "Verify rainfall and water level data with IMD",
                "Cross-reference with municipal corporation updates"
            ],
            "earthquake": [
                "Check National Center for Seismology reports",
                "Verify magnitude and epicenter data",
                "Look for official aftershock predictions"
            ]
        }

        suggestions = base_suggestions.copy()
        if disaster_type in disaster_specific:
            suggestions.extend(disaster_specific[disaster_type])

        return suggestions