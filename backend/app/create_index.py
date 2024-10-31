import logging
from pathlib import Path
from .document_processor import DocumentProcessor
from .config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # Initialize processor
    processor = DocumentProcessor()
    
    # Define paths
    pdf_directory = Config.DOCUMENTS_PATH
    index_path = Config.FAISS_INDEX_PATH
    
    try:
        # Create or update index
        vectorstore = processor.create_or_update_index(
            pdf_directory=pdf_directory,
            existing_index_path=index_path
        )
        
        # Verify the index
        processor.verify_index(index_path)
        
        logger.info("Index creation/update completed successfully")
        
    except Exception as e:
        logger.error(f"Error in index creation process: {e}")
        raise

if __name__ == "__main__":
    main() 