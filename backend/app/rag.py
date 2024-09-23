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

logger = logging.getLogger(__name__)

class RAG:
    def __init__(self):
        try:
            self.embeddings = OpenAIEmbeddings()
            self.vectordb = self._create_or_load_vectordb()
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

    def _create_or_load_vectordb(self):
        if os.path.exists(Config.FAISS_INDEX_PATH):
            try:
                vectordb = FAISS.load_local(Config.FAISS_INDEX_PATH, self.embeddings, allow_dangerous_deserialization=True)
                print(f"Loaded existing FAISS index from {Config.FAISS_INDEX_PATH}")
                return vectordb
            except Exception as e:
                print(f"Error loading existing index: {e}")
                print("Creating new index...")

        # If loading fails or index doesn't exist, create a new one
        documents = []
        for filename in os.listdir(Config.DOCUMENTS_PATH):
            file_path = os.path.join(Config.DOCUMENTS_PATH, filename)
            if filename.endswith('.pdf'):
                loader = PyPDFLoader(file_path)
                documents.extend(loader.load())
            elif filename.endswith('.csv'):
                loader = CSVLoader(file_path)
                documents.extend(loader.load())

        if not documents:
            raise ValueError(f"No PDF or CSV documents found in {Config.DOCUMENTS_PATH}")
        
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        texts = text_splitter.split_documents(documents)
        if not texts:
            raise ValueError("No text chunks created from documents")
        
        vectordb = FAISS.from_documents(texts, self.embeddings)
        vectordb.save_local(Config.FAISS_INDEX_PATH)
        print(f"Created new FAISS index at {Config.FAISS_INDEX_PATH}")
        return vectordb

    def _create_prompt_template(self):
        template = """You are a knowledgeable AI assistant for DAO Proptech, specializing in real estate investments. Use the following pieces of context to answer the human's question. If you don't know the answer, just say that you don't know, don't try to make up an answer.

        Context: {context}

        Current conversation:
        {chat_history}
        Human: {question}
        AI Assistant: """
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
                output_key="answer"  # Add this line
            )
            result = await qa_chain.ainvoke({"question": question})
            return result['answer']
        except openai.error.APIConnectionError as e:
            logger.error(f"OpenAI API connection error: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="OpenAI API connection error. Please try again later.")
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

    def add_texts(self, texts: list[str]):
        new_db = FAISS.from_texts(texts, self.embeddings)
        self.vectordb.merge_from(new_db)
        self.vectordb.save_local(Config.FAISS_INDEX_PATH)
        print(f"Added {len(texts)} new documents to the FAISS index")
