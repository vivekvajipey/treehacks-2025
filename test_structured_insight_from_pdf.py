import asyncio
import os
import json
import hashlib
import re
from datetime import datetime
from dotenv import load_dotenv
import yaml

from src.services.document.marker_service import MarkerService
from build_context_from_blocks import build_context_from_blocks
from src.services.rumination.structured_insight_service import StructuredInsightService
from src.models.conversation.message import Message, MessageRole
from src.services.ai.llm_service import LLMService
from src.models.viewer.block import Block

load_dotenv()

verbose = True
# pdf_name = "aime"
pdf_name = "deepseek_introduction"

def compute_hash(file_data: bytes) -> str:
    """Compute SHA-256 hash of file data."""
    return hashlib.sha256(file_data).hexdigest()

def generate_unique_filename(pdf_hash: str) -> str:
    """Generate a unique filename using the pdf hash and current timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"insights_{pdf_hash[:8]}_{timestamp}.json"

async def main():
    # Path to your sample PDF file in the 'pdf' directory
    pdf_path = os.path.join("pdf", f"{pdf_name}.pdf")
    if not os.path.exists(pdf_path):
        print(f"PDF file not found at {pdf_path}. Please add a sample PDF to the 'pdf' directory.")
        return

    # Read the PDF file as bytes and compute its hash
    with open(pdf_path, "rb") as f:
        file_data = f.read()
    pdf_hash = compute_hash(file_data)

    # Setup cache directory and file path
    cache_dir = "cache"
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, f"{pdf_hash}.json")

    # Load cached Marker API result if available; otherwise, call Marker API.
    if os.path.exists(cache_path):
        print("Loading cached Marker API response...")
        with open(cache_path, "r") as f:
            cache_data = json.load(f)
        # Reconstruct pages and blocks from cache
        pages = cache_data.get("pages", [])
        blocks_data = cache_data.get("blocks", [])
        blocks = [Block.from_dict(bd) for bd in blocks_data]
    else:
        print("Processing PDF with Marker API...")
        api_key = os.getenv("DATALAB_API_KEY")
        marker_service = MarkerService(api_key=api_key)
        try:
            pages, blocks = await marker_service.process_document(file_data)
        except Exception as e:
            print(f"Error during Marker processing: {e}")
            return
        # Cache the pages and blocks for future runs.
        cache_data = {
            "pages": [page.model_dump() for page in pages],
            "blocks": [block.model_dump() for block in blocks]
        }
        with open(cache_path, "w") as f:
            json.dump(cache_data, f, indent=2)
        print(f"Cached Marker API response to {cache_path}")

    print(f"Extracted {len(pages)} pages and {len(blocks)} blocks from the document.")

    # Optionally, build and print a context string for debugging.
    context = build_context_from_blocks(blocks)
    print("\n--- Generated Context ---\n")
    print(context)

    # Load prompts from YAML
    prompt_path = os.path.join("prompts", "prompt.yml")
    if not os.path.exists(prompt_path):
        print(f"Prompt file not found at {prompt_path}. Please add prompt.yml.")
        return
    with open(prompt_path, "r") as f:
        prompts = yaml.safe_load(f)
    system_prompt = prompts.get("system")
    initial_analysis_prompt = prompts.get("initial_analysis")
    follow_up_prompt = prompts.get("follow_up")

    # Initialize LLM service (ensure OPENAI_API_KEY is set)
    llm_api_key = os.getenv("OPENAI_API_KEY")
    llm_service = LLMService(api_key=llm_api_key)

    # Initialize the structured insight service.
    sis = StructuredInsightService()

    # Add the system prompt once to the cumulative conversation.
    if not sis.get_cumulative_messages():
        sis._update_cumulative_messages([
            Message(conversation_id="global", role=MessageRole.SYSTEM, content=system_prompt)
        ])

    # Filter blocks to only desired types: Text, Equation, TextInlineMath, ListItem.
    desired_types = {"Text", "Equation", "TextInlineMath", "ListItem"}
    filtered_blocks = [b for b in blocks if b.block_type in desired_types]
    print(f"\nProcessing {len(filtered_blocks)} blocks of interest for structured insights.")

    # For each filtered block, we build a growing conversation.
    for block in filtered_blocks:
        conversation_id = f"conv-{block.id}"
        # Prepare new messages for the current block.
        block_messages = []
        block_text = block.html_content or ""
        plain_text = re.sub(r'<[^>]+>', '', block_text).strip()
        initial_message = (
            f"{initial_analysis_prompt}\n"
            f"[Block ID: {block.id}, Page: {block.page_id}]\n"
            f"{plain_text}"
        )
        block_messages.append(Message(conversation_id=conversation_id, role=MessageRole.USER, content=initial_message))

        if verbose:
            print(f"\n--- Processing Block ID: {block.id}, Page: {block.page_number} ---")
            print(f"Initial message: {initial_message}")

        # Create full context: cumulative messages so far + new block messages.
        full_context = sis.get_cumulative_messages() + block_messages

        # Call LLM for initial analysis using full context.
        response1 = await llm_service.generate_response(full_context)
        block_messages.append(Message(conversation_id=conversation_id, role=MessageRole.ASSISTANT, content=response1))
        if verbose:
            print(f"Response 1: {response1}")

        # Append follow-up message.
        block_messages.append(Message(conversation_id=conversation_id, role=MessageRole.USER, content=follow_up_prompt))
        if verbose:
            print(f"Follow-up message: {follow_up_prompt}")

        # Create new full context with cumulative + block messages so far.
        full_context = sis.get_cumulative_messages() + block_messages
        response2 = await llm_service.generate_response(full_context)
        block_messages.append(Message(conversation_id=conversation_id, role=MessageRole.ASSISTANT, content=response2))
        if verbose:
            print(f"Response 2: {response2}")

        # Update the cumulative conversation with just the new block messages.
        sis._update_cumulative_messages(block_messages)
        # Also add the block's conversation to structured insights (using block.page_number)
        sis.add_block_conversation(block_messages, block_id=block.id, page_number=block.page_number)

    # Print cumulative messages (for prompt caching)
    print("\nCumulative Messages:")
    for msg in sis.get_cumulative_messages():
        print(f"{msg.role}: {msg.content}")

    # Print all structured insights using model_dump_json
    print("\nStructured Insights:")
    for ins in sis.get_all_insights():
        print(ins.model_dump_json(indent=2))

    # Generate a unique filename for saving insights
    unique_filename = generate_unique_filename(pdf_hash)
    sis.save_insights_to_json(unique_filename)
    print(f"\nInsights saved to {unique_filename}")

if __name__ == "__main__":
    asyncio.run(main())