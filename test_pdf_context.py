# test_pdf_context.py
import asyncio
import os

from src.services.document.marker_service import MarkerService
from build_context_from_blocks import build_context_from_blocks

from dotenv import load_dotenv

load_dotenv()

async def main():
    # Path to your sample PDF file in the 'pdf' directory
    pdf_path = os.path.join("pdf", "aime.pdf")
    if not os.path.exists(pdf_path):
        print(f"PDF file not found at {pdf_path}. Please add a sample PDF to the 'pdf' directory.")
        return

    # Read the PDF file as bytes
    with open(pdf_path, "rb") as f:
        file_data = f.read()

    # Instantiate MarkerService using an API key.
    # Replace 'your_marker_api_key' with your actual API key or set the MARKER_API_KEY environment variable.
    api_key = os.getenv("DATALAB_API_KEY")
    marker_service = MarkerService(api_key=api_key)

    print("Processing PDF with Marker API...")
    try:
        pages, blocks = await marker_service.process_document(file_data)
    except Exception as e:
        print(f"Error during Marker processing: {e}")
        return

    print(f"Extracted {len(pages)} pages and {len(blocks)} blocks from the document.")

    # Build a context string from the extracted blocks
    context = build_context_from_blocks(blocks)
    print("\n--- Generated Context ---\n")
    print(context)

if __name__ == "__main__":
    asyncio.run(main())