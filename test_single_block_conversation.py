import asyncio
import os
import yaml
import re
from dotenv import load_dotenv

from src.services.ai.llm_service import LLMService
from src.models.conversation.message import Message, MessageRole

# Simple HTML stripping utility (or import from your context service)
def strip_html(html: str) -> str:
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

    system_prompt = prompts.get("system", "You are a document reader agent.")
    initial_analysis_prompt = prompts.get("initial_analysis", "Analyze the following block:")
    follow_up_prompt = prompts.get("follow_up", "Please provide further detail.")

    # Create a dummy block (simulate a block extracted from a document)
    dummy_block = {
        "id": "test-block-1",
        "page_number": 1,
        "block_type": "Text",
        "html_content": "<p>This is a test block containing important details about the document's main theme. The text discusses key advancements in AI and their implications.</p>"
    }

    # Extract plain text from the block
    block_text = strip_html(dummy_block["html_content"]).strip()

    # Generate a unique conversation ID
    conversation_id = "unique-conversation-id"  # Replace with actual logic to generate or retrieve an ID

    # Build the initial conversation history
    conversation_history = []
    conversation_history.append(Message(conversation_id=conversation_id, role=MessageRole.SYSTEM, content=system_prompt))

    user_message = (
        f"{initial_analysis_prompt}\n"
        f"[Block ID: {dummy_block['id']}, Page: {dummy_block['page_number']}]\n"
        f"{block_text}"
    )
    conversation_history.append(Message(conversation_id=conversation_id, role=MessageRole.USER, content=user_message))

    # Initialize the LLM service (ensure your API key is set in the environment, e.g., LLM_API_KEY)
    api_key = os.getenv("OPENAI_API_KEY")
    llm_service = LLMService(api_key=api_key)

    # Turn 1: Get the initial analysis
    response1 = await llm_service.generate_response(conversation_history)
    conversation_history.append(Message(conversation_id=conversation_id, role=MessageRole.ASSISTANT, content=response1))

    # Turn 2: Follow-up question
    conversation_history.append(Message(conversation_id=conversation_id, role=MessageRole.USER, content=follow_up_prompt))
    response2 = await llm_service.generate_response(conversation_history)
    conversation_history.append(Message(conversation_id=conversation_id, role=MessageRole.ASSISTANT, content=response2))

    final_insight = response2

    # Build cumulative context (a simple concatenation of the conversation)
    cumulative_context = "\n".join([f"{msg.role}: {msg.content}" for msg in conversation_history])

    print("Final Insight from Block Conversation:\n")
    print(final_insight)
    print("\nCumulative Conversation Context:\n")
    print(cumulative_context)

if __name__ == "__main__":
    asyncio.run(main())
