import re
from typing import List, Optional
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.models.viewer.block import Block, BlockType

def strip_html(html: str) -> str:
    """
    A simple utility to remove HTML tags.
    In a production system, consider using a library like BeautifulSoup for more robust handling.
    """
    return re.sub(r'<[^>]+>', '', html)

def build_context_from_blocks(blocks: List[Block], max_chars: Optional[int] = None) -> str:
    """
    Build a context string from a list of Block objects.
    
    Args:
        blocks: A list of Block objects.
        max_chars: Optional maximum number of characters to include in the context.
    
    Returns:
        A string that aggregates block text with headers, ready for a single LLM call.
    """
    # Sort blocks by page number (or another relevant attribute)
    sorted_blocks = sorted(blocks, key=lambda b: (b.page_number or 0))
    
    context_parts = []
    total_chars = 0

    for block in sorted_blocks:
        # Extract plain text from HTML content
        block_text = strip_html(block.html_content or "").strip()
        if not block_text:
            continue
        
        header = f"[Page {block.page_number or 'N/A'} | {block.block_type}]:"
        part = f"{header}\n{block_text}"
        
        # If a maximum character limit is set, check whether adding this part would exceed it.
        if max_chars is not None:
            if total_chars + len(part) > max_chars:
                # Optionally, you can truncate the part to fit or break out of the loop.
                break
            total_chars += len(part)
        
        context_parts.append(part)
    
    # Join with a couple of newlines between blocks for readability
    context = "\n\n".join(context_parts)
    return context

# Example usage:
if __name__ == "__main__":
    # Imagine we have a list of Block objects from our document processing pipeline.
    # blocks = load_blocks_from_document(document_id)  # pseudo-code
    # For demonstration, let's create a dummy list:
    dummy_blocks = [
        Block(
            id="block1",
            page_number=1,
            block_type=BlockType.PAGE_HEADER,
            html_content="<p>Document Title: The Uncanny</p>"
        ),
        Block(
            id="block2",
            page_number=2,
            block_type=BlockType.TEXT,
            html_content="<p>This is the first paragraph of the document.</p>"
        )
    ]
    
    context = build_context_from_blocks(dummy_blocks)
    print(context)