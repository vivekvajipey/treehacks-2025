from abc import ABC, abstractmethod
from typing import List, Optional, TypeVar
from src.models.base.document import Document
from src.models.viewer.page import Page
from src.models.viewer.block import Block

DBSession = TypeVar('DBSession')

class DocumentRepository(ABC):
    @abstractmethod
    async def store_document(self, document: Document, session: Optional[DBSession] = None) -> None:
        pass
        
    @abstractmethod
    async def get_document(self, document_id: str, session: Optional[DBSession] = None) -> Optional[Document]:
        """Get a document by ID"""
        pass
    
    @abstractmethod
    async def store_pages(self, pages: List[Page], session: Optional[DBSession] = None) -> None:
        pass
    
    @abstractmethod
    async def get_document_pages(self, document_id: str, session: Optional[DBSession] = None) -> List[Page]:
        pass
    
    @abstractmethod
    async def store_blocks(self, blocks: List[Block], session: Optional[DBSession] = None) -> None:
        pass
    
    @abstractmethod
    async def get_page_blocks(self, page_id: str, session: Optional[DBSession] = None) -> List[Block]:
        pass

    @abstractmethod
    async def get_blocks(self, document_id: str, session: Optional[DBSession] = None) -> List[Block]:
        pass
    
    @abstractmethod
    async def get_block(self, block_id: str, session: Optional[DBSession] = None) -> Optional[Block]:
        """Get a block by ID"""
        pass