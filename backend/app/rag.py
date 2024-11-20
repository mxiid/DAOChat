# LangChain Core
from langchain_core.documents import Document
from langchain.schema import HumanMessage, SystemMessage

# LangChain Components
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from langchain.callbacks import AsyncIteratorCallbackHandler

# Vector Store
from langchain_community.vectorstores import FAISS

# Python Standard Library
import os
import logging
import asyncio
from typing import List, Optional, AsyncGenerator
import re
from datetime import datetime
import uuid

# OpenAI
from openai import OpenAIError, APIError, RateLimitError

# Async LRU Cache
from async_lru import alru_cache

# Configuration
from .config import Config

# Setup logging
logger = logging.getLogger(__name__)

# Tiktoken
import tiktoken

# FastAPI
from fastapi import HTTPException

# Monitoring
from .monitoring import ChatMonitoring

# Models
from .models import ChatMessage

# Database
from .database import SessionLocal, Base, engine

# Create tables
Base.metadata.create_all(bind=engine)

class RAG:
    def __init__(self, model_name: str = 'gpt-4o-mini', memory_ttl: int = 1800, db_session=None):
        try:
            # Add database session
            self.db = db_session
            
            # Initialize tokenizer with updated limits for gpt-4o-mini
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
            self.max_context_tokens = 128000  # 128K context window
            self.max_output_tokens = 16000    # 16K output tokens

            # Define system message
            self.system_message = """You are DAO Proptech's expert AI investment advisor, specializing in real estate investment opportunities. You combine the precision of a wealth manager with the warmth of a trusted advisor.

            **Investment Portfolio:**

            1. Urban Dwellings (Bahria Garden City, Rawalpindi)
            - Mixed-Use | Completion: 2028 | ROI: 30-40% annually
            - First tokenized underground skyscraper, smart apartments
            - Token: PKR 16,000/sq.ft., 737,633 sq.ft. total

            2. Elements Residencia (Bahria Town Phase 8, Rawalpindi)
            - Mixed-Use | Completion: 2026 | ROI: 30-40% annually
            - Furnished serviced apartments, premium amenities
            - Token: PKR 17,000/sq.ft., 215,000 sq.ft. total

            3. Globe Residency (Naya Nazimabad, Karachi)
            - Residential | Completion: 2025 | ROI: 15-25% annually
            - 1,344 units across 9 towers, complete community
            - Token: PKR 10,000/sq.ft.

            4. Broad Peak Realty (DHA 1, Rawalpindi)
            - Co-working | Completion: 2025 | ROI: 5% rental yield
            - 380+ seats, premium business facilities
            - Token: PKR 35,000/sq.ft., 21,000 sq.ft.

            5. Akron (Bahria Town Phase 7, Rawalpindi)
            - Co-working | Completed 2021 | ROI: 5% rental yield
            - 100+ seats, modern workspace
            - Token: PKR 27,500/sq.ft., 8,200 sq.ft.

            6. Qube 101 (Divine Gardens, Lahore)
            - Co-working | Completed 2022 | ROI: 5% rental yield
            - 100+ seats, modern workspace
            - Token: PKR 28,000/sq.ft., 10,000 sq.ft.

            7. Amna Homes (Sector D1, DHA Bahawalpur)
            - Residential | Completed 2027 | ROI: 2% rental yield
            - 333 villas, premium amenities
            - Token: PKR 9,200/sq.ft., 1,000 sq.ft.

            **Core Guidelines:**

            1. **Knowledge Base:** Use provided project details and general real estate knowledge only
            2. **Consistency:** Maintain accuracy across responses, express uncertainty when needed
            3. **Format:** Use clear Markdown formatting, tables for comparisons, bullet points for clarity
            4. **Project Details:** Always include ROI, location, type, timeline, features, and investment metrics
            5. **Value Focus:** Emphasize tokenization, fractional ownership, and returns
            6. **Engagement:** Use natural conversation flow, ask relevant follow-up questions
            7. **Problem Solving:** Provide concise summaries first, then details upon interest
            8. **Innovation:** Highlight blockchain technology and modern investment approaches
            9. Provide equally detailed responses about DAO PropTech's offerings in English or Urdu/Roman Urdu, maintaining consistency and using relevant Pakistani real estate terminology while adapting language to match the query while also pertaining to DAO PropTech and it's processes.
            10. **Balanced Perspective:** When discussing potential challenges or disadvantages:
                - Acknowledge legitimate concerns transparently
                - Explain how DAO PropTech addresses these challenges
                - Highlight the safeguards and solutions in place
                - Frame challenges as opportunities for growth
                - Emphasize the long-term benefits that outweigh short-term concerns

            **Response Structure:**
            - Start with direct answers to queries
            - Support with specific project examples
            - Include relevant metrics and data
            - End with thoughtful, engaging questions
            - Keep responses focused and value-driven
            - Redirect unrelated queries to relevant offerings
            - Maintain professional yet warm tone
            - Match query language style (English/Urdu), use local real estate terms, include PKR values, and provide culturally relevant context for DAO PropTech and it's projects.


            Remember: Your goal is to inform and guide investors toward confident decisions about DAO Proptech's innovative real estate opportunities."""

            self.embeddings = OpenAIEmbeddings()
            self.vectordb = self._load_vectordb()

            # Initialize LLMs with proper configurations for gpt-4o-mini
            self.streaming_llm = ChatOpenAI(
                temperature=0,
                model_name=model_name,
                streaming=True,
                max_tokens=self.max_output_tokens,  # Allow for maximum output
                request_timeout=60  # Increased timeout for larger responses
            )

            # Session management
            self.memory_pools = {}
            self.memory_ttl = memory_ttl
            self.last_access = {}

            # Concurrency control
            self.request_semaphore = asyncio.Semaphore(50)

            # Start cleanup task
            self.cleanup_task = asyncio.create_task(self._run_periodic_cleanup())

            # Add session tracking
            self.active_sessions = set()

        except Exception as e:
            logger.exception("Error initializing RAG")
            raise

    def _load_vectordb(self):
        """Load the existing vector store"""
        try:
            if os.path.exists(Config.FAISS_INDEX_PATH):
                vectordb = FAISS.load_local(
                    Config.FAISS_INDEX_PATH, 
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
                logger.info(f"Loaded existing FAISS index from {Config.FAISS_INDEX_PATH}")
                return vectordb
            else:
                raise FileNotFoundError(f"FAISS index not found at {Config.FAISS_INDEX_PATH}")
        except Exception as e:
            logger.error(f"Error loading vector store: {str(e)}")
            raise

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
            # Get or create memory for this session
            memory = self._get_or_create_memory(session_id)
            self.last_access[session_id] = datetime.now().timestamp()

            # Get relevant documents
            query_type = self._classify_query(question.lower())
            project_name = self._extract_project_name(question)
            docs = await self._get_relevant_documents(question, query_type, project_name)

            # Format context
            context = self._format_project_response(docs) if project_name else self._format_general_response(docs)

            # Create messages
            messages = [
                SystemMessage(content=self.system_message),
                *memory.chat_memory.messages[-4:],  # Include last 2 turns
                HumanMessage(
                    content=f"""Based on the following information:

                    Context:
                    {context}

                    Question: {question}

                    Please provide a clear, specific answer focusing on the relevant details."""
                    )
            ]

            # Get response
            response = await self.llm.apredict_messages(messages)

            # Update memory
            memory.chat_memory.add_user_message(question)
            memory.chat_memory.add_ai_message(response.content)

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

    @ChatMonitoring.track_request
    async def stream_query(self, question: str, session_id: str):
        """Process and stream responses with proper session management"""
        if session_id not in self.active_sessions:
            logger.warning(f"Invalid session ID: {session_id}")
            yield "Session expired. Please start a new conversation."
            return

        async with self.request_semaphore:
            try:
                # Get or create memory
                memory = self._get_or_create_memory(session_id)
                self.last_access[session_id] = datetime.now().timestamp()

                # For very short queries, we'll use a simplified context
                if len(question.split()) <= 1:
                    messages = [
                        SystemMessage(content=self.system_message),
                        *memory.chat_memory.messages[-10:],  # Include conversation history
                        HumanMessage(content=question)
                    ]
                else:
                    # Regular query processing with full context
                    query_type = self._classify_query(question.lower())
                    project_name = self._extract_project_name(question)
                    docs = await self._get_relevant_documents(question, query_type, project_name)

                    context = self._format_project_response(docs) if project_name else "\n\n".join(
                        f"- {doc.page_content}" for doc in docs
                    )

                    messages = [
                        SystemMessage(content=self.system_message),
                        *memory.chat_memory.messages[-10:],
                        HumanMessage(content=f"""Based on this context:
{context}

Question: {question}

Please provide a clear, specific answer focusing on the relevant details.""")
                    ]

                # Stream response with error handling
                collected_response = []
                try:
                    async for chunk in self.streaming_llm.astream(messages):
                        if hasattr(chunk, 'content') and chunk.content:
                            collected_response.append(chunk.content)
                            yield chunk.content

                    # Update memory with complete response
                    if collected_response:
                        full_response = ''.join(collected_response)
                        memory.chat_memory.add_user_message(question)
                        memory.chat_memory.add_ai_message(full_response)

                    # Store message in database
                    await self.db.execute(
                        ChatMessage(
                            session_id=session_id,
                            role='user',
                            content=question,
                            tokens=len(question.split())  # Simple approximation
                        )
                    )

                    # Store bot response
                    if collected_response:
                        await self.db.execute(
                            ChatMessage(
                                session_id=session_id,
                                role='bot',
                                content=full_response,
                                tokens=len(full_response.split())
                            )
                        )

                except Exception as e:
                    logger.error(f"Streaming error: {str(e)}")
                    yield "\nI apologize, but I encountered an error while generating the response."

            except Exception as e:
                logger.exception("Error in stream_query")
                yield "I apologize, but I encountered an error processing your request."

    async def _run_periodic_cleanup(self):
        """Run periodic cleanup of old sessions"""
        while True:
            try:
                await self.cleanup_old_sessions()
                await asyncio.sleep(300)  # Run every 5 minutes
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {str(e)}")
                await asyncio.sleep(60)  # Wait a minute before retrying

    async def cleanup_old_sessions(self):
        """Clean up old session memories"""
        current_time = datetime.now().timestamp()
        sessions_to_remove = []

        async with self.request_semaphore:
            for session_id in self.active_sessions.copy():
                if current_time - self.last_access.get(session_id, 0) > self.memory_ttl:
                    sessions_to_remove.append(session_id)

            for session_id in sessions_to_remove:
                await self._remove_session(session_id)
                logger.info(f"Cleaned up session: {session_id}")

    async def _remove_session(self, session_id: str):
        """Safely remove a session and its associated data"""
        try:
            self.active_sessions.discard(session_id)
            self.memory_pools.pop(session_id, None)
            self.last_access.pop(session_id, None)
            logger.info(f"Removed session: {session_id}")
        except Exception as e:
            logger.error(f"Error removing session {session_id}: {str(e)}")

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

    def _get_or_create_memory(self, session_id: str) -> ConversationBufferMemory:
        """Get or create a conversation memory for a session"""
        logger.info(f"Accessing memory for session: {session_id}")
        logger.info(f"Current active sessions: {list(self.memory_pools.keys())}")

        if session_id not in self.memory_pools:
            logger.info(f"Creating new memory for session: {session_id}")
            self.memory_pools[session_id] = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True,
                output_key="answer"
            )
            self.last_access[session_id] = datetime.now().timestamp()
        return self.memory_pools[session_id]

    async def _get_relevant_documents(self, question: str, query_type: str, project_name: Optional[str] = None) -> List[Document]:
        """Get relevant documents with caching"""
        try:
            logger.info(f"Searching for: Project={project_name}, Query={question}")

            if project_name:
                # Simple similarity search for the specific project
                docs = self.vectordb.similarity_search(
                    question,
                    k=4,  # Get top 4 results
                )
                logger.info(f"Found {len(docs)} documents for {project_name}")
                return docs
            else:
                # General search
                docs = self.vectordb.similarity_search(
                    question,
                    k=4
                )
                logger.info(f"Found {len(docs)} documents for general query")
                return docs

        except Exception as e:
            logger.error(f"Error retrieving documents: {str(e)}", exc_info=True)
            return []

    async def create_session(self) -> str:
        """Create a new session and return its ID"""
        session_id = str(uuid.uuid4())
        self.active_sessions.add(session_id)
        self.memory_pools[session_id] = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key="answer"
        )
        self.last_access[session_id] = datetime.now().timestamp()
        logger.info(f"Created new session: {session_id}")
        return session_id

# Create an instance of the RAG class with database session
def get_rag_instance():
    db = SessionLocal()
    try:
        return RAG(db_session=db)
    finally:
        db.close()

rag_instance = get_rag_instance()

# Define the functions to be used in routes
async def create_chat_session() -> str:
    """Create a new chat session"""
    return await rag_instance.create_session()

async def ask_question(question: str, session_id: str):
    """Handle questions with session validation"""
    if session_id not in rag_instance.active_sessions:
        yield "Session expired. Please start a new conversation."
        return
        
    async for chunk in rag_instance.stream_query(question, session_id):
        yield chunk

async def suggest_questions(context: str) -> list[str]:
    return await rag_instance.generate_questions(context)
