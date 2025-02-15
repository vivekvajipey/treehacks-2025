from functools import lru_cache
from typing import Optional
from fastapi import Depends
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer

Base = declarative_base()

from src.repositories.factory import RepositoryFactory
from src.repositories.interfaces.document_repository import DocumentRepository
from src.repositories.interfaces.storage_repository import StorageRepository
from src.repositories.interfaces.conversation_repository import ConversationRepository
from src.services.document.upload_service import UploadService
from src.services.document.marker_service import MarkerService
from src.services.conversation.chat_service import ChatService
from src.services.ai.llm_service import LLMService
from src.config import get_settings, Settings

# Global instances
repository_factory = RepositoryFactory()
db_session_factory = None

async def initialize_repositories():
    """Called on app startup to initialize repositories"""
    global db_session_factory
    
    settings = get_settings()
    
    # Initialize session factory if using a database
    if settings.document_storage_type in ["rds", "sqlite"]:
        if settings.document_storage_type == "rds":
            url = f"postgresql+asyncpg://{settings.db_user}:{settings.db_password}@{settings.db_host}:{settings.db_port}/db"
        else:  # sqlite
            url = f"sqlite+aiosqlite:///{settings.db_path}"
            
        engine = create_async_engine(url)
        db_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        # Create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    repository_factory.init_repositories(
        document_type=settings.document_storage_type,
        storage_type=settings.file_storage_type,
        data_dir=settings.data_dir,
        storage_dir=settings.storage_dir,
        db_path=settings.db_path,
        db_host=settings.db_host,
        db_port=settings.db_port,
        db_user=settings.db_user,
        db_password=settings.db_password,
        aws_access_key=settings.aws_access_key,
        aws_secret_key=settings.aws_secret_key,
        s3_bucket=settings.s3_bucket
    )

async def get_db() -> Optional[AsyncSession]:
    """Get database session if needed"""
    if db_session_factory is None:
        yield None
        return
        
    session = db_session_factory()
    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        raise e
    finally:
        await session.close()

def get_document_repository() -> DocumentRepository:
    """Dependency for document repository"""
    return repository_factory.document_repository

def get_storage_repository() -> StorageRepository:
    """Dependency for storage repository"""
    return repository_factory.storage_repository

def get_conversation_repository() -> ConversationRepository:
    """Dependency for conversation repository"""
    return repository_factory.conversation_repository

def get_marker_service() -> MarkerService:
    """Dependency for marker service"""
    settings = get_settings()
    return MarkerService(api_key=settings.datalab_api_key)

def get_llm_service() -> LLMService:
    """Dependency for LLM service"""
    settings = get_settings()
    return LLMService(api_key=settings.openai_api_key)

def get_upload_service(
    document_repository: DocumentRepository = Depends(get_document_repository),
    storage_repository: StorageRepository = Depends(get_storage_repository),
    marker_service: MarkerService = Depends(get_marker_service)
) -> UploadService:
    """Dependency for upload service that composes other dependencies"""
    return UploadService(
        document_repository=document_repository,
        storage_repository=storage_repository,
        marker_service=marker_service
    )

def get_chat_service(
    conversation_repository: ConversationRepository = Depends(get_conversation_repository),
    document_repository: DocumentRepository = Depends(get_document_repository),
    llm_service: LLMService = Depends(get_llm_service)
) -> ChatService:
    """Dependency for chat service"""
    return ChatService(conversation_repository, document_repository, llm_service)