from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, CSVLoader
from langchain.schema import HumanMessage, SystemMessage
from .config import Config
import os
import logging
import openai
import csv
import chardet
from io import StringIO
from langchain_core.documents import Document
from langchain.callbacks import AsyncIteratorCallbackHandler
import asyncio
import tiktoken
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
import multiprocessing
from fastapi import HTTPException
import time
from datetime import datetime
from typing import List, Optional
import re

# At the top of your file, after imports
os.environ['TIKTOKEN_CACHE_DIR'] = '/app/tiktoken'

# Initialize tiktoken (this will use the files in the specified cache directory)
tiktoken.get_encoding('cl100k_base')

logger = logging.getLogger(__name__)

class RAG:
    def __init__(self):
        try:
            self.embeddings = OpenAIEmbeddings()
            self.vectordb = self._load_vectordb()

            # Define system message once
            self.system_message = """Answer questions and provide insights solely based on the provided DAO whitepapers and any additional documents. All information shared should be grounded in these whitepapers, supplemented with general knowledge only when it is clearly compatible with the concepts directly discussed in the documents. Answer concisely, offering clarity and actionable insights that relate specifically to DAO governance, structure, PropTech applications, and related DAO operations as detailed in the documents. Always prioritize accuracy and avoid assumptions not backed by the documents. If needed, indicate if a question is beyond the scope of the provided material.

            The primary goal is to engage with clients by addressing frequently asked questions. Engage in a professional, informative tone and avoid speculative answers. Where clarifications are needed, seek to use the document content to fill in gaps or request further details from the user."""

            # Update ChatOpenAI initialization to use model_kwargs
            self.llm = ChatOpenAI(
                temperature=0, 
                model_name='gpt-4o',
                model_kwargs={"system_message": self.system_message}
            )
            self.prompt_template = self._create_prompt_template()

            # Remove the global memory since we're using per-session memory
            # self.memory = ConversationBufferMemory(...)

            # Initialize memory pools with a default TTL (e.g., 30 minutes)
            self.memory_pools = {}
            self.memory_ttl = 1800  # 30 minutes in seconds
            self.last_access = {}

            # CPU-bound task executor (70% of cores for CPU tasks)
            self.cpu_executor = ThreadPoolExecutor(
                max_workers=int(multiprocessing.cpu_count() * 0.7)
            )

            # I/O-bound task executor (2x number of cores for I/O tasks)
            self.io_executor = ThreadPoolExecutor(
                max_workers=multiprocessing.cpu_count() * 2
            )

            # Limit concurrent requests (based on available memory)
            available_memory_gb = 31  # From MemAvailable
            memory_per_request_mb = 500  # Estimated memory per request
            max_concurrent = min(
                int((available_memory_gb * 1024) / memory_per_request_mb),
                50  # Hard cap at 50 concurrent requests
            )
            self.request_semaphore = asyncio.Semaphore(max_concurrent)

            # Request queue
            self.request_queue = asyncio.Queue(maxsize=100)

            # Response cache (50MB max size)
            self.response_cache = lru_cache(maxsize=100)(self._process_request)
        except Exception as e:
            logger.error(f"Error initializing RAG: {str(e)}", exc_info=True)
            raise

    def _load_vectordb(self):
        if os.path.exists(Config.FAISS_INDEX_PATH):
            try:
                vectordb = FAISS.load_local(
                    Config.FAISS_INDEX_PATH, 
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
                logger.info(f"Loaded existing FAISS index from {Config.FAISS_INDEX_PATH}")
                return vectordb
            except Exception as e:
                logger.error(f"Error loading existing index: {e}")
                raise
        else:
            raise FileNotFoundError(f"FAISS index not found at {Config.FAISS_INDEX_PATH}")

    def _create_prompt_template(self):
        # Simplified prompt template that focuses on the current context and question
        template = """
        Context: {context}

        Current Conversation:
        {chat_history}

        Human: {question}

        Assistant:"""
        return PromptTemplate(template=template, input_variables=["context", "chat_history", "question"])

    async def _process_request(self, question: str, session_id: str):
        try:
            query_type = self._classify_query(question.lower())
            project_name = self._extract_project_name(question)

            if project_name:
                # Get project overview first
                overview_docs = self.vectordb.similarity_search(
                    f"{project_name} overview",
                    k=1,
                    filter={"project": project_name, "subsection": "overview"}
                )

                # Get relevant subsection based on query type
                subsection_filter = self._get_subsection_filter(query_type)
                specific_docs = self.vectordb.similarity_search(
                    question,
                    k=2,
                    filter={"project": project_name, "subsection": subsection_filter}
                )

                # Combine and structure the context
                context = self._format_project_response(overview_docs + specific_docs)

            else:
                # Handle general queries
                docs = self.vectordb.similarity_search(question, k=4)
                context = self._format_general_response(docs)

            # Create messages for the chat
            messages = [
                SystemMessage(content=self.system_message),
                HumanMessage(content=f"""Based on the following detailed information, provide a comprehensive and well-structured response:

Context:
{context}

Question: {question}

Please ensure to:
1. Include all relevant project details
2. Format the response with clear sections and bullet points
3. Highlight key investment features and amenities
4. Include specific numbers and metrics where available""")
            ]

            response = await self.llm.apredict_messages(messages)
            return response.content

        except Exception as e:
            logger.error(f"Error in _process_request: {str(e)}")
            raise

    def _get_subsection_filter(self, query_type: str) -> str:
        """Map query type to relevant subsection"""
        mapping = {
            "price": "investment",
            "roi": "investment",
            "location": "overview",
            "features": "amenities",
            "completion": "overview",
            "general": "highlights"
        }
        return mapping.get(query_type, "overview")

    def _format_project_response(self, docs: List[Document]) -> str:
        """Format project documents into structured context"""
        # Extract project metadata from first document
        metadata = docs[0].metadata

        context = f"""Project Overview: {metadata.get('project', 'Unknown Project')}

Key Details:
- Location: {metadata.get('location', '[Not specified]')}
- Project Type: {metadata.get('project_type', '[Not specified]')}
- Total Size: {metadata.get('size', '[Not specified]')}
- Completion Date: {metadata.get('completion', '[Not specified]')}
- Token Price: {metadata.get('price', '[Not specified]')}
- Estimated Rental Yield: {metadata.get('roi', '[Not specified]')}

Detailed Information:
"""

        # Add content from all documents
        for doc in docs:
            context += f"\n{doc.page_content}\n"

        return context

    def _is_better_metadata(self, new_metadata: dict, existing_metadata: dict) -> bool:
        """Compare metadata completeness"""
        key_fields = ['location', 'price_sqft', 'roi', 'completion_year', 'type']
        new_count = sum(1 for k in key_fields if new_metadata.get(k))
        existing_count = sum(1 for k in key_fields if existing_metadata.get(k))
        return new_count > existing_count

    def _extract_project_name(self, query: str) -> Optional[str]:
        """Extract and validate project name from query"""
        project_mapping = {
            "urban dwellings": "Urban Dwellings",
            "elements residencia": "Elements Residencia",
            "globe residency": "Globe Residency Apartments",
            "broad peak": "Broad Peak Realty",
            "akron": "Akron"
        }

        query_lower = query.lower()
        for key, value in project_mapping.items():
            if key in query_lower:
                return value
        return None

    async def query(self, question: str, session_id: str = None) -> str:
        async with self.request_semaphore:
            try:
                # Queue management
                try:
                    await asyncio.wait_for(
                        self.request_queue.put(question), 
                        timeout=5.0
                    )
                except asyncio.TimeoutError:
                    raise HTTPException(
                        status_code=503,
                        detail="System is currently overloaded. Please try again later."
                    )

                # Process request
                result = await self._process_request(question, session_id)
                self.request_queue.task_done()
                return result

            except Exception as e:
                logger.error(f"Error in query method: {str(e)}", exc_info=True)
                raise

    async def generate_questions(self, context: str) -> list[str]:
        try:
            prompt = f"Based on the following context, generate a list of relevant questions:\n\nContext: {context}\n\nQuestions:"
            response = await self.llm.agenerate(prompt)  # Pass the prompt as a string
            questions = response.generations[0][0].text.strip().split('\n')
            return [q.strip() for q in questions if q.strip()]
        except openai.error.APIConnectionError as e:
            logger.error(f"OpenAI API connection error: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="OpenAI API connection error. Please try again later.")
        except Exception as e:
            logger.error(f"Error in generate_questions method: {str(e)}", exc_info=True)
            raise

    async def stream_query(self, question: str, session_id: str):
        try:
            callback = AsyncIteratorCallbackHandler()
            streaming_llm = ChatOpenAI(
                streaming=True,
                callbacks=[callback],
                temperature=0,
                model_name='gpt-4o'
            )

            # Get relevant documents first
            docs = self.vectordb.similarity_search(
                question,
                k=4,
            )
            context = "\n\n".join(doc.page_content for doc in docs)

            # Get or create session-specific memory
            if session_id not in self.memory_pools:
                self.memory_pools[session_id] = ConversationBufferMemory(
                    memory_key="chat_history",
                    return_messages=True,
                    output_key="answer"
                )

            memory = self.memory_pools[session_id]
            chat_history = memory.chat_memory.messages if hasattr(memory, 'chat_memory') else []

            # Format the prompt with context
            formatted_prompt = self.prompt_template.format(
                context=context,
                chat_history=chat_history,
                question=question
            )

            # Create messages for the chat, including system message
            messages = [
                SystemMessage(content=self.system_message),
                HumanMessage(content=formatted_prompt)
            ]

            # Stream the response
            async for chunk in streaming_llm.astream(messages):
                if hasattr(chunk, 'content'):
                    yield chunk.content

            # Update memory after completion
            if hasattr(memory, 'chat_memory'):
                memory.chat_memory.add_user_message(question)
                memory.chat_memory.add_ai_message(formatted_prompt)

        except Exception as e:
            logger.error(f"Error in stream_query: {str(e)}", exc_info=True)
            yield "An error occurred while processing your request."

    def add_texts(self, texts: list[str]):
        """Process and index documents with project-focused chunking"""
        processed_chunks = []

        for text in texts:
            # First, try to identify project sections
            project_sections = re.split(r'\n(?=Project Overview:|# )', text)

            for section in project_sections:
                if not section.strip():
                    continue

                # Extract project name and metadata
                metadata = {
                    "project": self._extract_project_title(section),
                    "location": self._extract_field(section, "Location:"),
                    "project_type": self._extract_field(section, "Project Type:"),
                    "completion": self._extract_field(section, "Completion Date:"),
                    "price": self._extract_field(section, "Token Price:|Price:|Cost:"),
                    "roi": self._extract_field(section, "Estimated Rental Yield:|ROI:|Return:"),
                    "size": self._extract_field(section, "Total Size:|Size:"),
                    "section_type": "project_overview"
                }

                # Split into logical subsections
                subsections = {
                    "overview": section,  # Keep full overview
                    "highlights": self._extract_section(section, "Key Highlights", "Investment Benefits"),
                    "amenities": self._extract_section(section, "Amenities and Features:", "Strategic Location"),
                    "investment": self._extract_section(section, "Investment Benefits:", "Target Audience")
                }

                # Process each subsection
                for subsection_type, content in subsections.items():
                    if not content:
                        continue

                    chunk_metadata = {
                        **metadata,
                        "subsection": subsection_type,
                    }

                    processed_chunks.append(Document(
                        page_content=content,
                        metadata=chunk_metadata
                    ))

        # Create new vectorstore
        if processed_chunks:
            new_db = FAISS.from_documents(processed_chunks, self.embeddings)
            if hasattr(self, 'vectordb') and self.vectordb is not None:
                self.vectordb.merge_from(new_db)
            else:
                self.vectordb = new_db
            self.vectordb.save_local(Config.FAISS_INDEX_PATH)

    async def cleanup_old_sessions(self):
        """Clean up old session memories"""
        current_time = time.time()
        sessions_to_remove = []

        for session_id, last_access in self.last_access.items():
            if current_time - last_access > self.memory_ttl:
                sessions_to_remove.append(session_id)

        for session_id in sessions_to_remove:
            if session_id in self.memory_pools:
                del self.memory_pools[session_id]
            if session_id in self.last_access:
                del self.last_access[session_id]

    def _structure_context(self, docs: List[Document], query_type: str, project_name: str) -> str:
        """Structure context based on query type and available information"""
        if query_type == "overview":
            return self._structure_overview_context(docs)
        else:
            return self._structure_specific_context(docs, query_type, project_name)

    def _get_document_prompt(self, query_type: str) -> PromptTemplate:
        """Get appropriate document prompt based on query type"""
        if query_type == "overview":
            return PromptTemplate(
                template="Project Information:\n{page_content}\n",
                input_variables=["page_content"]
            )
        return PromptTemplate(
            template="{page_content}\n",
            input_variables=["page_content"]
        )

    def _extract_metadata(self, text: str) -> dict:
        """Extract metadata from text content"""
        metadata = {}

        # Extract project name
        project_matches = re.search(r'(?:project|title):\s*([^\n]+)', text, re.I)
        if project_matches:
            metadata['project'] = project_matches.group(1).strip()

        # Extract location
        location_matches = re.search(r'location:\s*([^\n]+)', text, re.I)
        if location_matches:
            metadata['location'] = location_matches.group(1).strip()

        # Extract price
        price_matches = re.search(r'(?:price|cost):\s*(?:PKR|Rs\.?)?\s*([\d,]+)', text, re.I)
        if price_matches:
            metadata['price'] = price_matches.group(1).strip()

        # Extract ROI
        roi_matches = re.search(r'(?:ROI|return|yield):\s*([\d.]+%)', text, re.I)
        if roi_matches:
            metadata['roi'] = roi_matches.group(1).strip()

        # Extract completion date
        completion_matches = re.search(r'(?:completion|timeline):\s*(\d{4})', text, re.I)
        if completion_matches:
            metadata['completion'] = completion_matches.group(1).strip()

        # Extract project type
        type_matches = re.search(r'type:\s*([^\n]+)', text, re.I)
        if type_matches:
            metadata['type'] = type_matches.group(1).strip()

        # Extract features
        features_section = re.search(r'features:(.*?)(?:\n\w+:|$)', text, re.I | re.S)
        if features_section:
            features = re.findall(r'[-•]\s*([^\n]+)', features_section.group(1))
            metadata['features'] = ', '.join(features) if features else None

        return metadata

    def _classify_query(self, query: str) -> str:
        """Classify query type for optimized retrieval"""
        if any(word in query for word in ['overview', 'all projects', 'summary', 'list', 'details']):
            return "overview"
        elif any(word in query for word in ['price', 'cost', 'sqft']):
            return "price"
        elif any(word in query for word in ['location', 'where']):
            return "location"
        elif any(word in query for word in ['roi', 'return', 'yield']):
            return "roi"
        elif any(word in query for word in ['complete', 'finish', 'when']):
            return "completion"
        return "general"

class FakeRetriever:
    """Helper class to use pre-retrieved documents"""
    def __init__(self, docs):
        self.docs = docs
    
    async def aget_relevant_documents(self, _):
        return self.docs
    
    def get_relevant_documents(self, _):
        return self.docs

# Create an instance of the RAG class
rag_instance = RAG()

# Define the functions to be used in routes
async def ask_question(question: str, session_id: str) -> str:
    return await rag_instance.query(question, session_id)

async def suggest_questions(context: str) -> list[str]:
    return await rag_instance.generate_questions(context)

# You can also add a function to add new texts if needed
def add_texts(texts: list[str]):
    rag_instance.add_texts(texts)
