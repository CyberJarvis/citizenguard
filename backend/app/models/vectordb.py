"""
VectorDB Models
Pydantic models for FAISS-based hazard classification
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


# Type definitions
HazardClassification = Literal["HAZARD", "NOT_HAZARD"]
DisasterType = Literal[
    "tsunami", "cyclone", "high_waves", "coastal_flood", "rip_currents",
    "oil_spill", "ship_stranding", "illegal_fishing", "beached_aquatic_animal", "none"
]


class VectorSearchResult(BaseModel):
    """Single result from vector similarity search"""
    rank: int = Field(..., description="Result ranking (1 = most similar)")
    score: float = Field(..., ge=0.0, le=1.0, description="Similarity score")
    text: str = Field(..., description="Original text")
    label: str = Field(..., description="Classification label")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ClassificationResult(BaseModel):
    """Result of hazard classification"""
    classification: HazardClassification = Field(..., description="HAZARD or NOT_HAZARD")
    is_hazard: bool = Field(..., description="True if classified as hazard")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Classification confidence")
    disaster_type: DisasterType = Field(..., description="Specific disaster type detected")
    similar_examples: List[VectorSearchResult] = Field(default_factory=list, description="Similar examples from training data")
    reasoning: str = Field(default="", description="Explanation for classification")
    processing_time_ms: Optional[float] = Field(default=None, description="Processing time in milliseconds")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Classification timestamp")


class VectorDBStats(BaseModel):
    """VectorDB index statistics"""
    total_vectors: int = Field(..., description="Total number of vectors in index")
    embedding_dimension: int = Field(..., description="Dimension of embeddings")
    index_type: str = Field(..., description="FAISS index type")
    model_name: str = Field(..., description="Sentence transformer model name")
    label_distribution: Dict[str, int] = Field(..., description="Count of each label")
    is_trained: bool = Field(..., description="Whether index is trained")
    is_initialized: bool = Field(..., description="Whether service is initialized")


# Request Models

class ClassifyRequest(BaseModel):
    """Request to classify a single text"""
    text: str = Field(..., min_length=1, max_length=2000, description="Text to classify")
    threshold: float = Field(default=0.6, ge=0.0, le=1.0, description="Classification threshold")
    include_similar: bool = Field(default=True, description="Include similar examples in response")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of similar examples to return")

    class Config:
        json_schema_extra = {
            "example": {
                "text": "Massive waves hitting the coast, people evacuating",
                "threshold": 0.6,
                "include_similar": True,
                "top_k": 5
            }
        }


class BatchClassifyRequest(BaseModel):
    """Request to classify multiple texts"""
    texts: List[str] = Field(..., min_length=1, max_length=100, description="Texts to classify")
    threshold: float = Field(default=0.6, ge=0.0, le=1.0, description="Classification threshold")

    class Config:
        json_schema_extra = {
            "example": {
                "texts": [
                    "Tsunami warning issued for coastal areas",
                    "Free iPhone giveaway click here"
                ],
                "threshold": 0.6
            }
        }


class BatchClassifyResponse(BaseModel):
    """Response for batch classification"""
    results: List[ClassificationResult] = Field(..., description="Classification results")
    total_processed: int = Field(..., description="Total texts processed")
    hazard_count: int = Field(..., description="Number classified as HAZARD")
    processing_time_ms: float = Field(..., description="Total processing time")


class AddSampleRequest(BaseModel):
    """Request to add a new training sample"""
    text: str = Field(..., min_length=1, max_length=2000, description="Sample text")
    label: DisasterType = Field(..., description="Classification label")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "text": "Heavy flooding reported in Mumbai suburbs",
                "label": "coastal_flood",
                "metadata": {"source": "manual_entry", "language": "en"}
            }
        }


class SearchRequest(BaseModel):
    """Request to search for similar texts"""
    query: str = Field(..., min_length=1, max_length=2000, description="Search query")
    top_k: int = Field(default=10, ge=1, le=50, description="Number of results")
    threshold: float = Field(default=0.3, ge=0.0, le=1.0, description="Minimum similarity threshold")


class SearchResponse(BaseModel):
    """Response for similarity search"""
    query: str = Field(..., description="Original query")
    results: List[VectorSearchResult] = Field(..., description="Search results")
    total_results: int = Field(..., description="Number of results returned")
    processing_time_ms: float = Field(..., description="Search time in milliseconds")


# Response wrappers

class VectorDBHealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service status")
    initialized: bool = Field(..., description="Whether service is initialized")
    model_loaded: bool = Field(..., description="Whether model is loaded")
    index_size: int = Field(..., description="Number of vectors in index")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class VectorDBResponse(BaseModel):
    """Generic VectorDB API response"""
    success: bool = Field(..., description="Operation success status")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Response data")
    error: Optional[str] = Field(default=None, description="Error message if failed")
