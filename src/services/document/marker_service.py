from typing import Dict, Any, Tuple, List
import requests
import asyncio
import os
from uuid import uuid4
from datetime import datetime
from fastapi import HTTPException
from src.models.viewer.block import Block, BlockType
from src.models.viewer.page import Page
from src.models.base.document import Document

class MarkerService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.marker_url = "https://www.datalab.to/api/v1/marker"
        self.max_polls = 300  # 10 minutes
        self.poll_interval = 2  # seconds
        
        if not self.api_key:
            raise ValueError("API key not provided")

    async def process_document(self, file_data: bytes) -> Tuple[List[Page], List[Block]]:
        """Full document processing through Marker"""
        try:
            check_url = await self._initiate_processing(file_data)
            marker_response = await self._poll_until_complete(check_url)
            return self._create_pages_and_blocks(marker_response)
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def _initiate_processing(self, file_data: bytes) -> str:
        """Start Marker processing, return check_url"""
        form_data = {
            'file': ('document.pdf', file_data, 'application/pdf'),
            'langs': (None, "English"),
            'output_format': (None, 'json'),
            "paginate": (None, True),
            "force_ocr": (None, False),
            "use_llm": (None, False),
            "strip_existing_ocr": (None, False),
            "disable_image_extraction": (None, False)
        }
        
        headers = {"X-Api-Key": self.api_key}
        response = requests.post(self.marker_url, files=form_data, headers=headers)
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, 
                              detail=f"Marker API request failed: {response.text}")
        
        data = response.json()
        if not data.get('success'):
            raise HTTPException(status_code=400, 
                              detail=f"Marker API request failed: {data.get('error')}")
            
        return data["request_check_url"]

    async def _poll_until_complete(self, check_url: str) -> Dict[str, Any]:
        """Poll check_url until processing is complete"""
        headers = {"X-Api-Key": self.api_key}
        
        for _ in range(self.max_polls):
            await asyncio.sleep(self.poll_interval)
            response = requests.get(check_url, headers=headers)
            data = response.json()
            
            if data["status"] == "complete":
                if not data["success"]:
                    raise HTTPException(status_code=400, 
                                      detail=f"Processing failed: {data.get('error')}")
                return data.get('json', {})
                
        raise HTTPException(status_code=408, detail="Processing timeout")

    def _create_pages_and_blocks(self, marker_response: Dict[str, Any]) -> Tuple[List[Page], List[Block]]:
        """Create Page and Block objects from Marker response"""
        pages = []
        blocks = []
        
        # Process each page in the response
        for page_idx, page_data in enumerate(marker_response.get('children', [])):
            if page_data.get('block_type') != 'Page':  # Only process Page blocks
                continue
                
            # Create the page
            page = Page(
                page_number=page_idx,
                polygon=page_data.get('polygon'),
                html_content=page_data.get('html', ""),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            pages.append(page)
            
            # Process blocks in this page
            page_blocks = self._process_blocks(page_data.get('children', []), page.id)
            blocks.extend(page_blocks)
            
            # Add block IDs to page
            for block in page_blocks:
                page.add_block(block.id)
        
        return pages, blocks
    
    def _process_blocks(self, block_list: List[Dict], page_id: str) -> List[Block]:
        """Recursively process blocks and their children"""
        blocks = []
        for block_data in block_list:
            # Create block
            block = Block.from_marker_block(block_data, None, page_id)
            blocks.append(block)
            
            # Process children recursively
            if block_data.get('children'):
                child_blocks = self._process_blocks(block_data['children'], page_id)
                blocks.extend(child_blocks)
        
        return blocks