from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from typing import List, Optional, Dict
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
from PyPDF2 import PdfWriter
import tempfile
import json
from collections import defaultdict
import re
import pandas as pd
import frontmatter  # pip install python-frontmatter

logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings()
        
        # Create different splitters for different content types
        self.splitters = {
            "overview": RecursiveCharacterTextSplitter(
                chunk_size=2000,
                chunk_overlap=200,
                separators=["\n\n", "\n", ". ", " ", ""]
            ),
            "metadata": RecursiveCharacterTextSplitter(
                chunk_size=500,
                chunk_overlap=100,
                separators=["\n\n", "\n", ". ", " ", ""]
            ),
            "content": RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=150,
                separators=["\n\n", "\n", ". ", " ", ""]
            )
        }
        self.api_key = os.getenv("UNSTRUCTURED_API_KEY")
        self.api_url = os.getenv("UNSTRUCTURED_API_URL", "https://api.unstructured.io/general/v0/general")
        if not self.api_key:
            raise ValueError("UNSTRUCTURED_API_KEY environment variable not set")

    def _cache_documents(self, documents: List[Document], cache_file: str) -> None:
        """Cache processed documents to file"""
        cache_data = []
        for doc in documents:
            cache_data.append({
                "content": doc.page_content,
                "metadata": doc.metadata
            })

        cache_path = Path("document_cache")
        cache_path.mkdir(exist_ok=True)

        with open(cache_path / cache_file, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)

        logger.info(f"Cached {len(documents)} documents to {cache_file}")

    def _load_cached_documents(self, cache_file: str) -> List[Document]:
        """Load documents from cache"""
        cache_path = Path("document_cache") / cache_file

        if not cache_path.exists():
            logger.warning(f"Cache file not found: {cache_file}")
            return []

        try:
            with open(cache_path, encoding="utf-8") as f:
                cache_data = json.load(f)

            documents = []
            for item in cache_data:
                documents.append(
                    Document(
                        page_content=item["content"],
                        metadata=item["metadata"]
                    )
                )

            logger.info(f"Loaded {len(documents)} documents from cache")
            return documents

        except Exception as e:
            logger.error(f"Error loading cache {cache_file}: {e}")
            return []

    def process_pdf(self, file_path: str) -> List[Document]:
        """Process PDF with progress saving and retry logic"""
        progress_file = Path("processing_progress.json")

        try:
            # Create cache directory if it doesn't exist
            Path("document_cache").mkdir(exist_ok=True)

            # Load previous progress if exists
            if progress_file.exists():
                with open(progress_file) as f:
                    progress = json.load(f)
            else:
                progress = {}

            file_key = str(Path(file_path).name)
            if file_key in progress and progress[file_key].get("completed"):
                logger.info(f"Skipping already processed file: {file_path}")
                return self._load_cached_documents(progress[file_key]["cache_file"])

            logger.info(f"Processing PDF: {file_path}")
            all_elements = []

            # Process in very small chunks (2 pages)
            chunk_size = 2
            with open(file_path, "rb") as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                num_pages = len(pdf_reader.pages)
                logger.info(f"PDF has {num_pages} pages")

                # Resume from last successful chunk if available
                start_page = progress.get(file_key, {}).get("last_page", 0)

                for start_page in range(start_page, num_pages, chunk_size):
                    end_page = min(start_page + chunk_size, num_pages)

                    # Try processing this chunk with retries
                    chunk_elements = self._process_chunk_with_retry(
                        file_path, start_page, end_page,
                        max_retries=3, base_timeout=60
                    )

                    if chunk_elements:
                        all_elements.extend(chunk_elements)
                        # Save progress
                        progress[file_key] = {
                            "last_page": end_page,
                            "total_elements": len(all_elements)
                        }
                        with open(progress_file, "w") as f:
                            json.dump(progress, f)

                    # Longer delay between chunks
                    time.sleep(5)

            # Process collected elements into documents
            documents = self._create_documents_from_elements(all_elements, file_path)

            # Cache the results
            cache_file = f"cache_{file_key}.json"
            self._cache_documents(documents, cache_file)
            progress[file_key] = {
                "completed": True,
                "cache_file": cache_file
            }
            with open(progress_file, "w") as f:
                json.dump(progress, f)

            return documents

        except Exception as e:
            logger.error(f"Error processing PDF {file_path}: {str(e)}")
            raise

    def _process_chunk_with_retry(self, file_path: str, start_page: int, end_page: int, 
                                max_retries: int = 3, base_timeout: int = 60) -> List[Dict]:
        """Process a chunk of PDF with retries"""
        pdf_writer = PdfWriter()

        # Create chunk PDF
        with open(file_path, "rb") as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            for page_num in range(start_page, end_page):
                pdf_writer.add_page(pdf_reader.pages[page_num])

        # Try processing with increasing timeouts
        for attempt in range(max_retries):
            timeout = base_timeout * (attempt + 1)  # Increase timeout with each retry

            try:
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_pdf:
                    pdf_writer.write(temp_pdf)
                    temp_pdf_path = temp_pdf.name

                logger.info(f"Processing pages {start_page + 1} to {end_page} (Attempt {attempt + 1}/{max_retries}, timeout={timeout}s)")

                with open(temp_pdf_path, "rb") as f:
                    response = requests.post(
                        self.api_url,
                        headers={
                            "unstructured-api-key": self.api_key,
                            "accept": "application/json"
                        },
                        files={"files": f},
                        timeout=timeout
                    )

                if response.status_code == 200:
                    elements = response.json()
                    logger.info(f"Received {len(elements)} elements")
                    return elements

            except requests.exceptions.Timeout:
                logger.warning(f"Timeout on attempt {attempt + 1}/{max_retries}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(10)  # Wait longer between retries

            except Exception as e:
                logger.error(f"Error on attempt {attempt + 1}: {str(e)}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(10)

            finally:
                try:
                    os.unlink(temp_pdf_path)
                except:
                    pass

        return []

    def _create_documents_from_elements(self, elements: List[Dict], file_path: str) -> List[Document]:
        """Create semantic documents with content-aware chunking"""
        documents = []
        current_section = []
        current_section_text = ""
        current_page_range = None
        project_name = Path(file_path).stem

        # Track semantic boundaries
        semantic_markers = {
            "section_start": ["introduction", "overview", "about", "features", "specifications", 
                             "pricing", "location", "payment", "amenities", "floor plan",
                             "contact", "timeline", "schedule", "terms", "conditions"],
            "important_elements": ["title", "header", "heading", "subheading", "table", "list"]
        }

        for element in elements:
            if not element.get("text"):
                continue

            text = element["text"].strip()
            if len(text) < 20:  # Skip very short elements
                continue

            element_type = element.get("type", "unknown").lower()
            page_num = element.get("page_number", None)

            # Detect semantic boundaries
            is_semantic_boundary = (
                element_type in semantic_markers["important_elements"] or
                any(marker in text.lower() for marker in semantic_markers["section_start"]) or
                len(current_section_text) > 1000 or  # Length-based boundary
                (page_num and current_page_range and abs(page_num - current_page_range[-1]) > 1)  # Page boundary
            )

            if is_semantic_boundary and current_section:
                # Create document from current section
                doc_text = "\n".join(sec["text"].strip() for sec in current_section)
                start_page = current_section[0].get("page_number")
                end_page = current_section[-1].get("page_number")

                # Extract semantic context
                semantic_context = {
                    "source": file_path,
                    "project": project_name,
                    "page_range": f"{start_page}-{end_page}" if start_page and end_page else "unknown",
                    "section_type": current_section[0].get("type", "unknown"),
                    "section_title": current_section[0].get("text", "")[:100],
                    "content_structure": element_type,
                    "semantic_markers": [marker for marker in semantic_markers["section_start"] 
                                      if marker in doc_text.lower()],
                    "contains_numerical_data": bool(re.search(r'\d+', doc_text)),
                    "contains_lists": bool(re.search(r'(?:^|\n)\s*[•\-\d]+\.?\s+', doc_text)),
                    "contains_tables": bool(re.search(r'\|\s*\w+\s*\|', doc_text)),
                    "text_length": len(doc_text),
                    "content_type": "overview" if "overview" in file_path.lower() else "detail",
                    # Extract specific data points
                    "price": re.search(r'(?:PKR|Rs\.?)\s*([\d,]+)', doc_text),
                    "location": re.search(r'(?:location|located in|address):\s*([^•\n]+)', doc_text, re.I),
                    "roi": re.search(r'(?:ROI|return|yield):\s*([\d.]+%)', doc_text, re.I),
                    "completion": re.search(r'(?:completion|timeline|complete by):\s*(\d{4})', doc_text, re.I)
                }

                documents.append(
                    Document(
                        page_content=doc_text,
                        metadata=semantic_context
                    )
                )

                current_section = []
                current_section_text = ""
                current_page_range = []

            current_section.append(element)
            current_section_text += f"\n{text}"
            if page_num:
                current_page_range = current_page_range or []
                current_page_range.append(page_num)

        # Process the last section
        if current_section:
            doc_text = "\n".join(sec["text"].strip() for sec in current_section)
            start_page = current_section[0].get("page_number")
            end_page = current_section[-1].get("page_number")

            semantic_context = {
                "source": file_path,
                "project": project_name,
                "page_range": f"{start_page}-{end_page}" if start_page and end_page else "unknown",
                "section_type": current_section[0].get("type", "unknown"),
                "section_title": current_section[0].get("text", "")[:100],
                "content_structure": element_type,
                "semantic_markers": [marker for marker in semantic_markers["section_start"] 
                                      if marker in doc_text.lower()],
                "contains_numerical_data": bool(re.search(r'\d+', doc_text)),
                "contains_lists": bool(re.search(r'(?:^|\n)\s*[•\-\d]+\.?\s+', doc_text)),
                "contains_tables": bool(re.search(r'\|\s*\w+\s*\|', doc_text)),
                "text_length": len(doc_text),
                "content_type": "overview" if "overview" in file_path.lower() else "detail",
                # Extract specific data points
                "price": re.search(r'(?:PKR|Rs\.?)\s*([\d,]+)', doc_text),
                "location": re.search(r'(?:location|located in|address):\s*([^•\n]+)', doc_text, re.I),
                "roi": re.search(r'(?:ROI|return|yield):\s*([\d.]+%)', doc_text, re.I),
                "completion": re.search(r'(?:completion|timeline|complete by):\s*(\d{4})', doc_text, re.I)
            }

            documents.append(
                Document(
                    page_content=doc_text,
                    metadata=semantic_context
                )
            )

        return documents

    def create_or_update_index(self, directory: str, existing_index_path: Optional[str] = None) -> FAISS:
        try:
            all_docs = []
            
            # Define file processors
            file_processors = {
                "*.pdf": self.process_pdf,
                "*.md": self.process_markdown,
                "*.csv": self.process_csv
            }
            
            # Process overview document first
            overview_file = Path(directory) / "overview.md"
            if overview_file.exists():
                logger.info("Processing overview document...")
                overview_docs = self.process_markdown(str(overview_file))
                all_docs.extend(overview_docs)
            
            # Then process other files
            for pattern, processor in file_processors.items():
                files = list(Path(directory).glob(pattern))
                for file in files:
                    if file != overview_file:  # Skip overview file as it's already processed
                        try:
                            logger.info(f"Processing {file}...")
                            docs = processor(str(file))
                            all_docs.extend(docs)
                        except Exception as e:
                            logger.error(f"Error processing {file}: {e}")
                            continue
            
            # Create embeddings and index
            logger.info("Creating embeddings and index...")
            texts = [doc.page_content for doc in all_docs]
            metadatas = [doc.metadata for doc in all_docs]
            
            # Create new vectorstore
            new_db = FAISS.from_texts(
                texts=texts,
                embedding=self.embeddings,
                metadatas=metadatas
            )
            
            # Save the index
            new_db.save_local(Config.FAISS_INDEX_PATH)
            logger.info(f"Saved index with {len(texts)} documents to {Config.FAISS_INDEX_PATH}")
            
            return new_db

        except Exception as e:
            logger.error(f"Error creating/updating index: {str(e)}")
            raise

    def verify_index(self, index_path: str) -> None:
        """Verify the contents of the index with better queries"""
        try:
            vectorstore = FAISS.load_local(
                index_path, 
                self.embeddings,
                allow_dangerous_deserialization=True
            )

            # More specific test queries
            test_queries = [
                # Urban Dwellings
                "What is the exact location of Urban Dwellings project?",
                "What is the expected ROI or return on investment for Urban Dwellings?",
                # Elements Residencia
                "Where exactly is Elements Residencia located?",
                "What is the projected ROI for Elements Residencia investment?",
                # Naya Nazimabad
                "What is the location of Globe Residency in Naya Nazimabad?",
                "What ROI or investment returns can I expect from Globe Residency Naya Nazimabad?",
                # Broad Peak Realty
                "Where is Broad Peak Realty located?",
                "What is the expected ROI for Broad Peak Realty investment?",
                # Akron
                "What is the exact location of Project Akron?",
                "What is the projected return on investment (ROI) for Project Akron?",
                # Cross-project comparisons
                "Compare the locations of all projects: Urban Dwellings, Elements Residencia, Naya Nazimabad, Broad Peak Realty, and Akron",
                "Which project offers the best ROI among Urban Dwellings, Elements Residencia, Naya Nazimabad, Broad Peak Realty, and Akron?",
            ]

            logger.info("\nVerification Results:")
            project_coverage = defaultdict(int)

            for query in test_queries:
                logger.info(f"\nTesting query: {query}")
                docs = vectorstore.similarity_search(
                    query, 
                    k=3,
                    filter=None  # Allow all projects to be searched
                )

                projects_found = set()
                for doc in docs:
                    project = doc.metadata.get("project", "unknown")
                    projects_found.add(project)
                    page_range = doc.metadata.get("page_range", "unknown")
                    section_title = doc.metadata.get("section_title", "unknown")

                    logger.info(f"\nProject: {project}")
                    logger.info(f"Pages: {page_range}")
                    logger.info(f"Section: {section_title}")
                    logger.info(f"Preview: {doc.page_content[:200]}...")

                    project_coverage[project] += 1

                logger.info(f"Projects found for query: {', '.join(projects_found)}")

            # Report coverage
            logger.info("\nProject Coverage in Queries:")
            for project, count in project_coverage.items():
                logger.info(f"{project}: appeared in {count} query results")

        except Exception as e:
            logger.error(f"Error verifying index: {e}")
            raise

    def process_markdown(self, file_path: str) -> List[Document]:
        """Process markdown files with frontmatter"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # Parse frontmatter and content
                post = frontmatter.load(f)
                content = post.content
                metadata = post.metadata

            # Special handling for overview document
            if "overview" in file_path.lower():
                # Use larger chunk size for overview
                chunks = self.splitters["overview"].split_text(content)
            else:
                # Use metadata chunk size for frontmatter-heavy sections
                if metadata:
                    chunks = self.splitters["metadata"].split_text(content)
                else:
                    chunks = self.splitters["content"].split_text(content)

            documents = []
            for chunk in chunks:
                # Enhance metadata with frontmatter
                enhanced_metadata = {
                    "source": file_path,
                    "project": metadata.get("project", Path(file_path).stem),
                    "content_type": "overview" if "overview" in file_path.lower() else "detail",
                    "price": metadata.get("price_sqft", None),
                    "location": metadata.get("location", None),
                    "rental_yield": metadata.get("rental yield", None),
                    "completion": metadata.get("completion_year", None),
                    **metadata  # Include all other frontmatter metadata
                }

                documents.append(
                    Document(
                        page_content=chunk,
                        metadata=enhanced_metadata
                    )
                )

            return documents
                
        except Exception as e:
            logger.error(f"Error processing markdown {file_path}: {str(e)}")
            raise

    def process_csv(self, file_path: str) -> List[Document]:
        """Process CSV files into structured documents"""
        try:
            # Try different encodings
            encodings = ['utf-8', 'latin1', 'cp1252', 'iso-8859-1']
            df = None
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(file_path, encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue
            
            if df is None:
                raise ValueError(f"Could not read CSV with any of the attempted encodings: {encodings}")
                
            # Rest of the processing...
            documents = []
            for idx, row in df.iterrows():
                content_parts = []
                for col, value in row.items():
                    if pd.notna(value):
                        content_parts.append(f"{col}: {value}")
                
                content = "\n".join(content_parts)
                
                metadata = {
                    "source": file_path,
                    "project": Path(file_path).stem,
                    "document_type": "csv",
                    "row_index": idx,
                    "contains_numerical_data": any(isinstance(v, (int, float)) for v in row if pd.notna(v)),
                    "columns": list(df.columns),
                    "text_length": len(content)
                }
                
                documents.append(
                    Document(
                        page_content=content,
                        metadata=metadata
                    )
                )
            
            return documents
                
        except Exception as e:
            logger.error(f"Error processing CSV {file_path}: {str(e)}")
            raise
