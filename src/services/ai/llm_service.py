from typing import List, Optional
from src.models.conversation.message import Message, MessageRole
from litellm import acompletion

class LLMService:
    CHAT_MODEL = "gpt-4o"  # Default model
    
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