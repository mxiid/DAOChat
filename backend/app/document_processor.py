from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from typing import List, Optional
from pathlib import Path
import logging
import os
from .config import Config
from unstructured_ingest.v2.pipeline.pipeline import Pipeline
from unstructured_ingest.v2.interfaces import ProcessorConfig
from unstructured_ingest.v2.processes.partitioner import PartitionerConfig
from unstructured_ingest.v2.processes.connectors.local import (
    LocalIndexerConfig,
    LocalDownloaderConfig,
    LocalConnectionConfig,
    LocalUploaderConfig
)
import requests
import PyPDF2
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time

logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        self.api_key = os.getenv("UNSTRUCTURED_API_KEY")
        self.api_url = os.getenv("UNSTRUCTURED_API_URL", "https://api.unstructured.io/general/v0/general")
        if not self.api_key:
            raise ValueError("UNSTRUCTURED_API_KEY environment variable not set")

    def process_pdf(self, file_path: str) -> List[Document]:
        """Process a single PDF file using Unstructured API directly"""
        import requests
        import PyPDF2
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        import time
        
        try:
            logger.info(f"Processing PDF: {file_path}")
            documents = []
            
            # Create a session with retry logic
            session = requests.Session()
            retries = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[408, 429, 500, 502, 503, 504]
            )
            session.mount('https://', HTTPAdapter(max_retries=retries))
            
            # Open PDF and get number of pages
            with open(file_path, "rb") as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                num_pages = len(pdf_reader.pages)
                logger.info(f"PDF has {num_pages} pages")
            
            # Process the entire PDF in one request
            logger.info("Sending PDF for processing...")
            try:
                with open(file_path, "rb") as f:
                    response = session.post(
                        self.api_url,
                        headers={
                            "unstructured-api-key": self.api_key,
                            "accept": "application/json"
                        },
                        files={"files": f},
                        timeout=300  # 5 minutes timeout
                    )
                
                if response.status_code == 200:
                    elements = response.json()
                    logger.info(f"Successfully received {len(elements)} elements from API")
                    
                    # Debug log to see what we're getting
                    if elements:
                        logger.info(f"Element types distribution: {dict((e.get('type'), elements.count(e.get('type'))) for e in elements)}")
                    
                    for element in elements:
                        # Skip images and very short text
                        if (element.get("text") and 
                            element.get("type") != "Image" and
                            len(element["text"].strip()) > 10):
                            
                            documents.append(
                                Document(
                                    page_content=element["text"].strip(),
                                    metadata={
                                        "source": file_path,
                                        "type": element.get("type", "unknown"),
                                        "page_num": element.get("metadata", {}).get("page_number", 0)
                                    }
                                )
                            )
                    
                    # Sort documents by page number
                    documents.sort(key=lambda x: x.metadata["page_num"])
                    
                    logger.info(f"Created {len(documents)} documents from {len(elements)} elements")
                    
                    # Debug log for document content - show first meaningful text
                    if documents:
                        narrative_docs = [doc for doc in documents if doc.metadata["type"] == "NarrativeText"]
                        if narrative_docs:
                            logger.info("Sample narrative content:")
                            logger.info(f"Page {narrative_docs[0].metadata['page_num']}: {narrative_docs[0].page_content[:200]}...")
                else:
                    logger.error(f"Error response from API: {response.status_code}")
                    logger.error(f"Response content: {response.text}")
                    response.raise_for_status()
                
            except requests.exceptions.Timeout:
                logger.error("Request timed out. The API might still be processing the document.")
                raise
            
            return documents
            
        except Exception as e:
            logger.error(f"Error processing PDF {file_path}: {str(e)}")
            raise

    def create_or_update_index(self, pdf_directory: str, existing_index_path: Optional[str] = None) -> FAISS:
        """Create or update FAISS index from a directory of PDFs"""
        try:
            # Process all PDFs in directory
            pdf_files = list(Path(pdf_directory).glob("*.pdf"))
            if not pdf_files:
                raise ValueError(f"No PDF files found in {pdf_directory}")
            
            all_docs = []
            for pdf_file in pdf_files:
                docs = self.process_pdf(str(pdf_file))
                all_docs.extend(docs)
            
            if not all_docs:
                raise ValueError("No valid documents extracted from PDFs")
            
            # Create new vectorstore
            texts = [doc.page_content for doc in all_docs]
            metadatas = [doc.metadata for doc in all_docs]
            
            new_db = FAISS.from_texts(
                texts,
                self.embeddings,
                metadatas=metadatas
            )
            
            # If updating existing index
            if existing_index_path and Path(existing_index_path).exists():
                try:
                    existing_db = FAISS.load_local(
                        existing_index_path, 
                        self.embeddings,
                        allow_dangerous_deserialization=True
                    )
                    existing_db.merge_from(new_db)
                    new_db = existing_db
                    logger.info(f"Updated existing index at {existing_index_path}")
                except Exception as e:
                    logger.error(f"Error updating existing index: {e}")
                    logger.info("Creating new index instead")
            
            # Save the index
            new_db.save_local(Config.FAISS_INDEX_PATH)
            logger.info(f"Saved index with {len(texts)} documents to {Config.FAISS_INDEX_PATH}")
            
            return new_db
            
        except Exception as e:
            logger.error(f"Error creating/updating index: {str(e)}")
            raise

    def verify_index(self, index_path: str) -> None:
        """Verify the contents of a FAISS index"""
        try:
            vectordb = FAISS.load_local(
                index_path, 
                self.embeddings,
                allow_dangerous_deserialization=True
            )
            
            # Sample some documents
            results = vectordb.similarity_search(
                "Show me everything",
                k=5  # Adjust number of samples
            )
            
            logger.info(f"Index verification results:")
            for i, doc in enumerate(results):
                logger.info(f"\nDocument {i+1}:")
                logger.info(f"Content preview: {doc.page_content[:200]}...")
                logger.info(f"Metadata: {doc.metadata}")
                
        except Exception as e:
            logger.error(f"Error verifying index: {str(e)}")
            raise 