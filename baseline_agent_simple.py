# baseline_agent_simple.py
import asyncio
import os
import yaml
import re
from dotenv import load_dotenv

from src.services.ai.llm_service import LLMService
from src.models.conversation.message import Message, MessageRole

def strip_html(html: str) -> str:
    import re
    return re.sub(r'<[^>]+>', '', html)

load_dotenv()

async def main():
    # Load a simple prompt from a separate YAML file or inline configuration
    prompt_path = os.path.join("prompts", "baseline_prompt.yml")
    if os.path.exists(prompt_path):
        with open(prompt_path, "r") as f:
            prompts = yaml.safe_load(f)
        simple_prompt = prompts.get("simple_prompt", "Provide a concise analysis of the following text block:")
    else:
        simple_prompt = "Provide a concise analysis of the following text block:"

    # Use the same deep block as before for a fair comparison
    with open("text/deep_block_1.html", "r") as f:
        deep_block_html = f.read()
    deep_block = {
        "id": "deep-block-1",
        "page_number": 3,
        "block_type": "Text",
        "html_content": deep_block_html
    }

    block_text = strip_html(deep_block["html_content"]).strip()

    # Use a fixed conversation id
    conversation_id = "baseline-conversation-1"

    # Build a simple conversation history: only system prompt and single user prompt
    conversation_history = []
    system_message = "You are a document reader agent whose task is to deeply understand each block of the document. Your responses should be concise and insightful."
    conversation_history.append(Message(conversation_id=conversation_id, role=MessageRole.SYSTEM, content=system_message))

    user_message = f"{simple_prompt}\n[Block ID: {deep_block['id']}, Page: {deep_block['page_number']}]\n{block_text}"
    conversation_history.append(Message(conversation_id=conversation_id, role=MessageRole.USER, content=user_message))

    api_key = os.getenv("OPENAI_API_KEY")
    llm_service = LLMService(api_key=api_key)

    response = await llm_service.generate_response(conversation_history)
    conversation_history.append(Message(conversation_id=conversation_id, role=MessageRole.ASSISTANT, content=response))

    cumulative_context = "\n".join([f"{msg.role}: {msg.content}" for msg in conversation_history])

    print("Baseline Simple Agent Insight:\n")
    print(response)
    print("\nCumulative Conversation Context:\n")
    print(cumulative_context)

if __name__ == "__main__":
    asyncio.run(main())
