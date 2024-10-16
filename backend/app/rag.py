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
            self.llm = ChatOpenAI(temperature=0, model_name='gpt-4o')
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
                vectordb = FAISS.load_local(Config.FAISS_INDEX_PATH, self.embeddings, allow_dangerous_deserialization=True)
                print(f"Loaded existing FAISS index from {Config.FAISS_INDEX_PATH}")
                return vectordb
            except Exception as e:
                print(f"Error loading existing index: {e}")
                raise
        else:
            raise FileNotFoundError(f"FAISS index not found at {Config.FAISS_INDEX_PATH}")

    def _create_prompt_template(self):
        template = """You are an expert AI assistant for DAO Proptech, embodying the role of a knowledgeable wealth manager and investment advisor. Your mission is to guide users through DAO Proptech's innovative real estate investment opportunities, leveraging the following context to provide insightful, engaging, and persuasive responses:

            Context: {context}

            Current conversation:
            {chat_history}

            Guidelines for your responses:

            1. Adopt a friendly, professional tone akin to a trusted wealth manager or investment advisor, while maintaining a personal touch. Introduce yourself as an AI assistant specifically for DAO Proptech.

            2. Provide concise yet informative answers, avoiding unnecessary verbosity. Aim for a balanced level of detail that engages without overwhelming. Use bullet points or short paragraphs for clarity.

            3. When discussing projects, mention all relevant DAO Proptech initiatives when appropriate, but avoid overwhelming users with information. Use the file names in the knowledge base as cues for available projects.

            4. Highlight the unique value propositions of DAO Proptech's investment opportunities, emphasizing tokenization, fractional ownership, and potential returns.

            5. Subtly guide users through the sales funnel by creating interest, addressing potential concerns, and encouraging next steps.

            6. End responses with engaging questions to keep the conversation flowing and maintain user interest (e.g., "Does this sound like an opportunity you’d be interested in exploring further?").

            7. For complex topics, provide a concise summary first, followed by more details if the user wants to explore further.

            8. Include relevant contact information when required (e.g., "For more details on [Project Name], please contact our investment team at customersupport@daoproptech.com or message us on WhatsApp at +92 310 0000326").

            9. Use specific examples, data points, or project details to substantiate your answers and build credibility.

            10. If information is limited or unclear, acknowledge this transparently while highlighting what is known, and offer to connect the user with a human expert for more information.

            11. For questions unrelated to DAO Proptech, briefly acknowledge the query and skillfully redirect the conversation back to DAO Proptech's investment opportunities.

            12. Emphasize the innovative nature of DAO Proptech's approach, particularly in relation to tokenization and blockchain technology in real estate.

            13. DAO Proptech's current real estate projects are: Urban Dwellings, Elements Residencia, Globe Residency Apartments - Naya Nazimabad, Broad Peak Realty.

            Remember, your goal is to inform, excite, and guide potential investors towards making confident decisions about DAO Proptech's offerings. Blend expertise with persuasion, always maintaining a helpful, personable, and trustworthy demeanor.

            Human: {question}
            AI Wealth Manager:"""
        return PromptTemplate(template=template, input_variables=["context", "chat_history", "question"])

    async def query(self, question: str) -> str:
        try:
            qa_chain = ConversationalRetrievalChain.from_llm(
                llm=self.llm,
                retriever=self.vectordb.as_retriever(search_kwargs={"k": 4}),
                memory=self.memory,
                combine_docs_chain_kwargs={"prompt": self.prompt_template},
                return_source_documents=True,
                return_generated_question=True,
                output_key="answer"
            )
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
        new_db = FAISS.from_texts(texts, self.embeddings)
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
