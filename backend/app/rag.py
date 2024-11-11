from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, CSVLoader
from langchain.schema import HumanMessage
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
            self.llm = ChatOpenAI(
                temperature=0, 
                model_name='gpt-4o',
                system_message="""You are an expert AI assistant for DAO Proptech, acting as a knowledgeable wealth manager and investment advisor. Your mission is to guide users through DAO Proptech's innovative real estate investment opportunities, using the provided DAO whitepapers, documents, and context to deliver insightful, engaging, and persuasive responses.

                Important Guidelines:
                - Use only the provided documents to answer questions and offer insights
                - Supplement with general knowledge only when it aligns directly with concepts in the documents
                - Ensure responses are accurate, logical, and consistent
                - If unsure, express uncertainty gracefully and offer to connect with a human expert
                - Focus on DAO Proptech's current projects:
                    - Urban Dwellings
                    - Elements Residencia
                    - Globe Residency Apartments - Naya Nazimabad
                    - Broad Peak Realty
                    - Akron
                
                When presenting project details, always include:
                - ROI Figures
                - Location
                - Project Type
                - Timeline
                - Key Features
                - Investment Metrics"""
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
            # Get or create session-specific memory
            if session_id not in self.memory_pools:
                self.memory_pools[session_id] = ConversationBufferMemory(
                    memory_key="chat_history",
                    return_messages=True,
                    output_key="answer"
                )

            # Update last access time
            self.last_access[session_id] = time.time()

            memory = self.memory_pools[session_id]

            # Create the chain with the session-specific memory
            qa_chain = ConversationalRetrievalChain.from_llm(
                llm=self.llm,
                retriever=self.vectordb.as_retriever(
                    search_type="mmr",
                    search_kwargs={"k": 4, "fetch_k": 8}
                ),
                memory=memory,
                combine_docs_chain_kwargs={"prompt": self.prompt_template},
                return_source_documents=True,
                return_generated_question=True,
                output_key="answer"
            )

            result = await qa_chain.ainvoke({"question": question})
            return result['answer']

        except Exception as e:
            logger.error(f"Error in _process_request method: {str(e)}", exc_info=True)
            raise

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
                model_name='gpt-4o',
                system_message=self.llm.system_message  # Use the same system message
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

            # Create messages for the chat
            messages = [HumanMessage(content=formatted_prompt)]

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
        # Create text splitter with smaller chunks and more overlap for numerical data
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,  # Smaller chunks to keep related data together
            chunk_overlap=100,  # More overlap to maintain context
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

        # Split texts into chunks
        chunks = text_splitter.split_text('\n'.join(texts))

        # Create and merge the new vectorstore
        new_db = FAISS.from_texts(chunks, self.embeddings)
        self.vectordb.merge_from(new_db)
        self.vectordb.save_local(Config.FAISS_INDEX_PATH)
        print(f"Added {len(texts)} new documents to the FAISS index")

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
