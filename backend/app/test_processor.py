import os
from pathlib import Path
from .document_processor import DocumentProcessor
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_pdf_processing():
    processor = DocumentProcessor()
    
    # Get the project root directory (assuming we're in backend/app)
    current_dir = Path(__file__).parent  # backend/app
    project_root = current_dir.parent.parent  # main project directory
    
    # Construct path to the PDF file
    pdf_path = project_root / "backend" / "data" / "test" / "test.pdf"
    
    # Verify file exists
    if not pdf_path.exists():
        logger.error(f"PDF file not found at: {pdf_path}")
        logger.info(f"Current directory: {os.getcwd()}")
        logger.info(f"Available files in data directory: {list((project_root / 'backend' / 'data').glob('*.pdf'))}")
        return
    
    logger.info(f"Found PDF file at: {pdf_path}")
    
    try:
        documents = processor.process_pdf(str(pdf_path))
        print(f"\nProcessed {len(documents)} documents")
        
        if documents:
            # Group documents by type
            doc_types = {}
            for doc in documents:
                doc_type = doc.metadata["type"]
                if doc_type not in doc_types:
                    doc_types[doc_type] = []
                doc_types[doc_type].append(doc)
            
            print("\nDocument type distribution:")
            for doc_type, docs in doc_types.items():
                print(f"{doc_type}: {len(docs)} elements")
            
            print("\nFirst narrative text content:")
            print("-" * 50)
            narrative_docs = doc_types.get("NarrativeText", [])
            if narrative_docs:
                print(f"Page {narrative_docs[0].metadata['page_num']}:")
                print(narrative_docs[0].page_content[:500])
            print("-" * 50)
            
            print("\nFirst title:")
            title_docs = doc_types.get("Title", [])
            if title_docs:
                print(f"Page {title_docs[0].metadata['page_num']}:")
                print(title_docs[0].page_content)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_pdf_processing() 