import json
import yaml
import re
from typing import List, Optional
from datetime import datetime

from src.models.rumination.structured_insight import StructuredInsight, Annotation
from src.models.conversation.message import Message, MessageRole
from src.services.ai.llm_service import LLMService

class StructuredInsightService:
    def __init__(self):
        # Store the cumulative conversation as a list of Message objects.
        self.cumulative_messages: List[Message] = []
        self.insights: List[StructuredInsight] = []
        self.llm_service = LLMService()
        
        # Load prompts from YAML.
        with open("prompts/prompt.yml", "r") as f:
            self.prompts = yaml.safe_load(f)

    async def extract_annotations(self, block_text: str) -> List[Annotation]:
        json_schema = {
            "type": "object",
            "properties": {
                "annotations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "phrase": {
                                "type": "string",
                                "description": "An exact substring from the block text that is significant."
                            },
                            "insight": {
                                "type": "string",
                                "description": "A concise explanation (1-2 sentences) of the phrase's significance."
                            }
                        },
                        "required": ["phrase", "insight"]
                    },
                    "minItems": 1,
                    "maxItems": 4
                }
            },
            "required": ["annotations"]
        }

        annotation_prompt = self.prompts.get("annotation_extraction")
        # Updated content now includes a reference to "json"
        annotation_message = Message(
            conversation_id="global",  # Using the global conversation ID for annotation extraction.
            role=MessageRole.USER,
            content=f"{annotation_prompt}\n\nBlock Text:\n{block_text}\n\nPlease format your response as a valid json object."
        )

        messages = self.cumulative_messages + [annotation_message]

        try:
            response = await self.llm_service.generate_structured_response(
                messages=messages,
                response_format={"type": "json_object"},
                json_schema=json_schema
            )
            annotations_data = response.get("annotations", [])
            self._update_cumulative_messages([annotation_message])
            return [Annotation(**annotation) for annotation in annotations_data]
        except Exception as e:
            print(f"Error extracting annotations: {e}")
            return []

    async def analyze_block(self, block) -> StructuredInsight:
        """
        Process a block by generating an overall insight and extracting annotations,
        using a growing conversation context.
        
        Args:
            block: A Block object containing text and metadata.
            
        Returns:
            A StructuredInsight object with overall insight, annotations, and conversation history.
        """
        conversation_id = f"conv-{block.id}"
        block_text = block.html_content or ""
        plain_text = re.sub(r'<[^>]+>', '', block_text).strip()

        # Build messages specific to this block.
        block_messages = []
        # Instead of adding a new system message, we assume the system prompt is already in cumulative_messages.
        initial_message = (
            f"{self.prompts['initial_analysis']}\n"
            f"[Block ID: {block.id}, Page: {block.page_number}]\n"
            f"{plain_text}"
        )
        block_messages.append(Message(conversation_id=conversation_id, role=MessageRole.USER, content=initial_message))

        # Create full context: cumulative messages so far + new block messages.
        full_context = self.get_cumulative_messages() + block_messages
        response1 = await self.llm_service.generate_response(full_context)
        block_messages.append(Message(conversation_id=conversation_id, role=MessageRole.ASSISTANT, content=response1))

        # block_messages.append(Message(conversation_id=conversation_id, role=MessageRole.USER, content=self.prompts['follow_up']))
        # full_context = self.get_cumulative_messages() + block_messages
        # response2 = await self.llm_service.generate_response(full_context)
        # block_messages.append(Message(conversation_id=conversation_id, role=MessageRole.ASSISTANT, content=response2))

        overall_insight = response1 # temporary

        # Update cumulative messages with the new messages for this block.
        self._update_cumulative_messages(block_messages)

        # Extract annotations based on the plain text and overall insight.
        annotations = await self.extract_annotations(plain_text)

        structured_insight = StructuredInsight(
            block_id=block.id,
            page_number=block.page_number,
            insight=overall_insight,
            annotations=annotations,
            conversation_history=[{"id": msg.id, "role": msg.role, "content": msg.content} 
                                  for msg in self.get_cumulative_messages()]
        )
        self.insights.append(structured_insight)
        return structured_insight

    def _update_cumulative_messages(self, conversation_history: List[Message]) -> None:
        """
        Append new messages to the cumulative conversation context.
        """
        self.cumulative_messages.extend(conversation_history)

    def get_cumulative_messages(self) -> List[Message]:
        return self.cumulative_messages

    def get_all_insights(self) -> List[StructuredInsight]:
        return self.insights

    def save_insights_to_json(self, file_path: str) -> None:
        with open(file_path, "w") as f:
            json.dump([insight.dict() for insight in self.insights], f, indent=2)
