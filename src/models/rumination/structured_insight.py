# src/models/rumination/structured_insight.py

from pydantic import BaseModel
from typing import List, Optional

class StructuredInsight(BaseModel):
    block_id: str
    page_number: Optional[int] = None
    insight: str
    conversation_history: List[dict]