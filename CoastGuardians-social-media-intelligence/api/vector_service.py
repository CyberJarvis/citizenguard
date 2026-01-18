"""
Coast Guardian FAISS Vector Service
Advanced similarity-based marine disaster detection using FAISS and Sentence Transformers
Adapted from user's existing HazardVectorDB implementation
"""

import os
import json
import numpy as np
import faiss
import pickle
from typing import List, Tuple, Dict, Any, Optional
from datetime import datetime
import logging
from sentence_transformers import SentenceTransformer

from api.models import SocialMediaPost, DisasterType

logger = logging.getLogger(__name__)

class CoastGuardianVectorDB:
    """Advanced FAISS-based vector database for marine disaster classification"""

    def __init__(
        self,
        model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        embed_dim: int = 384,
        index_type: str = "IndexFlatIP"  # Inner Product for cosine similarity
    ):
        self.model_name = model_name
        self.embed_dim = embed_dim
        self.index_type = index_type

        # Initialize sentence transformer
        try:
            self.model = SentenceTransformer(model_name)
            logger.info(f"Loaded sentence transformer: {model_name}")
        except Exception as e:
            logger.error(f"Failed to load sentence transformer: {e}")
            raise

        # Initialize FAISS index
        if index_type == "IndexFlatIP":
            self.index = faiss.IndexFlatIP(embed_dim)
        elif index_type == "IndexFlatL2":
            self.index = faiss.IndexFlatL2(embed_dim)
        else:
            raise ValueError(f"Unsupported index type: {index_type}")

        # Storage for metadata
        self.labels = []  # disaster types
        self.texts = []   # original texts
        self.metadata = []  # additional metadata

        # Marine disaster training data
        self.marine_training_data = self._get_marine_training_data()

        # Initialize with training data
        self._initialize_with_training_data()

    def _get_marine_training_data(self) -> List[Tuple[str, str]]:
        """Enhanced marine disaster training data for FAISS classification"""
        return [
            # Tsunami examples
            ("🚨 ALERT: Massive tsunami waves approaching Mumbai coast! Evacuation orders issued", "tsunami"),
            ("समुद्री लहरें तेज़ी से आ रही हैं, तुरंत ऊंची जगह जाएं", "tsunami"),
            ("சுனாமி எச்சரிக்கை! கடற்கரையில் இருந்து வெளியேறுங்கள்", "tsunami"),
            ("海啸警报！请立即撤离海岸地区", "tsunami"),
            ("Giant waves hitting the shore, people running inland", "tsunami"),
            ("सुनामी की लहरें आ रही हैं, सुरक्षित स्थान पर जाएं", "tsunami"),

            # Cyclone examples
            ("Cyclone Nisarga approaching Maharashtra coast, winds 120 kmph", "cyclone"),
            ("चक्रवात अलर्ट! तेज़ हवाओं से बचकर रहें", "cyclone"),
            ("புயல் எச்சரிக்கை - வலுவான காற்று வீசுகிறது", "cyclone"),
            ("Severe cyclonic storm with heavy rainfall expected", "cyclone"),
            ("Coastal areas under cyclone warning, evacuate immediately", "cyclone"),
            ("तूफान आ रहा है, सभी मछुआरे वापस आ जाएं", "cyclone"),

            # Oil Spill examples
            ("Oil spill spotted near Kochi port! Environmental disaster", "oil_spill"),
            ("समुद्र में तेल फैल गया है, मछली न खाएं", "oil_spill"),
            ("கடலில் எண்ணெய் கசிவு - மீன் பிடிப்பதை நிறுத்துங்கள்", "oil_spill"),
            ("Black thick oil covering the beach, wildlife affected", "oil_spill"),
            ("Ship leaked oil into Arabian Sea near Mumbai", "oil_spill"),
            ("समुद्री तट पर काला तेल दिख रहा है", "oil_spill"),

            # Flooding examples
            ("Heavy rains caused flooding in coastal areas of Chennai", "flooding"),
            ("बाढ़ का पानी घरों में घुस गया है", "flooding"),
            ("வெள்ளம் காரணமாக பல குடும்பங்கள் சிக்கித் தவிக்கின்றன", "flooding"),
            ("Streets flooded due to high tide and heavy monsoon", "flooding"),
            ("Coastal flooding emergency in Kerala backwaters", "flooding"),
            ("समुद्री तूफान से बाढ़ आ गई है", "flooding"),

            # Earthquake examples
            ("Strong earthquake felt in Andaman Islands, magnitude 6.2", "earthquake"),
            ("भूकंप के झटके महसूस हुए, समुद्र के पास न जाएं", "earthquake"),
            ("நிலநடుக்கம் உணரப்பட்டது - கடற்கரைக்கு அருகில் செல்லாதீர்கள்", "earthquake"),
            ("Tremors felt across coastal Karnataka after quake", "earthquake"),
            ("Underwater earthquake detected, tsunami possibility", "earthquake"),
            ("समुद्र के नीचे भूकंप आया है", "earthquake"),

            # Non-disaster examples (spam/normal)
            ("Beautiful sunset at Marina Beach today! Perfect weather 🌅", "none"),
            ("Having amazing seafood at the restaurant by the shore", "none"),
            ("आज मौसम बहुत अच्छा है, समुद्री तट पर घूमने गए", "none"),
            ("கடற்கரையில் நண்பர்களுடன் அருமையான நேரம்", "none"),
            ("Just chilling at the beach with friends 😎", "none"),
            ("मछली पकड़ने गए थे, अच्छा दिन था", "none"),
            ("Planning beach vacation for next month", "none"),
            ("समुद्री किनारे योग कक्षा में भाग लिया", "none"),
        ]

    def _initialize_with_training_data(self):
        """Initialize FAISS index with marine training data"""
        try:
            texts = [item[0] for item in self.marine_training_data]
            labels = [item[1] for item in self.marine_training_data]

            # Generate embeddings
            embeddings = self.model.encode(texts, normalize_embeddings=True)
            embeddings = embeddings.astype('float32')

            # Add to index
            self.index.add(embeddings)
            self.texts.extend(texts)
            self.labels.extend(labels)

            # Create metadata
            for i, (text, label) in enumerate(self.marine_training_data):
                self.metadata.append({
                    "id": i,
                    "text": text,
                    "label": label,
                    "source": "training_data",
                    "timestamp": datetime.now().isoformat()
                })

            logger.info(f"Initialized FAISS index with {len(texts)} training samples")

        except Exception as e:
            logger.error(f"Failed to initialize training data: {e}")
            raise

    def encode_text(self, text: str) -> np.ndarray:
        """Encode text into vector embedding"""
        try:
            embedding = self.model.encode([text], normalize_embeddings=True)
            return embedding[0].astype('float32')
        except Exception as e:
            logger.error(f"Failed to encode text: {e}")
            raise

    def add_text(self, text: str, label: str, metadata: Dict[str, Any] = None):
        """Add new text to the vector database"""
        try:
            # Generate embedding
            embedding = self.encode_text(text)

            # Add to index
            self.index.add(embedding.reshape(1, -1))

            # Store metadata
            self.texts.append(text)
            self.labels.append(label)

            metadata_entry = {
                "id": len(self.texts) - 1,
                "text": text,
                "label": label,
                "timestamp": datetime.now().isoformat(),
                **(metadata or {})
            }
            self.metadata.append(metadata_entry)

            logger.debug(f"Added text to vector DB: {text[:50]}...")

        except Exception as e:
            logger.error(f"Failed to add text: {e}")
            raise

    def search_similar(
        self,
        query_text: str,
        k: int = 5,
        threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Search for similar texts using FAISS"""
        try:
            # Encode query
            query_embedding = self.encode_text(query_text)
            query_embedding = query_embedding.reshape(1, -1)

            # Search
            scores, indices = self.index.search(query_embedding, k)

            results = []
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx != -1 and score >= threshold:  # Valid result above threshold
                    results.append({
                        "rank": i + 1,
                        "score": float(score),
                        "text": self.texts[idx],
                        "label": self.labels[idx],
                        "metadata": self.metadata[idx] if idx < len(self.metadata) else {}
                    })

            return results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def classify_disaster_type(
        self,
        text: str,
        confidence_threshold: float = 0.6
    ) -> Tuple[str, float, List[Dict[str, Any]]]:
        """Classify text for disaster type using similarity search"""
        try:
            # Search for similar examples
            similar_results = self.search_similar(text, k=10, threshold=0.3)

            if not similar_results:
                return "none", 0.0, []

            # Count labels by similarity score (weighted voting)
            label_scores = {}
            total_weight = 0

            for result in similar_results:
                label = result['label']
                score = result['score']
                weight = score ** 2  # Square for emphasis on high similarity

                if label not in label_scores:
                    label_scores[label] = 0
                label_scores[label] += weight
                total_weight += weight

            # Normalize scores
            if total_weight > 0:
                for label in label_scores:
                    label_scores[label] /= total_weight

            # Get best prediction
            if label_scores:
                best_label = max(label_scores.items(), key=lambda x: x[1])
                predicted_label, confidence = best_label

                # Apply confidence threshold
                if confidence >= confidence_threshold:
                    return predicted_label, confidence, similar_results
                else:
                    return "none", confidence, similar_results

            return "none", 0.0, similar_results

        except Exception as e:
            logger.error(f"Classification failed: {e}")
            return "none", 0.0, []

    def get_disaster_confidence(self, text: str) -> Dict[str, float]:
        """Get confidence scores for all disaster types"""
        try:
            similar_results = self.search_similar(text, k=20, threshold=0.1)

            # Initialize all disaster types
            disaster_types = ["tsunami", "cyclone", "oil_spill", "flooding", "earthquake", "none"]
            confidence_scores = {dt: 0.0 for dt in disaster_types}

            if not similar_results:
                return confidence_scores

            # Calculate weighted scores for each disaster type
            total_weight = 0
            for result in similar_results:
                score = result['score']
                label = result['label']
                weight = score ** 2

                if label in confidence_scores:
                    confidence_scores[label] += weight
                total_weight += weight

            # Normalize
            if total_weight > 0:
                for label in confidence_scores:
                    confidence_scores[label] /= total_weight

            return confidence_scores

        except Exception as e:
            logger.error(f"Failed to get confidence scores: {e}")
            return {dt: 0.0 for dt in ["tsunami", "cyclone", "oil_spill", "flooding", "earthquake", "none"]}

    def enhance_post_analysis(self, post: SocialMediaPost) -> Dict[str, Any]:
        """Enhance post analysis with vector similarity insights"""
        try:
            # Get disaster classification
            predicted_type, confidence, similar_results = self.classify_disaster_type(post.text)

            # Get all confidence scores
            all_confidences = self.get_disaster_confidence(post.text)

            # Calculate similarity-based relevance score
            relevance_score = max(all_confidences.values()) * 10  # Scale to 0-10

            # Find most similar marine disaster example
            marine_similar = [r for r in similar_results if r['label'] != 'none'][:3]

            enhancement = {
                "vector_classification": {
                    "predicted_disaster_type": predicted_type,
                    "confidence": round(confidence, 3),
                    "relevance_score": round(relevance_score, 1),
                    "all_confidences": {k: round(v, 3) for k, v in all_confidences.items()}
                },
                "similar_examples": similar_results[:5],
                "marine_similar_examples": marine_similar,
                "vector_keywords": self._extract_keywords_from_similar(similar_results),
                "classification_reasoning": self._generate_reasoning(predicted_type, confidence, similar_results)
            }

            return enhancement

        except Exception as e:
            logger.error(f"Failed to enhance analysis: {e}")
            return {"vector_classification": {"error": str(e)}}

    def _extract_keywords_from_similar(self, similar_results: List[Dict[str, Any]]) -> List[str]:
        """Extract keywords from similar results"""
        keywords = set()
        marine_keywords = {
            'tsunami', 'waves', 'coastal', 'evacuation', 'cyclone', 'storm', 'flooding',
            'oil', 'spill', 'earthquake', 'tremor', 'sea', 'ocean', 'beach', 'port',
            'emergency', 'alert', 'warning', 'disaster', 'marine', 'maritime'
        }

        for result in similar_results[:3]:  # Top 3 results
            text = result['text'].lower()
            for keyword in marine_keywords:
                if keyword in text:
                    keywords.add(keyword)

        return list(keywords)[:10]  # Limit to 10 keywords

    def _generate_reasoning(
        self,
        predicted_type: str,
        confidence: float,
        similar_results: List[Dict[str, Any]]
    ) -> str:
        """Generate human-readable reasoning for classification"""
        if confidence < 0.3:
            return "Low similarity to known marine disaster patterns"
        elif confidence < 0.6:
            return f"Moderate similarity to {predicted_type} patterns, but uncertain"
        else:
            similar_count = len([r for r in similar_results if r['label'] == predicted_type])
            return f"Strong similarity to {predicted_type} patterns ({similar_count} similar examples found)"

    def save_index(self, filepath: str):
        """Save FAISS index and metadata"""
        try:
            # Save FAISS index
            faiss.write_index(self.index, f"{filepath}.faiss")

            # Save metadata
            metadata = {
                "texts": self.texts,
                "labels": self.labels,
                "metadata": self.metadata,
                "model_name": self.model_name,
                "embed_dim": self.embed_dim,
                "index_type": self.index_type
            }

            with open(f"{filepath}.pkl", 'wb') as f:
                pickle.dump(metadata, f)

            logger.info(f"Saved vector database to {filepath}")

        except Exception as e:
            logger.error(f"Failed to save index: {e}")
            raise

    def load_index(self, filepath: str):
        """Load FAISS index and metadata"""
        try:
            # Load FAISS index
            self.index = faiss.read_index(f"{filepath}.faiss")

            # Load metadata
            with open(f"{filepath}.pkl", 'rb') as f:
                metadata = pickle.load(f)

            self.texts = metadata["texts"]
            self.labels = metadata["labels"]
            self.metadata = metadata["metadata"]

            logger.info(f"Loaded vector database from {filepath}")

        except Exception as e:
            logger.error(f"Failed to load index: {e}")
            raise

    def get_statistics(self) -> Dict[str, Any]:
        """Get vector database statistics"""
        try:
            label_counts = {}
            for label in self.labels:
                label_counts[label] = label_counts.get(label, 0) + 1

            return {
                "total_vectors": self.index.ntotal,
                "embedding_dimension": self.embed_dim,
                "index_type": self.index_type,
                "model_name": self.model_name,
                "label_distribution": label_counts,
                "is_trained": self.index.is_trained
            }
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {"error": str(e)}

# Global instance (will be initialized in main.py)
vector_db = None

def initialize_vector_db() -> CoastGuardianVectorDB:
    """Initialize global vector database instance"""
    global vector_db
    if vector_db is None:
        vector_db = CoastGuardianVectorDB()
    return vector_db

def get_vector_db() -> Optional[CoastGuardianVectorDB]:
    """Get global vector database instance"""
    return vector_db