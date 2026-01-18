"""
VectorDB API Routes
FAISS-based hazard classification endpoints
"""

import logging
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_database
from app.models.user import User
from app.middleware.rbac import get_current_user, require_analyst
from app.services.vectordb_service import get_vectordb_service, VectorDBService
from app.models.vectordb import (
    ClassifyRequest, BatchClassifyRequest, AddSampleRequest,
    SearchRequest, SearchResponse, ClassificationResult,
    BatchClassifyResponse, VectorDBStats, VectorDBHealthResponse,
    VectorDBResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vectordb", tags=["VectorDB"])


# Dependency to get VectorDB service
async def get_service(
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> VectorDBService:
    """Get initialized VectorDB service."""
    service = get_vectordb_service(db)
    if not service._initialized:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="VectorDB service not initialized"
        )
    return service


# =============================================================================
# PUBLIC ENDPOINTS (No Authentication)
# =============================================================================

@router.get("/health", response_model=VectorDBHealthResponse)
async def health_check():
    """
    Health check for VectorDB service.
    Public endpoint - no authentication required.
    """
    try:
        service = get_vectordb_service()
        stats = service.get_statistics() if service._initialized else None

        return VectorDBHealthResponse(
            status="healthy" if service._initialized else "not_initialized",
            initialized=service._initialized,
            model_loaded=service.model is not None,
            index_size=stats.total_vectors if stats else 0,
            timestamp=datetime.now(timezone.utc)
        )
    except Exception as e:
        logger.error(f"VectorDB health check failed: {e}")
        return VectorDBHealthResponse(
            status="error",
            initialized=False,
            model_loaded=False,
            index_size=0,
            timestamp=datetime.now(timezone.utc)
        )


# =============================================================================
# ANALYST ENDPOINTS (Requires Authentication)
# =============================================================================

@router.get("/stats", response_model=VectorDBStats)
async def get_statistics(
    current_user: User = Depends(require_analyst),
    service: VectorDBService = Depends(get_service)
):
    """
    Get VectorDB index statistics.
    Requires Analyst role or higher.
    """
    return service.get_statistics()


@router.post("/classify", response_model=ClassificationResult)
async def classify_text(
    request: ClassifyRequest,
    current_user: User = Depends(require_analyst),
    service: VectorDBService = Depends(get_service)
):
    """
    Classify a single text as HAZARD or NOT_HAZARD.

    Returns the classification, confidence, disaster type, and similar examples.
    Requires Analyst role or higher.
    """
    try:
        result = service.classify_hazard(
            text=request.text,
            threshold=request.threshold,
            top_k=request.top_k if request.include_similar else 1
        )

        if not request.include_similar:
            result.similar_examples = []

        return result

    except Exception as e:
        logger.error(f"Classification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Classification failed: {str(e)}"
        )


@router.post("/classify/batch", response_model=BatchClassifyResponse)
async def batch_classify(
    request: BatchClassifyRequest,
    current_user: User = Depends(require_analyst),
    service: VectorDBService = Depends(get_service)
):
    """
    Classify multiple texts in batch.

    Returns classification results for each text.
    Requires Analyst role or higher.
    """
    import time
    start_time = time.time()

    try:
        results = service.batch_classify(
            texts=request.texts,
            threshold=request.threshold
        )

        hazard_count = sum(1 for r in results if r.is_hazard)
        processing_time = (time.time() - start_time) * 1000

        return BatchClassifyResponse(
            results=results,
            total_processed=len(results),
            hazard_count=hazard_count,
            processing_time_ms=processing_time
        )

    except Exception as e:
        logger.error(f"Batch classification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch classification failed: {str(e)}"
        )


@router.post("/search", response_model=SearchResponse)
async def search_similar(
    request: SearchRequest,
    current_user: User = Depends(require_analyst),
    service: VectorDBService = Depends(get_service)
):
    """
    Search for similar texts in the VectorDB.

    Returns ranked results with similarity scores.
    Requires Analyst role or higher.
    """
    import time
    start_time = time.time()

    try:
        results = service.search_similar(
            query_text=request.query,
            k=request.top_k,
            threshold=request.threshold
        )

        processing_time = (time.time() - start_time) * 1000

        return SearchResponse(
            query=request.query,
            results=results,
            total_results=len(results),
            processing_time_ms=processing_time
        )

    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


# =============================================================================
# ADMIN ENDPOINTS (Requires Admin Role)
# =============================================================================

@router.post("/sample", response_model=VectorDBResponse)
async def add_training_sample(
    request: AddSampleRequest,
    current_user: User = Depends(require_analyst),
    service: VectorDBService = Depends(get_service),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Add a new training sample to the VectorDB.

    This expands the classification capability for new examples.
    Requires Analyst role or higher.
    """
    try:
        # Add metadata about who added it
        metadata = request.metadata or {}
        metadata["added_by"] = current_user.user_id
        metadata["added_at"] = datetime.now(timezone.utc).isoformat()

        service.add_sample(
            text=request.text,
            label=request.label,
            metadata=metadata
        )

        # Also save to database for persistence
        if db is not None:
            await db.vectordb_samples.insert_one({
                "text": request.text,
                "label": request.label,
                "metadata": metadata,
                "added_by": current_user.user_id,
                "created_at": datetime.now(timezone.utc)
            })

        logger.info(f"Added training sample: {request.text[:50]}... -> {request.label} by {current_user.user_id}")

        return VectorDBResponse(
            success=True,
            data={
                "message": "Sample added successfully",
                "label": request.label,
                "index_size": service.index.ntotal
            }
        )

    except Exception as e:
        logger.error(f"Add sample error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add sample: {str(e)}"
        )


@router.post("/save", response_model=VectorDBResponse)
async def save_index(
    current_user: User = Depends(require_analyst),
    service: VectorDBService = Depends(get_service)
):
    """
    Save the current VectorDB index to disk.

    This persists any new training samples added during runtime.
    Requires Analyst role or higher.
    """
    try:
        await service.save_index()

        return VectorDBResponse(
            success=True,
            data={
                "message": "Index saved successfully",
                "index_size": service.index.ntotal
            }
        )

    except Exception as e:
        logger.error(f"Save index error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save index: {str(e)}"
        )


# =============================================================================
# PUBLIC CLASSIFICATION ENDPOINT (For frontend widgets)
# =============================================================================

@router.post("/public/classify", response_model=ClassificationResult)
async def public_classify(
    request: ClassifyRequest
):
    """
    Public classification endpoint for frontend widgets.

    Limited functionality - no authentication required.
    Does not return similar examples for privacy.
    """
    try:
        service = get_vectordb_service()
        if not service._initialized:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="VectorDB service not initialized"
            )

        result = service.classify_hazard(
            text=request.text,
            threshold=request.threshold,
            top_k=5
        )

        # Remove similar examples for public endpoint
        result.similar_examples = []

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Public classification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Classification service unavailable"
        )
