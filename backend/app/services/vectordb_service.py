"""
VectorDB Service
FAISS-based vector similarity search for hazard classification.
Uses sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 for multilingual support.

Enhanced with:
- Spam detection for promotional/irrelevant content
- Panic level scoring based on text characteristics
- Verification layer integration for 6-layer pipeline
"""

import os
import logging
import pickle
import re
import time
from typing import List, Tuple, Dict, Any, Optional
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import settings
from app.models.vectordb import (
    ClassificationResult, VectorSearchResult, VectorDBStats,
    DisasterType, HazardClassification
)
from app.models.verification import (
    LayerResult, LayerStatus, LayerName, TextLayerData
)

logger = logging.getLogger(__name__)


class VectorDBService:
    """FAISS-based vector database for marine disaster classification."""

    # =============================================================================
    # SPAM DETECTION CONFIGURATION
    # =============================================================================

    # Keywords that indicate spam/promotional content
    SPAM_KEYWORDS = [
        # English spam keywords
        "buy", "click", "link", "subscribe", "follow", "free", "prize",
        "giveaway", "discount", "sale", "offer", "win", "winner", "earn",
        "money", "cash", "deal", "promo", "promotion", "like and share",
        "share now", "retweet", "dm me", "check out", "visit my",
        # Hindi spam keywords
        "खरीदें", "फ्री", "जीतें", "ऑफर", "डिस्काउंट", "फॉलो करें",
        # Common promotional patterns
        "@", "http", "www.", ".com", "👉", "🔗", "⬇️"
    ]

    # Keywords that indicate urgency/panic
    PANIC_KEYWORDS = [
        # English panic words
        "help", "emergency", "urgent", "immediately", "now", "danger",
        "dangerous", "warning", "alert", "evacuate", "rescue", "save",
        "dying", "dead", "death", "critical", "severe", "extreme",
        # Hindi panic words
        "मदद", "बचाओ", "खतरा", "जल्दी", "तुरंत", "भागो", "मरना",
        "आपातकाल", "चेतावनी", "खतरनाक"
    ]

    # Multilingual training data for coastal hazards
    MARINE_TRAINING_DATA = [
        # Tsunami examples (English, Hindi, Marathi, Hinglish)
        ("Massive tsunami waves approaching the coast! Evacuate now", "tsunami"),
        ("Tsunami warning issued after major earthquake", "tsunami"),
        ("Giant waves hitting the shore, people running inland", "tsunami"),
        ("समुद्र में भयंकर लहरें उठ रही हैं, सुनामी का खतरा", "tsunami"),
        ("सुनामी चेतावनी जारी, तट से दूर जाएं", "tsunami"),
        ("tsunami aa raha hai jaldi bhago", "tsunami"),

        # Cyclone examples
        ("Cyclone Nisarga approaching Maharashtra coast, winds 120 kmph", "cyclone"),
        ("Severe cyclonic storm with heavy rainfall expected", "cyclone"),
        ("Hurricane force winds damaging coastal structures", "cyclone"),
        ("चक्रवात अलर्ट! तेज़ हवाओं से बचकर रहें", "cyclone"),
        ("तूफान आ रहा है, सभी मछुआरे वापस आ जाएं", "cyclone"),
        ("cyclone warning hai, ghar me raho", "cyclone"),

        # High waves examples
        ("Dangerous surf conditions at beaches, 5m waves reported", "high_waves"),
        ("Beach closed due to high waves and strong currents", "high_waves"),
        ("Extremely high waves making boating dangerous", "high_waves"),
        ("समुद्र में ऊंची लहरें, तैराकी करना खतरनाक", "high_waves"),
        ("समुद्राच्या लाटा खूप उंच आहेत, धोकादायक", "high_waves"),
        ("waves bahut high hai, beach pe mat jao", "high_waves"),

        # Coastal flood examples
        ("Heavy monsoon flooding in coastal Chennai, roads submerged", "coastal_flood"),
        ("High tide combined with rain causing coastal flooding", "coastal_flood"),
        ("Sea water flooding homes in low-lying coastal areas", "coastal_flood"),
        ("बाढ़ का पानी घरों में घुस गया है, तटीय क्षेत्र जलमग्न", "coastal_flood"),
        ("समुद्र का पानी गांवों में आ गया, मदद भेजो", "coastal_flood"),
        ("flooding ho gayi hai coastal area me", "coastal_flood"),

        # Rip current examples
        ("Dangerous rip currents reported at Goa beaches", "rip_currents"),
        ("Strong undertow pulling swimmers out to sea", "rip_currents"),
        ("Multiple rescues due to rip currents at beach", "rip_currents"),
        ("समुद्र में खतरनाक धाराएं, तैरने से बचें", "rip_currents"),
        ("rip current bahut strong hai beach pe", "rip_currents"),

        # Oil spill examples (English, Hindi, Hinglish)
        ("Massive oil spill detected near Mumbai port, marine life at risk", "oil_spill"),
        ("Oil slick spreading across the coast from ship collision", "oil_spill"),
        ("Huge oil spill in marine region, urgent cleanup needed", "oil_spill"),
        ("Oil tanker leak polluting coastal waters, fishing banned", "oil_spill"),
        ("Black oil washing up on beaches after offshore spill", "oil_spill"),
        ("समुद्र में तेल रिसाव, मछलियां मर रही हैं", "oil_spill"),
        ("तट पर तेल फैल गया है, समुद्री जीवन खतरे में", "oil_spill"),
        ("oil spill ho gaya hai port ke paas, bahut bada leak hai", "oil_spill"),
        ("Petroleum leak from offshore rig contaminating sea water", "oil_spill"),
        ("Emergency response needed for major oil spill near coast", "oil_spill"),

        # Ship stranding / Maritime accidents
        ("Ship stranded near rocky coast, crew needs rescue", "ship_stranding"),
        ("Vessel run aground on reef, taking on water", "ship_stranding"),
        ("Fishing boat capsized in rough seas, missing crew", "ship_stranding"),
        ("जहाज फंस गया है चट्टानों पर, मदद चाहिए", "ship_stranding"),
        ("boat doob rahi hai samundar me, rescue bhejo", "ship_stranding"),

        # Illegal fishing / Poaching
        ("Illegal trawlers spotted in protected marine zone", "illegal_fishing"),
        ("Poachers caught fishing in restricted waters", "illegal_fishing"),
        ("Unauthorized fishing boats destroying coral reef", "illegal_fishing"),
        ("अवैध मछली पकड़ने वाले संरक्षित क्षेत्र में देखे गए", "illegal_fishing"),
        ("illegal fishing ho rahi hai sanctuary me", "illegal_fishing"),

        # Beached Aquatic Animal examples (100 examples - English, Hindi, Marathi, Hinglish, Tamil, regional variations)
        # Whales
        ("Dead whale washed up on beach near Mumbai", "beached_aquatic_animal"),
        ("Large whale stranded on Juhu beach needs help", "beached_aquatic_animal"),
        ("Beached whale found at Marina Beach Chennai", "beached_aquatic_animal"),
        ("Massive whale carcass on Goa beach, authorities alerted", "beached_aquatic_animal"),
        ("Whale stranding reported at Kovalam beach", "beached_aquatic_animal"),
        ("Blue whale found dead on coast", "beached_aquatic_animal"),
        ("Humpback whale washed ashore, crowd gathering", "beached_aquatic_animal"),
        ("Sperm whale stranded on rocky shore", "beached_aquatic_animal"),
        ("Baby whale found on beach, still alive needs rescue", "beached_aquatic_animal"),
        ("Whale beaching incident at Digha beach West Bengal", "beached_aquatic_animal"),

        # Dolphins
        ("Dolphin stranded on beach, please help rescue", "beached_aquatic_animal"),
        ("Dead dolphin found washed up at Versova beach", "beached_aquatic_animal"),
        ("Multiple dolphins beached at Alibag coast", "beached_aquatic_animal"),
        ("Injured dolphin on shore near fishing village", "beached_aquatic_animal"),
        ("Dolphin carcass found on Puri beach Odisha", "beached_aquatic_animal"),
        ("Baby dolphin stranded, fishermen trying to save it", "beached_aquatic_animal"),
        ("Bottlenose dolphin found dead on Malvan beach", "beached_aquatic_animal"),
        ("Dolphin washed ashore after storm", "beached_aquatic_animal"),
        ("River dolphin found on riverbank near coast", "beached_aquatic_animal"),
        ("Pod of dolphins stranded on Kochi beach", "beached_aquatic_animal"),

        # Sea Turtles
        ("Sea turtle found dead on beach with plastic in stomach", "beached_aquatic_animal"),
        ("Olive ridley turtle stranded on Odisha coast", "beached_aquatic_animal"),
        ("Giant sea turtle washed up on shore", "beached_aquatic_animal"),
        ("Injured turtle on beach needs wildlife rescue", "beached_aquatic_animal"),
        ("Dead turtle found entangled in fishing net on beach", "beached_aquatic_animal"),
        ("Hawksbill turtle stranded at Andaman beach", "beached_aquatic_animal"),
        ("Leatherback turtle carcass found on coast", "beached_aquatic_animal"),
        ("Multiple turtles washed ashore after cyclone", "beached_aquatic_animal"),
        ("Turtle nesting disturbed, female turtle stranded", "beached_aquatic_animal"),
        ("Green sea turtle found on Varkala beach Kerala", "beached_aquatic_animal"),

        # Sharks
        ("Shark washed up on beach, crowd gathering", "beached_aquatic_animal"),
        ("Dead shark found on Goa beach shore", "beached_aquatic_animal"),
        ("Large shark stranded on sand at low tide", "beached_aquatic_animal"),
        ("Whale shark carcass on Maharashtra coast", "beached_aquatic_animal"),
        ("Baby shark found dead on beach", "beached_aquatic_animal"),
        ("Shark beaching reported near fishing harbor", "beached_aquatic_animal"),
        ("Hammerhead shark found on beach", "beached_aquatic_animal"),
        ("Tiger shark washed ashore after storm", "beached_aquatic_animal"),

        # Rays and other marine life
        ("Manta ray stranded on beach, need help", "beached_aquatic_animal"),
        ("Giant stingray found dead on shore", "beached_aquatic_animal"),
        ("Eagle ray washed up on coast", "beached_aquatic_animal"),
        ("Dugong found dead on Gujarat coast", "beached_aquatic_animal"),
        ("Manatee carcass on beach, rare sighting", "beached_aquatic_animal"),
        ("Large fish die-off on beach, hundreds dead", "beached_aquatic_animal"),
        ("Sunfish washed ashore on Gokarna beach", "beached_aquatic_animal"),
        ("Jellyfish mass stranding on beach", "beached_aquatic_animal"),

        # Seals and Sea Lions (rare in India but included)
        ("Seal found stranded on beach, unusual sighting", "beached_aquatic_animal"),
        ("Sea lion washed up on shore, needs rescue", "beached_aquatic_animal"),

        # Hindi examples
        ("समुद्र तट पर मरी हुई व्हेल मिली", "beached_aquatic_animal"),
        ("डॉल्फिन किनारे पर फंसी है, बचाओ", "beached_aquatic_animal"),
        ("समुद्री कछुआ मृत अवस्था में मिला", "beached_aquatic_animal"),
        ("बड़ी मछली समुद्र किनारे बहकर आई", "beached_aquatic_animal"),
        ("शार्क का शव समुद्र तट पर मिला", "beached_aquatic_animal"),
        ("व्हेल किनारे पर फंस गई है, मदद चाहिए", "beached_aquatic_animal"),
        ("डॉल्फिन का शव बीच पर मिला", "beached_aquatic_animal"),
        ("कछुआ जाल में फंसकर मर गया, तट पर पड़ा है", "beached_aquatic_animal"),
        ("मछुआरों को समुद्री जीव का शव मिला किनारे पर", "beached_aquatic_animal"),
        ("तूफान के बाद कई समुद्री जीव तट पर आ गए", "beached_aquatic_animal"),
        ("बच्चा डॉल्फिन फंसा है रेत में, जल्दी आओ", "beached_aquatic_animal"),
        ("बड़ी व्हेल मछली मुंबई बीच पर", "beached_aquatic_animal"),
        ("समुद्री कछुए का शव प्लास्टिक से भरा था", "beached_aquatic_animal"),
        ("गोवा बीच पर शार्क का शव देखा गया", "beached_aquatic_animal"),
        ("केरल तट पर डॉल्फिन फंसी, बचाव जारी", "beached_aquatic_animal"),

        # Marathi examples
        ("समुद्र किनाऱ्यावर व्हेल सापडला", "beached_aquatic_animal"),
        ("डॉल्फिन किनाऱ्यावर अडकली आहे", "beached_aquatic_animal"),
        ("मेलेली कासव समुद्र किनाऱ्यावर", "beached_aquatic_animal"),
        ("मोठा मासा वाहून आला किनाऱ्यावर", "beached_aquatic_animal"),
        ("समुद्री जीव मृतावस्थेत सापडले", "beached_aquatic_animal"),
        ("व्हेलचे शव कोकण किनाऱ्यावर", "beached_aquatic_animal"),

        # Hinglish examples
        ("whale beach pe aake mar gayi", "beached_aquatic_animal"),
        ("dolphin fas gayi hai sand mein, help karo", "beached_aquatic_animal"),
        ("turtle dead mili beach pe plastic se", "beached_aquatic_animal"),
        ("shark ka body mila hai shore pe", "beached_aquatic_animal"),
        ("bahut badi machli aayi hai beach pe", "beached_aquatic_animal"),
        ("marine animal stranded hai, rescue chahiye", "beached_aquatic_animal"),
        ("samundar se whale aake phasi hai", "beached_aquatic_animal"),
        ("dolphin mar gayi, body beach pe padi hai", "beached_aquatic_animal"),
        ("sea turtle injured hai kinare pe", "beached_aquatic_animal"),
        ("fish die-off hua hai beach pe", "beached_aquatic_animal"),

        # Tamil examples
        ("கடற்கரையில் திமிங்கலம் இறந்து கிடக்கிறது", "beached_aquatic_animal"),
        ("டால்பின் கரையில் மாட்டிக்கொண்டது", "beached_aquatic_animal"),
        ("கடல் ஆமை இறந்து கிடக்கிறது", "beached_aquatic_animal"),

        # Informal/casual reports (matching real user language patterns)
        ("whale died on beach please help", "beached_aquatic_animal"),
        ("there is whale died at coast please see", "beached_aquatic_animal"),
        ("whale is dead on beach come fast", "beached_aquatic_animal"),
        ("dead whale lying on shore", "beached_aquatic_animal"),
        ("whale died near beach please check", "beached_aquatic_animal"),
        ("one whale died at beach area", "beached_aquatic_animal"),
        ("big fish died on beach looks like whale", "beached_aquatic_animal"),
        ("whale body at beach please come", "beached_aquatic_animal"),
        ("dolphin died at beach need help", "beached_aquatic_animal"),
        ("there is dolphin died at shore", "beached_aquatic_animal"),
        ("dead dolphin at beach please see to it", "beached_aquatic_animal"),
        ("dolphin body found at coast", "beached_aquatic_animal"),
        ("turtle died on beach plastic problem", "beached_aquatic_animal"),
        ("sea turtle dead at shore please help", "beached_aquatic_animal"),
        ("there is big fish died on coast", "beached_aquatic_animal"),
        ("shark died at beach very big", "beached_aquatic_animal"),
        ("please see whale died at chennai beach", "beached_aquatic_animal"),
        ("whale died mumbai coast urgent", "beached_aquatic_animal"),
        ("dolphin died goa beach please come", "beached_aquatic_animal"),
        ("turtle died kerala coast help needed", "beached_aquatic_animal"),

        # Various description styles
        ("URGENT: Large marine mammal stranded on beach", "beached_aquatic_animal"),
        ("Alert: Whale beaching at local beach needs immediate attention", "beached_aquatic_animal"),
        ("Found a dead sea creature on the shore this morning", "beached_aquatic_animal"),
        ("Marine animal rescue needed at beach area", "beached_aquatic_animal"),
        ("Stranded marine life spotted near coast guard station", "beached_aquatic_animal"),
        ("Emergency: Dolphin stranding in progress", "beached_aquatic_animal"),
        ("Wildlife emergency - beached whale at beach", "beached_aquatic_animal"),
        ("Dead aquatic animal found by fishermen", "beached_aquatic_animal"),
        ("Sea creature washed up, looks like whale", "beached_aquatic_animal"),
        ("Ocean animal stranded on sandy beach", "beached_aquatic_animal"),
        ("Cetacean stranding reported at coastal area", "beached_aquatic_animal"),
        ("Marine mammal beached, needs veterinary help", "beached_aquatic_animal"),
        ("Aquatic life dying on beach, many fish and dolphins", "beached_aquatic_animal"),
        ("Beach covered with dead marine animals", "beached_aquatic_animal"),
        ("Whale stuck in shallow water near beach", "beached_aquatic_animal"),

        # With location context (Indian coastal areas)
        ("Porpoise found dead at Ratnagiri beach Maharashtra", "beached_aquatic_animal"),
        ("Sea cow stranded near Dwarka coast Gujarat", "beached_aquatic_animal"),
        ("Whale shark washed up at Diu beach", "beached_aquatic_animal"),
        ("Dolphin stranding at Puducherry coast", "beached_aquatic_animal"),
        ("Turtle carcass at Rushikonda beach Vizag", "beached_aquatic_animal"),
        ("Marine animal found at Chandipur beach Odisha", "beached_aquatic_animal"),
        ("Whale beaching at Tarkarli beach", "beached_aquatic_animal"),
        ("Dead dolphin at Karwar beach Karnataka", "beached_aquatic_animal"),
        ("Sea turtle at Mandarmani beach Bengal", "beached_aquatic_animal"),
        ("Stranded whale at Daman beach", "beached_aquatic_animal"),

        # Non-hazard / Spam examples
        ("Beautiful sunset at Marina Beach today! Perfect weather", "none"),
        ("Having amazing seafood at the restaurant by the shore", "none"),
        ("आज मौसम बहुत अच्छा है, समुद्री तट पर घूमने गए", "none"),
        ("Just chilling at the beach with friends", "none"),
        ("Planning beach vacation for next month", "none"),
        ("Fish market prices are high this season", "none"),
        ("New beach resort opening soon, great deals", "none"),
        ("Free iPhone giveaway, click link", "none"),
        ("Follow for more beach photos", "none"),
        ("Best food in coastal town, try it", "none"),
        ("मछली की कीमत आज बहुत ज्यादा है", "none"),
        ("नया होटल खुल रहा है समुद्र किनारे", "none"),
    ]

    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None):
        self.db = db
        self.model_name = settings.VECTORDB_MODEL_NAME
        self.embed_dim = settings.VECTORDB_EMBED_DIM
        self.model: Optional[SentenceTransformer] = None
        self.index: Optional[faiss.IndexFlatIP] = None
        self.labels: List[str] = []
        self.texts: List[str] = []
        self.metadata: List[Dict] = []
        self._initialized = False

    async def initialize(self):
        """Initialize model and FAISS index."""
        if self._initialized:
            return

        try:
            logger.info(f"Loading sentence transformer: {self.model_name}")

            # Set environment to avoid TensorFlow warnings
            os.environ['TRANSFORMERS_NO_TF'] = '1'
            os.environ['TOKENIZERS_PARALLELISM'] = 'false'

            self.model = SentenceTransformer(self.model_name)

            # Initialize FAISS index (Inner Product for cosine similarity)
            self.index = faiss.IndexFlatIP(self.embed_dim)

            # Load training data
            self._initialize_with_training_data()

            # Try to load persisted index if exists
            index_path = Path(settings.VECTORDB_INDEX_PATH)
            if index_path.with_suffix('.faiss').exists():
                await self.load_index(str(index_path))

            self._initialized = True
            logger.info(f"VectorDB initialized with {self.index.ntotal} vectors")

        except Exception as e:
            logger.error(f"Failed to initialize VectorDB: {e}")
            raise

    def _initialize_with_training_data(self):
        """Initialize FAISS index with training data."""
        texts = [item[0] for item in self.MARINE_TRAINING_DATA]
        labels = [item[1] for item in self.MARINE_TRAINING_DATA]

        # Generate embeddings
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        embeddings = embeddings.astype('float32')

        # Add to index
        self.index.add(embeddings)
        self.texts.extend(texts)
        self.labels.extend(labels)

        for i, (text, label) in enumerate(self.MARINE_TRAINING_DATA):
            self.metadata.append({
                "id": i,
                "text": text,
                "label": label,
                "source": "training_data",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

        logger.info(f"Initialized with {len(texts)} training samples")

    def encode_text(self, text: str) -> np.ndarray:
        """Encode text to vector embedding."""
        embedding = self.model.encode([text], normalize_embeddings=True)
        return embedding[0].astype('float32')

    def classify_hazard(
        self,
        text: str,
        threshold: float = None,
        top_k: int = 10
    ) -> ClassificationResult:
        """
        Classify text as HAZARD or NOT HAZARD.

        Args:
            text: Text to classify
            threshold: Classification threshold (default from config)
            top_k: Number of similar examples to consider

        Returns:
            ClassificationResult with classification, confidence, and similar examples
        """
        start_time = time.time()
        threshold = threshold or settings.VECTORDB_CLASSIFICATION_THRESHOLD

        # Search for similar examples
        similar = self.search_similar(text, k=top_k, threshold=0.3)

        if not similar:
            return ClassificationResult(
                classification="NOT_HAZARD",
                is_hazard=False,
                confidence=0.0,
                disaster_type="none",
                similar_examples=[],
                reasoning="No similar examples found in training data",
                processing_time_ms=(time.time() - start_time) * 1000
            )

        # Weighted voting by similarity score
        label_scores: Dict[str, float] = {}
        total_weight = 0.0

        for result in similar:
            label = result.label
            score = result.score
            weight = score ** 2  # Square for emphasis on high similarity

            label_scores[label] = label_scores.get(label, 0) + weight
            total_weight += weight

        # Normalize scores
        if total_weight > 0:
            for label in label_scores:
                label_scores[label] /= total_weight

        # Get best prediction
        best_label = max(label_scores.keys(), key=lambda k: label_scores[k])
        confidence = label_scores[best_label]

        # Determine if hazard
        is_hazard = best_label != "none" and confidence >= threshold

        # Generate reasoning
        if is_hazard:
            reasoning = f"Classified as {best_label.upper()} hazard with {confidence:.1%} confidence based on {len(similar)} similar examples"
        else:
            reasoning = f"Not classified as hazard. Best match: {best_label} with {confidence:.1%} confidence (threshold: {threshold:.1%})"

        return ClassificationResult(
            classification="HAZARD" if is_hazard else "NOT_HAZARD",
            is_hazard=is_hazard,
            confidence=confidence,
            disaster_type=best_label,
            similar_examples=similar[:5],  # Return top 5
            reasoning=reasoning,
            processing_time_ms=(time.time() - start_time) * 1000
        )

    def search_similar(
        self,
        query_text: str,
        k: int = 5,
        threshold: float = 0.5
    ) -> List[VectorSearchResult]:
        """Search for similar texts using FAISS."""
        query_embedding = self.encode_text(query_text).reshape(1, -1)

        scores, indices = self.index.search(query_embedding, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx != -1 and score >= threshold:
                results.append(VectorSearchResult(
                    rank=len(results) + 1,
                    score=float(score),
                    text=self.texts[idx],
                    label=self.labels[idx],
                    metadata=self.metadata[idx] if idx < len(self.metadata) else {}
                ))

        return results

    def add_sample(self, text: str, label: str, metadata: Dict = None):
        """Add new sample to the index."""
        embedding = self.encode_text(text)
        self.index.add(embedding.reshape(1, -1))

        self.texts.append(text)
        self.labels.append(label)
        self.metadata.append({
            "id": len(self.texts) - 1,
            "text": text,
            "label": label,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **(metadata or {})
        })

        logger.info(f"Added sample to VectorDB: {text[:50]}... -> {label}")

    async def save_index(self, filepath: str = None):
        """Persist FAISS index to disk."""
        filepath = filepath or settings.VECTORDB_INDEX_PATH

        # Ensure directory exists
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        faiss.write_index(self.index, f"{filepath}.faiss")

        with open(f"{filepath}.pkl", 'wb') as f:
            pickle.dump({
                "texts": self.texts,
                "labels": self.labels,
                "metadata": self.metadata,
                "model_name": self.model_name,
                "embed_dim": self.embed_dim
            }, f)

        logger.info(f"Saved VectorDB to {filepath}")

    async def load_index(self, filepath: str):
        """Load FAISS index from disk."""
        try:
            self.index = faiss.read_index(f"{filepath}.faiss")

            with open(f"{filepath}.pkl", 'rb') as f:
                data = pickle.load(f)
                self.texts = data["texts"]
                self.labels = data["labels"]
                self.metadata = data["metadata"]

            logger.info(f"Loaded VectorDB from {filepath} ({self.index.ntotal} vectors)")
        except Exception as e:
            logger.warning(f"Could not load index from {filepath}: {e}")

    def get_statistics(self) -> VectorDBStats:
        """Get VectorDB statistics."""
        label_counts = {}
        for label in self.labels:
            label_counts[label] = label_counts.get(label, 0) + 1

        return VectorDBStats(
            total_vectors=self.index.ntotal if self.index else 0,
            embedding_dimension=self.embed_dim,
            index_type="IndexFlatIP",
            model_name=self.model_name,
            label_distribution=label_counts,
            is_trained=self.index.is_trained if self.index else False,
            is_initialized=self._initialized
        )

    def batch_classify(
        self,
        texts: List[str],
        threshold: float = None
    ) -> List[ClassificationResult]:
        """Classify multiple texts."""
        return [self.classify_hazard(text, threshold) for text in texts]

    # =============================================================================
    # VERIFICATION LAYER METHODS (Enhanced for 6-layer pipeline)
    # =============================================================================

    def detect_spam(self, text: str) -> Tuple[bool, List[str]]:
        """
        Detect if text contains spam/promotional content.

        Args:
            text: Text to analyze

        Returns:
            Tuple of (is_spam, list of spam keywords found)
        """
        text_lower = text.lower()
        found_keywords = []

        for keyword in self.SPAM_KEYWORDS:
            if keyword.lower() in text_lower:
                found_keywords.append(keyword)

        # Text is spam if 2+ spam keywords found or contains URL patterns
        is_spam = len(found_keywords) >= 2 or any(
            pattern in text_lower
            for pattern in ["http://", "https://", "www.", ".com/"]
        )

        return is_spam, found_keywords

    def calculate_panic_level(self, text: str) -> float:
        """
        Calculate panic level of text (0.0 to 1.0).

        Factors:
        - Presence of panic keywords
        - Excessive exclamation marks
        - ALL CAPS usage
        - Repeated urgent phrases

        Args:
            text: Text to analyze

        Returns:
            Panic level from 0.0 (calm) to 1.0 (extreme panic)
        """
        panic_score = 0.0

        # Factor 1: Panic keywords (max 0.4)
        text_lower = text.lower()
        panic_keyword_count = sum(
            1 for keyword in self.PANIC_KEYWORDS
            if keyword.lower() in text_lower
        )
        panic_score += min(0.4, panic_keyword_count * 0.1)

        # Factor 2: Exclamation marks (max 0.2)
        exclamation_count = text.count('!')
        if exclamation_count > 0:
            panic_score += min(0.2, exclamation_count * 0.05)

        # Factor 3: ALL CAPS (max 0.2)
        words = text.split()
        if words:
            caps_ratio = sum(1 for w in words if w.isupper() and len(w) > 1) / len(words)
            panic_score += min(0.2, caps_ratio * 0.4)

        # Factor 4: Repeated punctuation (max 0.1)
        if re.search(r'[!?]{2,}', text):
            panic_score += 0.1

        # Factor 5: Urgency phrases (max 0.1)
        urgency_phrases = ["right now", "hurry", "asap", "immediately", "जल्दी करो"]
        for phrase in urgency_phrases:
            if phrase.lower() in text_lower:
                panic_score += 0.05

        return min(1.0, panic_score)

    async def analyze_for_verification(
        self,
        text: str,
        reported_hazard_type: str
    ) -> LayerResult:
        """
        Analyze text for the verification pipeline (Layer 3).

        Combines:
        - Vector similarity classification
        - Spam detection
        - Panic level scoring
        - Type match validation

        Args:
            text: Report description text
            reported_hazard_type: The hazard type reported by user

        Returns:
            LayerResult for the text analysis layer
        """
        start_time = time.time()

        try:
            # 1. Spam detection
            is_spam, spam_keywords = self.detect_spam(text)

            if is_spam:
                return LayerResult(
                    layer_name=LayerName.TEXT,
                    status=LayerStatus.FAIL,
                    score=0.0,
                    confidence=0.95,
                    weight=0.25,
                    reasoning=f"Text appears to be spam/promotional content. Found keywords: {', '.join(spam_keywords[:5])}",
                    data=TextLayerData(
                        description=text[:200],
                        predicted_hazard_type="none",
                        classification_confidence=0.0,
                        similarity_score=0.0,
                        panic_level=0.0,
                        is_spam=True,
                        spam_keywords_found=spam_keywords,
                        top_matches=[]
                    ).model_dump(),
                    processed_at=datetime.now(timezone.utc)
                )

            # 2. Panic level calculation
            panic_level = self.calculate_panic_level(text)

            # 3. Vector similarity classification
            classification = self.classify_hazard(text, top_k=10)

            # 4. Get top matches for layer data
            similar_results = self.search_similar(text, k=3, threshold=0.3)
            top_matches = [
                {"text": r.text[:100], "label": r.label, "score": r.score}
                for r in similar_results
            ]

            # 5. Map predicted type to system hazard type
            predicted_type = classification.disaster_type
            similarity_score = classification.confidence

            # 6. Calculate final score
            # Score components:
            # - Similarity score (50%): How well text matches known hazard patterns
            # - Classification confidence (30%): Confidence in predicted type
            # - Inverse panic penalty (20%): Lower panic = higher score (calm, descriptive reports are better)

            # For natural hazards and emergency situations, panic is expected, so we don't penalize
            # Also include beached_aquatic_animal as urgent rescue appeals are valid
            emergency_hazards = [
                "tsunami", "cyclone", "high_waves", "coastal_flood", "rip_currents",
                "beached_aquatic_animal", "ship_stranding"  # Rescue situations where urgency is valid
            ]
            is_emergency = predicted_type in emergency_hazards

            panic_penalty = 0.0 if is_emergency else (panic_level * 0.3)  # Only penalize for non-emergency hazards

            score = (
                (similarity_score * 0.5) +
                (classification.confidence * 0.3) +
                ((1.0 - panic_penalty) * 0.2)
            )

            # 7. Determine status
            if score >= 0.5 and classification.is_hazard:
                status = LayerStatus.PASS
                reasoning = (
                    f"Text analysis successful. Predicted: {predicted_type} "
                    f"(confidence: {classification.confidence:.1%}). "
                    f"Semantic similarity: {similarity_score:.1%}. "
                    f"Panic level: {panic_level:.1%}."
                )
            elif classification.is_hazard:
                status = LayerStatus.PASS
                reasoning = (
                    f"Text indicates hazard but with moderate confidence. "
                    f"Predicted: {predicted_type} ({classification.confidence:.1%}). "
                    f"Manual review recommended."
                )
            else:
                status = LayerStatus.FAIL
                reasoning = (
                    f"Text does not match known hazard patterns. "
                    f"Best match: {predicted_type} ({classification.confidence:.1%}). "
                    f"May be non-hazard content."
                )

            # Build layer data
            layer_data = TextLayerData(
                description=text[:500],  # Truncate for storage
                predicted_hazard_type=predicted_type,
                classification_confidence=classification.confidence,
                similarity_score=similarity_score,
                panic_level=panic_level,
                is_spam=False,
                spam_keywords_found=[],
                top_matches=top_matches
            )

            processing_time = (time.time() - start_time) * 1000

            return LayerResult(
                layer_name=LayerName.TEXT,
                status=status,
                score=max(0.0, min(1.0, score)),
                confidence=classification.confidence,
                weight=0.25,
                reasoning=reasoning,
                data=layer_data.model_dump(),
                processed_at=datetime.now(timezone.utc)
            )

        except Exception as e:
            logger.error(f"Text analysis error: {e}")
            return LayerResult(
                layer_name=LayerName.TEXT,
                status=LayerStatus.FAIL,
                score=0.5,  # Partial score for system error
                confidence=0.0,
                weight=0.25,
                reasoning=f"Text analysis failed: {str(e)}",
                data={"error": str(e), "text": text[:100]},
                processed_at=datetime.now(timezone.utc)
            )


# Singleton instance
_vectordb_service: Optional[VectorDBService] = None


def get_vectordb_service(db: Optional[AsyncIOMotorDatabase] = None) -> VectorDBService:
    """Get VectorDB service instance."""
    global _vectordb_service
    if _vectordb_service is None:
        _vectordb_service = VectorDBService(db)
    return _vectordb_service


async def initialize_vectordb_service(db: AsyncIOMotorDatabase) -> VectorDBService:
    """Initialize VectorDB service."""
    service = get_vectordb_service(db)
    await service.initialize()
    return service
