import logging
from pathlib import Path
from .document_processor import DocumentProcessor
from .config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main(verify_only=False):
    processor = DocumentProcessor()
    data_dir = Path("backend/data")
    
    try:
        if not verify_only:
            # Process all PDFs
            all_docs = []
            for pdf_file in data_dir.glob("*.pdf"):
                docs = processor.process_pdf(str(pdf_file))
                all_docs.extend(docs)
                
            logger.info(f"\nTotal documents processed: {len(all_docs)}")
            logger.info("Documents per project:")
            project_counts = {}
            for doc in all_docs:
                project = doc.metadata["project"]
                project_counts[project] = project_counts.get(project, 0) + 1
            for project, count in project_counts.items():
                logger.info(f"{project}: {count} pages")
        
        # Verify with comprehensive checks
        processor.verify_index(Config.FAISS_INDEX_PATH)
        
        logger.info("Index verification completed successfully")
        
    except Exception as e:
        logger.error(f"Error in index creation process: {e}")
        raise

if __name__ == "__main__":
    import sys
    verify_only = "--verify" in sys.argv
    main(verify_only=verify_only) 