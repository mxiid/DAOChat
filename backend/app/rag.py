from langchain.llms import OpenAI
from langchain.chains import RetrievalQA
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Milvus

from .config import Config
from .vector_store import VectorStore

class RAG:
    def __init__(self):
        self.vector_store = VectorStore()
        self.embeddings = OpenAIEmbeddings(openai_api_key=Config.OPENAI_API_KEY)
        self.vectorstore = Milvus(
            embedding_function=self.embeddings,
            collection_name=self.vector_store.collection_name,
            connection_args={"host": Config.MILVUS_HOST, "port": Config.MILVUS_PORT}
        )
        self.llm = OpenAI(temperature=0, openai_api_key=Config.OPENAI_API_KEY)
        self.qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.vectorstore.as_retriever()
        )

    def answer_question(self, question):
        return self.qa_chain.run(question)

    # Add methods for adding documents, updating the vector store, etc.
