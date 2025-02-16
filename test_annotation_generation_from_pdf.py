# test_annotation_generation_from_pdf.py

import asyncio
import os
import json
import hashlib
from datetime import datetime
from dotenv import load_dotenv

from src.services.document.marker_service import MarkerService
from build_context_from_blocks import build_context_from_blocks
from src.services.rumination.structured_insight_service import StructuredInsightService
from src.models.viewer.block import Block
from src.models.conversation.message import Message
load_dotenv()

verbose = True
pdf_name = "deepseek_introduction_page_1"

def compute_hash(file_data: bytes) -> str:
    """Compute SHA-256 hash of file data."""
    return hashlib.sha256(file_data).hexdigest()

def generate_unique_filename(pdf_hash: str) -> str:
    """Generate a unique filename using the pdf hash and current timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"annotations_{pdf_hash[:8]}_{timestamp}.json"

async def main():
    # Path to the sample PDF file in the 'pdf' directory.
    pdf_path = os.path.join("pdf", f"{pdf_name}.pdf")
    if not os.path.exists(pdf_path):
        print(f"PDF file not found at {pdf_path}. Please add a sample PDF to the 'pdf' directory.")
        return

    # Read PDF file as bytes and compute its hash.
    with open(pdf_path, "rb") as f:
        file_data = f.read()
    pdf_hash = compute_hash(file_data)

    # Setup cache directory and file path.
    cache_dir = "cache"
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, f"{pdf_hash}.json")

    # Load cached Marker API response if available; otherwise, call Marker API.
    if os.path.exists(cache_path):
        print("Loading cached Marker API response...")
        with open(cache_path, "r") as f:
            cache_data = json.load(f)
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
        cache_data = {
            "pages": [page.model_dump() for page in pages],
            "blocks": [block.model_dump() for block in blocks]
        }
        with open(cache_path, "w") as f:
            json.dump(cache_data, f, indent=2)
        print(f"Cached Marker API response to {cache_path}")

    print(f"Extracted {len(pages)} pages and {len(blocks)} blocks from the document.")

    # Optionally, print a context string for debugging.
    context = build_context_from_blocks(blocks)
    print("\n--- Generated Context ---\n")
    print(context)

    # Initialize the StructuredInsightService.
    sis = StructuredInsightService()
    # Add the system prompt to the cumulative messages (only once).
    if not sis.get_cumulative_messages():
        sis._update_cumulative_messages([
            # Use a global conversation ID for static content.
            # The system prompt is already injected with the objective.
            Message(conversation_id="global", role="system", content=sis.prompts["system"])
        ])

    # Filter blocks to desired types.
    desired_types = {"Text", "Equation", "TextInlineMath", "ListItem"}
    filtered_blocks = [b for b in blocks if b.block_type in desired_types]
    print(f"\nProcessing {len(filtered_blocks)} blocks for annotation extraction.")

    # Process each block using the analyze_block method.
    for block in filtered_blocks:
        insight = await sis.analyze_block(block)
        if verbose:
            print(f"\nStructured Insight for Block {block.id}:")
            print(insight.model_dump_json(indent=2))

    # Print cumulative messages for debugging.
    print("\nCumulative Messages:")
    for msg in sis.get_cumulative_messages():
        print(f"{msg.role}: {msg.content}")

    # Save all structured insights to a unique file.
    unique_filename = generate_unique_filename(pdf_hash)
    sis.save_insights_to_json(unique_filename)
    print(f"\nInsights saved to {unique_filename}")

if __name__ == "__main__":
    asyncio.run(main())
