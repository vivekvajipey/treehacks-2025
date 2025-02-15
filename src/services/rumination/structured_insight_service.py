import json
from typing import List, Optional
from src.models.rumination.structured_insight import StructuredInsight
from src.models.conversation.message import Message, MessageRole

class StructuredInsightService:
    def __init__(self):
        # Instead of a string, we'll store the cumulative conversation as a list of Message objects.
        self.cumulative_messages: List[Message] = []
        self.insights: List[StructuredInsight] = []

    def add_block_conversation(
        self, conversation_history: List[Message], block_id: str, page_number: Optional[int]
    ) -> StructuredInsight:
        # Assume that the final assistant message is our final insight.
        final_insight = ""
        if conversation_history and conversation_history[-1].role == MessageRole.ASSISTANT:
            final_insight = conversation_history[-1].content

        structured_insight = StructuredInsight(
            block_id=block_id,
            page_number=page_number,
            insight=final_insight,
            conversation_history=[{
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
            } for msg in conversation_history]
        )
        self.insights.append(structured_insight)
        self._update_cumulative_messages(conversation_history)
        return structured_insight

    def _update_cumulative_messages(self, conversation_history: List[Message]) -> None:
        """
        Update the cumulative messages list with the messages from the current block conversation.
        By preserving the prefix (static messages like system instructions) and appending new interactions,
        subsequent API calls will benefit from prompt caching.
        """
        # Extend the cumulative messages with the new conversation.
        self.cumulative_messages.extend(conversation_history)

    def get_cumulative_messages(self) -> List[Message]:
        return self.cumulative_messages

    def get_all_insights(self) -> List[StructuredInsight]:
        return self.insights

    def save_insights_to_json(self, file_path: str) -> None:
        with open(file_path, "w") as f:
            json.dump([insight.dict() for insight in self.insights], f, indent=2)
