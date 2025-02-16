import json
import yaml
import re
import os
import logging
from typing import List 

from src.models.rumination.structured_insight import StructuredInsight, Annotation
from src.models.conversation.message import Message, MessageRole
from src.services.ai.llm_service import LLMService
from src.repositories.interfaces.insight_repository import InsightRepository

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class StructuredInsightService:
    def __init__(self, 
                 llm_service: LLMService,
                 insight_repository: InsightRepository):
        # Store the cumulative conversation as a list of Message objects.
        self.cumulative_messages: List[Message] = []
        self.llm_service = llm_service
        self.insight_repository = insight_repository
        
        # Get the absolute path to the config directory
        config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "config")
        
        # Load prompts from YAML.
        with open(os.path.join(config_dir, "prompt.yml"), "r") as f:
            self.prompts = yaml.safe_load(f)

        with open(os.path.join(config_dir, "rumination_config.yml"), "r") as f:
            self.rumination_config = yaml.safe_load(f)
        
        self.objective = self.rumination_config.get("objective", "Focus on extracting the key themes and details of the document.")

        # Inject objective into prompts
        for key in self.prompts:
            if isinstance(self.prompts[key], str):
                self.prompts[key] = self.prompts[key].replace("{OBJECTIVE}", self.objective)

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
        Process a block by generating an overall insight and extracting annotations.
        First checks if an insight exists, if not generates a new one.
        """
        logger.debug(f"Starting analyze_block for block_id: {block.id}, document_id: {block.document_id}")
        
        # Check if insight already exists
        existing_insight = await self.insight_repository.get_block_insight(block.id)
        if existing_insight:
            logger.debug(f"Found existing insight with document_id: {existing_insight.document_id}")
            return existing_insight

        # Generate new insight
        conversation_id = f"conv-{block.id}"
        block_text = block.html_content or ""
        plain_text = re.sub(r'<[^>]+>', '', block_text).strip()

        # Build messages specific to this block.
        block_messages = []
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

        overall_insight = response1

        # Update cumulative messages with the new messages for this block.
        self._update_cumulative_messages(block_messages)

        # Extract annotations based on the plain text and overall insight.
        annotations = await self.extract_annotations(plain_text)

        try:
            structured_insight = StructuredInsight(
                block_id=block.id,
                document_id=block.document_id,
                page_number=block.page_number,
                insight=overall_insight,
                annotations=annotations,
                conversation_history=[{"id": msg.id, "role": msg.role, "content": msg.content} 
                                    for msg in self.get_cumulative_messages()]
            )
            logger.debug(f"Created StructuredInsight with document_id: {structured_insight.document_id}")
        except Exception as e:
            logger.error(f"Error creating StructuredInsight: {str(e)}", exc_info=True)
            logger.error(f"Block data: {json.dumps({'block_id': block.id, 'document_id': block.document_id,'page_number': block.page_number})}")
            raise

        # Store the insight
        try:
            await self.insight_repository.create_insight(structured_insight)
            logger.debug("Successfully stored insight in repository")
        except Exception as e:
            logger.error(f"Error storing insight: {str(e)}", exc_info=True)
            raise

        return structured_insight

    async def get_document_insights(self, document_id: str) -> List[StructuredInsight]:
        """Get all insights for a document from the repository"""
        return await self.insight_repository.get_document_insights(document_id)

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
