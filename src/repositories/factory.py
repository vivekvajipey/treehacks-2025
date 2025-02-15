# repositories/factory.py
from enum import Enum
from typing import Optional
from .interfaces.document_repository import DocumentRepository
from .interfaces.storage_repository import StorageRepository
from .interfaces.conversation_repository import ConversationRepository

class StorageType(Enum):
    LOCAL = "local"
    SQLITE = "sqlite"
    S3 = "s3"
    RDS = "rds"

class RepositoryFactory:
    def __init__(self):
        self._document_repo: Optional[DocumentRepository] = None
        self._storage_repo: Optional[StorageRepository] = None
        self._conversation_repo: Optional[ConversationRepository] = None
        
    def init_repositories(
        self,
        document_type: str = "local",
        storage_type: str = "local",
        **kwargs  # For connection strings, credentials etc
    ):
        """Initialize repositories based on type.
        """
        if document_type == "local":
            from .implementations.json_document_repository import JSONDocumentRepository
            from .implementations.json_conversation_repository import JSONConversationRepository
            self._document_repo = JSONDocumentRepository(data_dir=kwargs.get('data_dir', 'local_db'))
            self._conversation_repo = JSONConversationRepository(data_dir=kwargs.get('data_dir', 'local_db'))
        elif document_type == "sqlite":
            from .implementations.sqlite_document_repository import SQLiteDocumentRepository
            from .implementations.sqlite_conversation_repository import SQLiteConversationRepository
            db_path = kwargs.get('db_path', 'sqlite.db')
            self._document_repo = SQLiteDocumentRepository(db_path=db_path)
            self._conversation_repo = SQLiteConversationRepository(db_path=db_path)
        elif document_type == "rds":
            from .implementations.rds_document_repository import RDSDocumentRepository
            raise NotImplementedError("RDS implementation pending")
            # from .implementations.rds_conversation_repository import RDSConversationRepository
            # self._document_repo = RDSDocumentRepository()
            # )
            # self._conversation_repo = RDSConversationRepository()
            # )

        if storage_type == "local":
            from .implementations.local_storage_repository import LocalStorageRepository
            self._storage_repo = LocalStorageRepository(storage_dir=kwargs.get('storage_dir', 'local_storage'))
        elif storage_type == "s3":
            from .implementations.s3_storage_repository import S3StorageRepository
            self._storage_repo = S3StorageRepository(
                bucket=kwargs.get('bucket'),
                aws_access_key=kwargs.get('aws_access_key'),
                aws_secret_key=kwargs.get('aws_secret_key')
            )

    @property
    def document_repository(self) -> DocumentRepository:
        if not self._document_repo:
            raise RuntimeError("Repository not initialized. Call init_repositories first.")
        return self._document_repo

    @property
    def storage_repository(self) -> StorageRepository:
        if not self._storage_repo:
            raise RuntimeError("Repository not initialized. Call init_repositories first.")
        return self._storage_repo

    @property
    def conversation_repository(self) -> ConversationRepository:
        """Get conversation repository instance"""
        if not self._conversation_repo:
            raise RuntimeError("Conversation repository not initialized")
        return self._conversation_repo