import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio
import json

from src.services.rumination.structured_insight_service import StructuredInsightService
from src.api.dependencies import get_insight_service, get_document_repository
from src.models.rumination.structured_insight import StructuredInsight, Annotation
from src.repositories.interfaces.document_repository import DocumentRepository
from src.models.viewer.block import Block

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set to DEBUG level for detailed logging

router = APIRouter(prefix="/insights", tags=["insights"])

class AnalyzeBlockRequest(BaseModel):
    block_id: str
    page_number: int
    block_content: str
    document_id: str

class RuminateRequest(BaseModel):
    document_id: str
    objective: str

class RuminationStatus:
    PENDING = "pending"
    COMPLETE = "complete"
    ERROR = "error"

_rumination_status = {}  # Store status for each document
_current_block = {}  # Store current block being processed for each document

async def rumination_event_generator(request: Request, insight_service: StructuredInsightService, document_id: str):
    """Generate SSE events for rumination progress"""
    try:
        while True:
            # Check if client closed connection
            if await request.is_disconnected():
                break

            # Get latest insights for the document
            insights = await insight_service.get_document_insights(document_id)
            
            # Get current status and block
            status = _rumination_status.get(document_id, RuminationStatus.PENDING)
            current_block_id = _current_block.get(document_id)
            
            # Send the insights and status as an SSE event
            yield f"data: {json.dumps({'insights': [insight.dict() for insight in insights], 'status': status,'current_block_id': current_block_id})}\n\n"
            
            # If complete or error, stop streaming
            if status in [RuminationStatus.COMPLETE, RuminationStatus.ERROR]:
                # Clear current block
                _current_block.pop(document_id, None)
                break
                
            # Wait a bit before next update
            await asyncio.sleep(1)
    except Exception as e:
        _rumination_status[document_id] = RuminationStatus.ERROR
        _current_block.pop(document_id, None)
        yield f"data: {json.dumps({'error': str(e), 'status': RuminationStatus.ERROR,'current_block_id': None})}\n\n"

@router.get("/ruminate/stream/{document_id}")
async def stream_rumination(    
    request: Request,
    document_id: str,
    insight_service: StructuredInsightService = Depends(get_insight_service)
) -> StreamingResponse:
    """Stream rumination progress as Server-Sent Events"""
    return StreamingResponse(
        rumination_event_generator(request, insight_service, document_id),
        media_type="text/event-stream"
    )

@router.post("/ruminate")
async def start_rumination(
    request: RuminateRequest,
    insight_service: StructuredInsightService = Depends(get_insight_service),
    document_repository: DocumentRepository = Depends(get_document_repository)
) -> dict:
    """Start the rumination process for a document"""
    try:
        logger.debug(f"Starting rumination for document_id: {request.document_id}")
        logger.debug(f"Objective: {request.objective}")
        
        # Reset status for this document
        _rumination_status[request.document_id] = RuminationStatus.PENDING
        
        # Get all blocks for the document
        blocks = await document_repository.get_blocks(request.document_id)
        if not blocks:
            raise HTTPException(status_code=404, detail="No blocks found for document")
            
        logger.debug(f"Found {len(blocks)} blocks to process")
        
        # Start async task to process blocks
        asyncio.create_task(process_document_blocks(blocks, insight_service, request.document_id))
        
        return {"status": "started", "document_id": request.document_id}
    except Exception as e:
        _rumination_status[request.document_id] = RuminationStatus.ERROR
        logger.error(f"Error starting rumination: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_document_blocks(blocks: List[Block], insight_service: StructuredInsightService, document_id: str):
    """Process all blocks in a document asynchronously"""
    try:
        logger.debug(f"Starting to process {len(blocks)} blocks")
        for block in blocks:
            if block.block_type and block.block_type.lower() == "text":
                try:
                    # Set current block being processed
                    _current_block[document_id] = block.id
                    logger.debug(f"Processing block {block.id} of type {block.block_type}")
                    
                    await insight_service.analyze_block(block)
                    logger.debug(f"Processed block {block.id}")
                except Exception as block_error:
                    logger.error(f"Error processing block {block.id}: {str(block_error)}")
                    continue
            else:
                logger.debug(f"Skipping non-text block {block.id} of type {block.block_type}")
        
        # Set status to complete after all blocks are processed
        _rumination_status[document_id] = RuminationStatus.COMPLETE
        # Clear current block
        _current_block.pop(document_id, None)
        logger.debug(f"Completed rumination for document {document_id}")
    except Exception as e:
        logger.error(f"Error in process_document_blocks: {str(e)}", exc_info=True)
        _rumination_status[document_id] = RuminationStatus.ERROR
        _current_block.pop(document_id, None)

@router.get("/block/{block_id}", response_model=StructuredInsight)
async def get_block_insight(
    block_id: str,
    insight_service: StructuredInsightService = Depends(get_insight_service),
    document_repository: DocumentRepository = Depends(get_document_repository)
) -> StructuredInsight:
    """Get insights for a specific block"""
    try:
        # Get the actual block from the repository
        block = await document_repository.get_block(block_id)
        if not block:
            raise HTTPException(status_code=404, detail="Block not found")
            
        # Analyze the block
        insight = await insight_service.analyze_block(block)
        if not insight:
            raise HTTPException(status_code=404, detail="No insight found for block")
        return insight
    except Exception as e:
        logger.error(f"Error getting block insight for {block_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/document/{document_id}", response_model=List[StructuredInsight])
async def get_document_insights(
    document_id: str,
    insight_service: StructuredInsightService = Depends(get_insight_service)
) -> List[StructuredInsight]:
    """Get all insights for a document"""
    try:
        insights = await insight_service.get_document_insights(document_id)
        logger.debug(f"Retrieved {len(insights)} insights for document {document_id}")
        return insights
    except Exception as e:
        logger.error(f"Error getting document insights for {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze", response_model=StructuredInsight)
async def analyze_block(
    request: AnalyzeBlockRequest,
    insight_service: StructuredInsightService = Depends(get_insight_service)
) -> StructuredInsight:
    """Analyze a block to generate insights"""
    try:
        from src.models.viewer.block import Block
        
        logger.debug(f"Analyzing block with data: {json.dumps({'block_id': request.block_id,'document_id': request.document_id,'page_number': request.page_number})}")
        
        if not request.document_id:
            logger.error("document_id is missing from request")
            raise HTTPException(status_code=400, detail="document_id is required")
            
        block = Block(
            id=request.block_id,
            document_id=request.document_id,
            block_type="text",
            html_content=request.block_content,
            page_number=request.page_number
        )
        
        logger.debug(f"Created Block object with document_id: {block.document_id}")
        
        insight = await insight_service.analyze_block(block)
        logger.debug(f"Generated insight with document_id: {getattr(insight, 'document_id', None)}")
        
        if not getattr(insight, 'document_id', None):
            logger.error("Generated insight is missing document_id")
            
        return insight
    except ValueError as e:
        logger.error(f"Validation error analyzing block {request.block_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error analyzing block {request.block_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) 