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
            self.llm = ChatOpenAI(temperature=0, model_name='gpt-4')
            self.prompt_template = self._create_prompt_template()
            self.memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True,
                output_key="answer"
            )
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
        template = """
                    You are an expert AI assistant for DAO Proptech. Your primary goal is to provide accurate, direct information about our real estate projects.

                    **Context:** {context}

                    **Current Conversation:**
                    {chat_history}

                    **Core Guidelines:**
                    1. ALWAYS state specific information when available (locations, numbers, dates, prices)
                    2. When exact data is in the context (like locations, ROI, prices), quote it directly
                    3. Focus on facts from the documents, not general advice
                    4. If information exists in multiple documents, combine it clearly
                    5. Format numerical data consistently (use PKR for prices, % for returns)

                    **Project Information Requirements:**
                    When discussing any project, ALWAYS include if available:
                    - Exact Location
                    - ROI/Yield figures
                    - Price per sq ft
                    - Timeline/Completion date
                    - Key Features

                    **Response Format:**
                    1. Start with the most specific, factual information
                    2. Use bullet points for multiple features
                    3. Include exact quotes for important numbers/locations
                    4. Only add general statements after specific facts

                    **Human:** {question}

                    **AI Assistant:**
            """
        return PromptTemplate(template=template, input_variables=["context", "chat_history", "question"])

    async def query(self, question: str) -> str:
        try:
            # Detect if the question is asking for a table or comparison
            table_keywords = ['table', 'compare', 'comparison', 'list', 'price', 'cost', 'per']
            is_table_request = any(keyword in question.lower() for keyword in table_keywords)

            # Configure the retriever separately
            search_kwargs = {
                "k": 10 if is_table_request else 4,  # Get more context for tables
                "fetch_k": 20 if is_table_request else 8,  # Fetch more candidates
            }

            # Create retriever with MMR search type
            retriever = self.vectordb.as_retriever(
                search_type="mmr",
                search_kwargs=search_kwargs
            )

            qa_chain = ConversationalRetrievalChain.from_llm(
                llm=self.llm,
                retriever=retriever,
                memory=self.memory,
                combine_docs_chain_kwargs={"prompt": self.prompt_template},
                return_source_documents=True,
                return_generated_question=True,
                output_key="answer"
            )

            if is_table_request:
                # Enhance table-specific questions
                enhanced_question = f"""
                Create a markdown table for this request. Include ALL available data points.
                If you find numerical data in the context, you MUST include it.
                Original question: {question}
                """
                result = await qa_chain.ainvoke({"question": enhanced_question})
            else:
                result = await qa_chain.ainvoke({"question": question})

            return result['answer']
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

    async def stream_query(self, question: str):
        callback = AsyncIteratorCallbackHandler()
        streaming_llm = ChatOpenAI(
            streaming=True,
            callbacks=[callback],
            temperature=0,
            model_name='gpt-4'
        )

        qa_chain = ConversationalRetrievalChain.from_llm(
            llm=streaming_llm,
            retriever=self.vectordb.as_retriever(search_kwargs={"k": 4}),
            memory=self.memory,
            combine_docs_chain_kwargs={"prompt": self.prompt_template},
            return_source_documents=True,
            return_generated_question=True,
        )

        try:
            task = asyncio.create_task(qa_chain.ainvoke({"question": question}))
            async for token in callback.aiter():
                yield token
            await task  # Ensure the task completes
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

# Create an instance of the RAG class
rag_instance = RAG()

# Define the functions to be used in routes
async def ask_question(question: str) -> str:
    return await rag_instance.query(question)

async def suggest_questions(context: str) -> list[str]:
    return await rag_instance.generate_questions(context)

# You can also add a function to add new texts if needed
def add_texts(texts: list[str]):
    rag_instance.add_texts(texts)
