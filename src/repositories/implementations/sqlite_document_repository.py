from typing import List, Optional, Dict, Any
import aiosqlite
import sqlite3
import json
import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from src.models.base.document import Document
from src.models.viewer.page import Page
from src.models.viewer.block import Block
from src.repositories.interfaces.document_repository import DocumentRepository

class SQLiteDocumentRepository(DocumentRepository):
    """SQLite implementation of DocumentRepository."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_db()
    
    def _ensure_db(self):
        """Create database and tables if they don't exist."""
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
            
        with sqlite3.connect(self.db_path) as db:
            # Documents table
            db.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    data TEXT NOT NULL
                )
            """)
            
            # Pages table
            db.execute("""
                CREATE TABLE IF NOT EXISTS pages (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    data TEXT NOT NULL,
                    FOREIGN KEY (document_id) REFERENCES documents(id)
                )
            """)
            
            # Blocks table
            db.execute("""
                CREATE TABLE IF NOT EXISTS blocks (
                    id TEXT PRIMARY KEY,
                    page_id TEXT NOT NULL,
                    data TEXT NOT NULL,
                    FOREIGN KEY (page_id) REFERENCES pages(id)
                )
            """)
            db.commit()
    
    async def store_document(self, document: Document, session: Optional[AsyncSession] = None) -> None:
        """Store a document in SQLite."""
        if session:
            await session.execute(
                text("INSERT OR REPLACE INTO documents (id, data) VALUES (:id, :data)"),
                {
                    "id": document.id,
                    "data": document.json()
                }
            )
            return
            
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO documents (id, data) VALUES (?, ?)",
                (document.id, document.json())
            )
            await db.commit()
    
    async def get_document(self, document_id: str, session: Optional[AsyncSession] = None) -> Optional[Document]:
        """Get a document by ID from SQLite."""
        if session:
            result = await session.execute(
                text("SELECT data FROM documents WHERE id = :id"),
                {"id": document_id}
            )
            row = result.fetchone()
            if row:
                return Document.parse_raw(row[0])
            return None
            
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT data FROM documents WHERE id = ?",
                (document_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return Document.parse_raw(row[0])
        return None
    
    async def store_pages(self, pages: List[Page], session: Optional[AsyncSession] = None) -> None:
        """Store pages in SQLite."""
        if session:
            for page in pages:
                await session.execute(
                    text("INSERT OR REPLACE INTO pages (id, document_id, data) VALUES (:id, :document_id, :data)"),
                    {
                        "id": page.id,
                        "document_id": page.document_id,
                        "data": page.json()
                    }
                )
            return
            
        async with aiosqlite.connect(self.db_path) as db:
            for page in pages:
                await db.execute(
                    "INSERT OR REPLACE INTO pages (id, document_id, data) VALUES (?, ?, ?)",
                    (page.id, page.document_id, page.json())
                )
            await db.commit()
    
    async def get_document_pages(self, document_id: str, session: Optional[AsyncSession] = None) -> List[Page]:
        """Get all pages for a document from SQLite."""
        if session:
            result = await session.execute(
                text("SELECT data FROM pages WHERE document_id = :document_id"),
                {"document_id": document_id}
            )
            return [Page.parse_raw(row[0]) for row in result]
            
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT data FROM pages WHERE document_id = ?",
                (document_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [Page.parse_raw(row[0]) for row in rows]
    
    async def store_blocks(self, blocks: List[Block], session: Optional[AsyncSession] = None) -> None:
        """Store blocks in SQLite."""
        if session:
            for block in blocks:
                await session.execute(
                    text("INSERT OR REPLACE INTO blocks (id, page_id, data) VALUES (:id, :page_id, :data)"),
                    {
                        "id": block.id,
                        "page_id": block.page_id,
                        "data": block.json()
                    }
                )
            return
            
        async with aiosqlite.connect(self.db_path) as db:
            for block in blocks:
                await db.execute(
                    "INSERT OR REPLACE INTO blocks (id, page_id, data) VALUES (?, ?, ?)",
                    (block.id, block.page_id, block.json())
                )
            await db.commit()
    
    async def get_page_blocks(self, page_id: str, session: Optional[AsyncSession] = None) -> List[Block]:
        """Get all blocks for a page from SQLite."""
        if session:
            result = await session.execute(
                text("SELECT data FROM blocks WHERE page_id = :page_id"),
                {"page_id": page_id}
            )
            return [Block.parse_raw(row[0]) for row in result]
            
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT data FROM blocks WHERE page_id = ?",
                (page_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [Block.parse_raw(row[0]) for row in rows]
    
    async def get_pages(self, document_id: str, session: Optional[AsyncSession] = None) -> List[Page]:
        """Get all pages for a document"""
        if session:
            result = await session.execute(
                text("SELECT data FROM pages WHERE document_id = :document_id"),
                {"document_id": document_id}
            )
            return [Page.parse_raw(row[0]) for row in result]
            
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT data FROM pages WHERE document_id = ?",
                (document_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [Page.parse_raw(row[0]) for row in rows]
    
    async def get_blocks(self, document_id: str, session: Optional[AsyncSession] = None) -> List[Block]:
        """Get all blocks for a document"""
        if session:
            result = await session.execute(
                text("""
                    SELECT b.data, p.data as page_data
                    FROM blocks b 
                    JOIN pages p ON b.page_id = p.id 
                    WHERE p.document_id = :document_id
                """),
                {"document_id": document_id}
            )
            blocks = []
            for row in result:
                block = Block.parse_raw(row[0])
                page = Page.parse_raw(row[1])
                block.page_number = page.page_number
                blocks.append(block)
            return blocks
            
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                """
                SELECT b.data, p.data as page_data
                FROM blocks b 
                JOIN pages p ON b.page_id = p.id 
                WHERE p.document_id = ?
                """,
                (document_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                blocks = []
                for row in rows:
                    block = Block.parse_raw(row[0])
                    page = Page.parse_raw(row[1])
                    block.page_number = page.page_number
                    blocks.append(block)
                return blocks
    
    async def get_block(self, block_id: str, session: Optional[AsyncSession] = None) -> Optional[Block]:
        """Get a block by ID from SQLite"""
        if session:
            result = await session.execute(
                text("SELECT data FROM blocks WHERE id = :id"),
                {"id": block_id}
            )
            row = result.fetchone()
            if row:
                return Block.parse_raw(row[0])
            return None
            
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT data FROM blocks WHERE id = ?",
                (block_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return Block.parse_raw(row[0])
        return None
