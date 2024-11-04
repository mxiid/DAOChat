import logging
from pathlib import Path
from typing import List, Dict
from langchain.docstore.document import Document
from .document_processor import DocumentProcessor
from .config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def analyze_document_quality(docs: List[Document]) -> Dict:
    """Analyze the quality of processed documents"""
    stats = {
        "total_docs": len(docs),
        "avg_length": sum(len(doc.page_content) for doc in docs) / len(docs) if docs else 0,
        "projects": {},
        "content_stats": {
            "with_numerical": 0,
            "with_lists": 0,
            "with_tables": 0,
        },
        "potential_issues": []
    }
    
    # Analyze each document
    for doc in docs:
        # Project coverage
        project = doc.metadata.get("project", "unknown")
        if project not in stats["projects"]:
            stats["projects"][project] = {
                "count": 0,
                "total_length": 0,
                "has_numerical": 0,
                "has_lists": 0,
                "has_tables": 0
            }
        
        stats["projects"][project]["count"] += 1
        stats["projects"][project]["total_length"] += len(doc.page_content)
        
        # Content statistics
        if doc.metadata.get("contains_numerical_data"):
            stats["content_stats"]["with_numerical"] += 1
            stats["projects"][project]["has_numerical"] += 1
        if doc.metadata.get("contains_lists"):
            stats["content_stats"]["with_lists"] += 1
            stats["projects"][project]["has_lists"] += 1
        if doc.metadata.get("contains_tables"):
            stats["content_stats"]["with_tables"] += 1
            stats["projects"][project]["has_tables"] += 1
    
    # Identify potential issues
    for project, data in stats["projects"].items():
        if data["count"] < 3:
            stats["potential_issues"].append(
                f"Low document count for {project}: {data['count']} documents"
            )
        avg_length = data["total_length"] / data["count"]
        if avg_length < 100:
            stats["potential_issues"].append(
                f"Very short documents for {project}: avg {avg_length:.0f} chars"
            )
        if data["has_numerical"] == 0:
            stats["potential_issues"].append(
                f"No numerical data found for {project}"
            )
    
    return stats

def main(verify_only=False, force_rebuild=False):
    processor = DocumentProcessor()
    data_dir = Path("backend/data")
    index_path = Path(Config.FAISS_INDEX_PATH)
    
    try:
        if force_rebuild and index_path.exists():
            logger.info("Removing existing index...")
            if index_path.is_dir():
                for file in index_path.glob("*"):
                    file.unlink()
                index_path.rmdir()
            else:
                index_path.unlink()
        
        if not verify_only:
            all_docs = []
            logger.info("Starting document processing...")
            
            # Process all supported file types
            file_processors = {
                "*.pdf": processor.process_pdf,
                "*.md": processor.process_markdown,
                "*.csv": processor.process_csv
            }
            
            for pattern, proc_func in file_processors.items():
                files = list(data_dir.glob(pattern))
                for file in files:
                    logger.info(f"Processing {file.name}...")
                    try:
                        docs = proc_func(str(file))
                        all_docs.extend(docs)
                        logger.info(f"Successfully processed {len(docs)} sections from {file.name}")
                    except Exception as e:
                        logger.error(f"Error processing {file.name}: {str(e)}")
                        continue
            
            # Create new index
            logger.info("\nCreating new FAISS index...")
            processor.create_or_update_index(str(data_dir))
            logger.info("Index created successfully")
            
            # Analyze quality
            quality_stats = analyze_document_quality(all_docs)
            
            # Log comprehensive statistics
            logger.info("\n=== Processing Statistics ===")
            logger.info(f"Total documents processed: {quality_stats['total_docs']}")
            logger.info(f"Average document length: {quality_stats['avg_length']:.0f} characters")
            
            logger.info("\nProject Coverage:")
            for project, data in quality_stats["projects"].items():
                logger.info(f"\n{project}:")
                logger.info(f"  Documents: {data['count']}")
                logger.info(f"  Average length: {data['total_length'] / data['count']:.0f} chars")
                logger.info(f"  Documents with numerical data: {data['has_numerical']}")
                logger.info(f"  Documents with lists: {data['has_lists']}")
                logger.info(f"  Documents with tables: {data['has_tables']}")
            
            logger.info("\nContent Statistics:")
            for key, value in quality_stats["content_stats"].items():
                logger.info(f"{key}: {value} documents")
            
            # Log potential issues
            if quality_stats["potential_issues"]:
                logger.warning("\nPotential Issues Detected:")
                for issue in quality_stats["potential_issues"]:
                    logger.warning(f"⚠️ {issue}")
        
        if index_path.exists():
            # Verify index
            logger.info("\nVerifying index...")
            processor.verify_index(Config.FAISS_INDEX_PATH)
            logger.info("Index verification completed successfully")
        else:
            logger.warning("No index found to verify")
        
    except Exception as e:
        logger.error(f"Error in index creation process: {e}")
        raise

if __name__ == "__main__":
    import sys
    verify_only = "--verify" in sys.argv
    force_rebuild = "--rebuild" in sys.argv
    main(verify_only=verify_only, force_rebuild=force_rebuild)