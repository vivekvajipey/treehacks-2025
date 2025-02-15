from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.document.upload_service import UploadService
from src.api.dependencies import get_upload_service, get_document_repository, get_db
from src.repositories.interfaces.document_repository import DocumentRepository
from src.models.viewer.block import Block
from src.models.base.document import Document

document_router = APIRouter(prefix="/documents")

@document_router.post("/")
async def upload_document(
    file: UploadFile = File(...),
    upload_service: UploadService = Depends(get_upload_service),
    session: Optional[AsyncSession] = Depends(get_db)
) -> Document:
    """Upload a new document"""
    # For testing purposes, using a fixed user_id
    doc = await upload_service.upload(file, session, user_id="test_user")
    return doc

@document_router.get("/{document_id}")
async def get_document(
    document_id: str,
    document_repository: DocumentRepository = Depends(get_document_repository),
    session: Optional[AsyncSession] = Depends(get_db)
) -> Document:
    """Get a document by ID"""
    doc = await document_repository.get_document(document_id, session=session)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

@document_router.get("/{document_id}/pages")
async def get_pages(
    document_id: str,
    document_repository: DocumentRepository = Depends(get_document_repository),
    session: Optional[AsyncSession] = Depends(get_db)
):
    """Get all pages for a document"""
    pages = await document_repository.get_document_pages(document_id, session=session)
    if not pages:
        raise HTTPException(status_code=404, detail="Pages not found")
    return pages

@document_router.get("/{document_id}/blocks")
async def get_blocks(
    document_id: str,
    document_repository: DocumentRepository = Depends(get_document_repository),
    session: Optional[AsyncSession] = Depends(get_db)
) -> List[Block]:
    """Get all blocks for a document"""
    blocks = await document_repository.get_blocks(document_id, session)
    if not blocks:
        raise HTTPException(status_code=404, detail="Blocks not found")
    return blocks