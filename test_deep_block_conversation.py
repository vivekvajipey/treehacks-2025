# test_deep_block_conversation.py
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
    # Load prompts from prompt.yml (adjust the path if needed)
    prompt_path = os.path.join("prompts", "prompt.yml")
    if not os.path.exists(prompt_path):
        print(f"Prompt file not found at {prompt_path}. Please add prompt.yml.")
        return

    with open(prompt_path, "r") as f:
        prompts = yaml.safe_load(f)

    system_prompt = prompts.get("system")
    initial_analysis_prompt = prompts.get("initial_analysis")
    follow_up_prompt = prompts.get("follow_up")

    # Use a deeper text that would benefit from deep reading.
    with open("text/grpo.txt", "r") as f:
        deep_block_html = f.read()
    deep_block = {
        "id": "grpo-block-1",
        "page_number": 3,
        "block_type": "Text",
        "html_content": deep_block_html
    }

    block_text = strip_html(deep_block["html_content"]).strip()

    # Generate a unique conversation ID (could be a UUID in a full implementation)
    conversation_id = "deep-conversation-1"

    # Build conversation history with our system prompt and initial analysis prompt
    conversation_history = []
    conversation_history.append(Message(conversation_id=conversation_id, role=MessageRole.SYSTEM, content=system_prompt))

    user_message = (
        f"{initial_analysis_prompt}\n"
        f"[Block ID: {deep_block['id']}, Page: {deep_block['page_number']}]\n"
        f"{block_text}"
    )
    conversation_history.append(Message(conversation_id=conversation_id, role=MessageRole.USER, content=user_message))

    # Initialize LLM service (ensure OPENAI_API_KEY is set in environment)
    api_key = os.getenv("OPENAI_API_KEY")
    llm_service = LLMService(api_key=api_key)

    # Turn 1: Initial analysis
    response1 = await llm_service.generate_response(conversation_history)
    conversation_history.append(Message(conversation_id=conversation_id, role=MessageRole.ASSISTANT, content=response1))

    # Turn 2: Follow-up question
    conversation_history.append(Message(conversation_id=conversation_id, role=MessageRole.USER, content=follow_up_prompt))
    response2 = await llm_service.generate_response(conversation_history)
    conversation_history.append(Message(conversation_id=conversation_id, role=MessageRole.ASSISTANT, content=response2))

    final_insight = response2

    cumulative_context = "\n".join([f"{msg.role}: {msg.content}" for msg in conversation_history])

    print("Final Insight from Deep Block Conversation:\n")
    print(final_insight)
    print("\nCumulative Conversation Context:\n")
    print(cumulative_context)

if __name__ == "__main__":
    asyncio.run(main())
