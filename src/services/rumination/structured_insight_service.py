import json
from typing import List, Optional
from src.models.rumination.structured_insight import StructuredInsight
from src.models.conversation.message import Message, MessageRole

class StructuredInsightService:
    def __init__(self):
        self.cumulative_context = ""
        self.insights: List[StructuredInsight] = []

    def add_block_conversation(
        self, conversation_history: List[Message], block_id: str, page_number: Optional[int]
    ) -> StructuredInsight:
        # Assume the final assistant message is the final insight.
        final_insight = ""
        if conversation_history and conversation_history[-1].role == MessageRole.ASSISTANT:
            final_insight = conversation_history[-1].content
        
        structured_insight = StructuredInsight(
            block_id=block_id,
            page_number=page_number,
            insight=final_insight,
            conversation_history=[msg.dict() for msg in conversation_history]
        )
        self.insights.append(structured_insight)
        self._update_cumulative_context(conversation_history)
        return structured_insight

    def _update_cumulative_context(self, conversation_history: List[Message]) -> None:
        # Concatenate each message in the conversation.
        context_str = "\n".join([f"{msg.role}: {msg.content}" for msg in conversation_history])
        self.cumulative_context += context_str + "\n"

    def get_cumulative_context(self) -> str:
        return self.cumulative_context

    def get_all_insights(self) -> List[StructuredInsight]:
        return self.insights

    def save_insights_to_json(self, file_path: str) -> None:
        with open(file_path, "w") as f:
            json.dump([insight.dict() for insight in self.insights], f, indent=2)