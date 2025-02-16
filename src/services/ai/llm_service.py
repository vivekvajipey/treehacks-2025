# llm_service.py

from typing import List, Optional, Dict, Any
from src.models.conversation.message import Message, MessageRole
from litellm import acompletion
import json

class LLMService:
    CHAT_MODEL = "gpt-4o-mini"  # Default model
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        
    async def generate_response(self, messages: List[Message]) -> str:
        """Generate LLM response for the given messages
        
        Args:
            messages: List of messages in the conversation thread
            
        Returns:
            Generated response text
        """
        # Convert our Message objects to the format expected by litellm
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                "role": msg.role,  # MessageRole enum is already a string
                "content": msg.content
            })
            
        completion = await acompletion(
            model=self.CHAT_MODEL,
            messages=formatted_messages,
            api_key=self.api_key,
            stream=False  # Don't stream responses for now
        )
        return completion.choices[0].message.content

    async def generate_structured_response(
        self, 
        messages: List[Message], 
        response_format: Dict[str, str],
        json_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate LLM response in a structured JSON format according to the provided schema
        
        Args:
            messages: List of messages in the conversation thread
            response_format: Format specification for the response (e.g., {"type": "json_object"})
            json_schema: JSON schema that defines the structure of the expected response
            
        Returns:
            Structured response as a dictionary matching the provided schema
        """
        # Convert our Message objects to the format expected by litellm
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                "role": msg.role,
                "content": msg.content
            })
            
        completion = await acompletion(
            model=self.CHAT_MODEL,
            messages=formatted_messages,
            api_key=self.api_key,
            response_format=response_format,
            tools=[{
                "type": "function",
                "function": {
                    "name": "output_structure",
                    "description": "Structure the output according to the schema",
                    "parameters": json_schema
                }
            }],
            tool_choice={"type": "function", "function": {"name": "output_structure"}},
            stream=False
        )
        
        # Extract and parse the JSON response from the function call
        function_call = completion.choices[0].message.tool_calls[0]
        return json.loads(function_call.function.arguments)