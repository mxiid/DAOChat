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
from .models import ChatMessage, ChatSession

# Database
from .database import SessionLocal, Base, engine
from sqlalchemy import select


class RAG:
    def __init__(
        self, model_name: str = "gpt-4o-mini", memory_ttl: int = 1800, db_session=None
    ):
        try:
            # Store the session factory instead of a session
            self.db_session = SessionLocal

            # Initialize tokenizer with updated limits for gpt-4o-mini
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
            self.max_context_tokens = 128000  # 128K context window
            self.max_output_tokens = 16000  # 16K output tokens

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
            - Match query language style (English/Roman Urdu)), use local real estate terms, include PKR values, and provide culturally relevant context for DAO PropTech and it's projects.

            **Contact Details:**
            - Email: info@daoproptech.com
            - Phone: +92 310 0000326
            - Website: https://daoproptech.com
            - Office Address: 17-A, Business Bay, Sector F, DHA-1, Islamabad, Pakistan

            Remember: Your goal is to inform and guide investors toward confident decisions about DAO Proptech's innovative real estate opportunities."""

            self.embeddings = OpenAIEmbeddings()
            self.vectordb = self._load_vectordb()

            # Initialize LLMs with proper configurations for gpt-4o-mini
            self.llm = ChatOpenAI(
                temperature=0,
                model_name=model_name,
                streaming=False,
                max_tokens=self.max_output_tokens,
            )

            self.streaming_llm = ChatOpenAI(
                temperature=0,
                model_name=model_name,
                streaming=True,
                max_tokens=self.max_output_tokens,
                request_timeout=60,
            )

            # Add a lock for thread-safe session management
            self._session_lock = asyncio.Lock()

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
                    allow_dangerous_deserialization=True,
                )
                logger.info(
                    f"Loaded existing FAISS index from {Config.FAISS_INDEX_PATH}"
                )
                return vectordb
            else:
                raise FileNotFoundError(
                    f"FAISS index not found at {Config.FAISS_INDEX_PATH}"
                )
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
        return PromptTemplate(
            template=template, input_variables=["context", "chat_history", "question"]
        )

    async def _process_request(self, question: str, session_id: str):
        try:
            # Get or create memory for this session
            memory = self._get_or_create_memory(session_id)
            self.last_access[session_id] = datetime.now().timestamp()

            # Get relevant documents
            query_type = self._classify_query(question.lower())
            project_name = self._extract_project_name(question)
            docs = await self._get_relevant_documents(
                question, query_type, project_name
            )

            # Format context
            context = (
                self._format_project_response(docs)
                if project_name
                else self._format_general_response(docs)
            )

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
                ),
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
            "general": "highlights",
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
        key_fields = ["location", "price_sqft", "roi", "completion_year", "type"]
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
            "akron": "Akron",
        }

        if not query:
            return None

        query_lower = query.lower()
        for key, value in project_mapping.items():
            if key in query_lower:
                return value
        return None

    def _get_project_names(self) -> dict:
        """Get all project names mapping"""
        return {
            "urban dwellings": "Urban Dwellings",
            "elements residencia": "Elements Residencia",
            "globe residency": "Globe Residency Apartments",
            "broad peak": "Broad Peak Realty",
            "akron": "Akron",
        }

    async def generate_questions(self, context: str) -> list[str]:
        try:
            prompt = f"Based on the following context, generate a list of relevant questions:\n\nContext: {context}\n\nQuestions:"
            response = await self.llm.agenerate(prompt)  # Pass the prompt as a string
            questions = response.generations[0][0].text.strip().split("\n")
            return [q.strip() for q in questions if q.strip()]
        except openai.error.APIConnectionError as e:
            logger.error(f"OpenAI API connection error: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail="OpenAI API connection error. Please try again later.",
            )
        except Exception as e:
            logger.error(f"Error in generate_questions method: {str(e)}", exc_info=True)
            raise

    def _format_markdown(self, text: str) -> str:
        """Ensure consistent markdown formatting while preserving tables"""
        # Split text into sections (tables and non-tables)
        sections = re.split(r"(\|.*\|.*(?:\r?\n\|.*\|.*)*)", text)

        formatted_sections = []
        for section in sections:
            # If this is a table section, preserve it exactly
            if section.strip().startswith("|") and section.strip().endswith("|"):
                formatted_sections.append(section)
            else:
                # Apply formatting to non-table sections
                formatted = section
                # Fix bullet points
                formatted = re.sub(r"(?m)^[•*+-]\s+", "- ", formatted)
                # Fix headings (ensure space after #)
                formatted = re.sub(r"(?m)^(#{1,6})([^ #])", r"\1 \2", formatted)
                # Fix bold text (ensure consistent ** usage)
                formatted = re.sub(
                    r"(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)", r"**\1**", formatted
                )
                # Fix lists (ensure proper spacing)
                formatted = re.sub(r"(?m)^(\d+\.)\s*", r"\1 ", formatted)
                # Fix line breaks (ensure consistent spacing)
                formatted = re.sub(r"\n{3,}", "\n\n", formatted)
                formatted_sections.append(formatted)

        return "".join(formatted_sections).strip()

    @ChatMonitoring.track_request
    async def stream_query(self, question: str, session_id: str):
        """Process and stream responses with proper session management"""
        if not question or not question.strip():
            async def empty_response():
                yield "I couldn't understand your question. Could you please rephrase it?"
            return empty_response()

        if session_id not in self.active_sessions:
            logger.warning(f"Invalid session ID: {session_id}")
            async def error_gen():
                yield "Session expired. Please start a new conversation."
            return error_gen()

        async with self.request_semaphore:
            try:
                # Get or create memory
                memory = self._get_or_create_memory(session_id)
                self.last_access[session_id] = datetime.now().timestamp()

                # Process query and get messages
                messages = await self._prepare_messages(question, memory)

                # Create and return the async generator
                async def response_generator():
                    collected_response = []
                    try:
                        async for chunk in self.streaming_llm.astream(messages):
                            if hasattr(chunk, 'content') and chunk.content:
                                if isinstance(chunk.content, str) and chunk.content.strip():
                                    collected_response.append(chunk.content)
                                    yield chunk.content
                                else:
                                    logger.warning(f"Invalid chunk content: {chunk.content}")

                        # If no valid response was collected
                        if not collected_response:
                            yield "I apologize, but I couldn't generate a proper response. Please try again."
                            return

                        # Update memory and store in database after completion
                        await self._update_conversation_history(
                            session_id, 
                            question, 
                            collected_response, 
                            memory
                        )
                    except Exception as e:
                        logger.error(f"Error in response generation: {str(e)}")
                        yield "I encountered an error while processing your request. Please try again."

                return response_generator()

            except Exception as e:
                logger.exception("Error in stream_query")
                async def error_gen():
                    yield "I apologize, but I encountered an error processing your request."
                return error_gen()

    async def _prepare_messages(self, question: str, memory):
        """Prepare messages for the conversation"""
        # Get relevant documents from RAG
        docs = await self._get_relevant_documents(question, self._classify_query(question.lower()))
        
        # Format context from relevant documents
        context = "\n\n".join(f"{doc.page_content}" for doc in docs)
        
        # Include only recent conversation history (last 2 turns)
        recent_messages = memory.chat_memory.messages[-4:] if memory.chat_memory.messages else []
        
        return [
            SystemMessage(content=self.system_message),
            *recent_messages,
            HumanMessage(content=f"""Based on this context:
{context}

Question: {question}

Please provide a clear, specific answer focusing on the relevant details.""")
        ]

    async def _update_conversation_history(
        self, session_id, question, collected_response, memory
    ):
        """Update conversation history and database"""
        if collected_response:
            full_response = "".join(collected_response)
            memory.chat_memory.add_user_message(question)
            memory.chat_memory.add_ai_message(full_response)

            async with self.db_session() as session:
                try:
                    # Verify session exists and update last activity
                    chat_session = await session.execute(
                        select(ChatSession).where(ChatSession.id == session_id)
                    )
                    chat_session = chat_session.scalar_one_or_none()

                    if not chat_session:
                        logger.error(f"Session {session_id} not found in database")
                        raise ValueError("Invalid session ID")

                    # Update session last activity
                    chat_session.last_activity = datetime.utcnow()
                    await session.commit()

                except Exception as e:
                    await session.rollback()
                    logger.error(f"Database error: {str(e)}")
                    raise

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
        """Clean up old session memories but keep database records"""
        current_time = datetime.now().timestamp()
        sessions_to_remove = []

        async with self.request_semaphore:
            for session_id in self.active_sessions.copy():
                if current_time - self.last_access.get(session_id, 0) > self.memory_ttl:
                    sessions_to_remove.append(session_id)

            for session_id in sessions_to_remove:
                await self._remove_session(session_id)
                logger.info(f"Cleaned up session memory: {session_id}")

    async def _remove_session(self, session_id: str):
        """Safely remove a session with proper locking"""
        async with self._session_lock:
            try:
                self.active_sessions.discard(session_id)
                if session_id in self.memory_pools:
                    self.memory_pools[
                        session_id
                    ].clear()  # Clear memory before removing
                    self.memory_pools.pop(session_id, None)
                self.last_access.pop(session_id, None)
                logger.info(f"Removed session from memory: {session_id}")
            except Exception as e:
                logger.error(f"Error removing session {session_id}: {str(e)}")

    def _extract_metadata(self, text: str) -> dict:
        """Extract metadata from text content"""
        metadata = {}

        # Extract project name
        project_matches = re.search(r"(?:project|title):\s*([^\n]+)", text, re.I)
        if project_matches:
            metadata["project"] = project_matches.group(1).strip()

        # Extract location
        location_matches = re.search(r"location:\s*([^\n]+)", text, re.I)
        if location_matches:
            metadata["location"] = location_matches.group(1).strip()

        # Extract price
        price_matches = re.search(
            r"(?:price|cost):\s*(?:PKR|Rs\.?)?\s*([\d,]+)", text, re.I
        )
        if price_matches:
            metadata["price"] = price_matches.group(1).strip()

        # Extract ROI
        roi_matches = re.search(r"(?:ROI|return|yield):\s*([\d.]+%)", text, re.I)
        if roi_matches:
            metadata["roi"] = roi_matches.group(1).strip()

        # Extract completion date
        completion_matches = re.search(
            r"(?:completion|timeline):\s*(\d{4})", text, re.I
        )
        if completion_matches:
            metadata["completion"] = completion_matches.group(1).strip()

        # Extract project type
        type_matches = re.search(r"type:\s*([^\n]+)", text, re.I)
        if type_matches:
            metadata["type"] = type_matches.group(1).strip()

        # Extract features
        features_section = re.search(r"features:(.*?)(?:\n\w+:|$)", text, re.I | re.S)
        if features_section:
            features = re.findall(r"[-•]\s*([^\n]+)", features_section.group(1))
            metadata["features"] = ", ".join(features) if features else None

        return metadata

    def _classify_query(self, query: str) -> str:
        """Classify query type for optimized retrieval"""
        if any(
            word in query
            for word in ["overview", "all projects", "summary", "list", "details"]
        ):
            return "overview"
        elif any(word in query for word in ["price", "cost", "sqft"]):
            return "price"
        elif any(word in query for word in ["location", "where"]):
            return "location"
        elif any(word in query for word in ["roi", "return", "yield"]):
            return "roi"
        elif any(word in query for word in ["complete", "finish", "when"]):
            return "completion"
        return "general"

    def _get_or_create_memory(self, session_id: str) -> ConversationBufferMemory:
        """Get or create a conversation memory for a session"""
        if session_id not in self.memory_pools:
            logger.info(f"Creating new memory for session: {session_id}")
            memory = ConversationBufferMemory(
                memory_key="chat_history", return_messages=True, output_key="answer"
            )
            memory.clear()
            self.memory_pools[session_id] = memory
            self.last_access[session_id] = datetime.now().timestamp()

        return self.memory_pools[session_id]

    async def _get_relevant_documents(
        self, question: str, query_type: str
    ) -> List[Document]:
        """Get relevant documents with caching"""
        try:
            logger.info(f"Searching for query: {question}")
            docs = self.vectordb.similarity_search(question, k=4)  # Get top 4 results
            logger.info(f"Found {len(docs)} relevant documents")
            return docs
        except Exception as e:
            logger.error(f"Error retrieving documents: {str(e)}", exc_info=True)
            return []

    async def create_session(self, session_id: Optional[str] = None) -> str:
        """Create a new session with proper locking"""
        async with self._session_lock:
            if session_id is None:
                session_id = str(uuid.uuid4())

            # Create fresh memory for new session
            memory = ConversationBufferMemory(
                memory_key="chat_history", return_messages=True, output_key="answer"
            )
            memory.clear()  # Ensure memory is empty

            # Add to active sessions
            self.active_sessions.add(session_id)
            self.memory_pools[session_id] = memory
            self.last_access[session_id] = datetime.now().timestamp()

            logger.info(f"Created new session with clean memory: {session_id}")
            return session_id


# Create an instance of the RAG class with database session
def get_rag_instance():
    return RAG()  # No need to pass db_session anymore


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
