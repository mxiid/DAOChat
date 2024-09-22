from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA
from langchain_openai import OpenAIEmbeddings, OpenAI
from langchain.vectorstores import FAISS
from .config import Config

class RAG:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(openai_api_key=Config.OPENAI_API_KEY)
        self.llm = OpenAI(temperature=0, openai_api_key=Config.OPENAI_API_KEY)
        self.qa_chain = self._create_qa_chain()

    def _create_qa_chain(self):
        try:
            vector_store = FAISS.load_local(Config.FAISS_INDEX_PATH, self.embeddings)
            print(f"Loaded existing FAISS index from {Config.FAISS_INDEX_PATH}")
        except:
            vector_store = FAISS.from_texts(["Initial document"], self.embeddings)
            vector_store.save_local(Config.FAISS_INDEX_PATH)
            print(f"Created new FAISS index at {Config.FAISS_INDEX_PATH}")

        prompt_template = PromptTemplate(
            template="""You are a knowledgeable AI assistant for DAO Proptech, acting as a wealth manager and a sales representative to guide users through our investment offerings. Your task is to provide clear, concise, yet informative answers based on the following context:

            {context}

            Guidelines for answering:
            1. Keep the responses suitable for a chat bubble display.
            2. Focus on the most relevant information to directly answer the question.
            3. Use bullet points or short paragraphs for easy readability.
            4. If a complex topic requires a longer explanation, offer a concise summary and ask if the user would like more details.
            5. For investment-related questions, briefly mention key factors like potential returns, risks, and alignment with DAO Proptech's goals.
            6. Use specific examples or data points when they significantly enhance the answer without making it too long.
            7. Include relevant contact information only when directly applicable to the user's query or when they explicitly ask for it. Use the following details as appropriate:
            - Email: info@daoproptech.com
            - Phone: +923143267767
            - Website: https://daoproptech.com
            - Platform: https://id.daoproptech.com
            - Urban Dwellings: https://daoproptech.com/urban-dwellings/
            8. Subtly guide users through the sales and marketing funnel, building trust while creating urgency.
            9. Emphasize the value and potential of high-ticket items, such as tokenized real estate (expected ticket price: $2,500).
            10. If you don't have enough information to answer, briefly explain what you know and what's unclear.
            11. If the question is unrelated to DAO Proptech, politely redirect the user to ask about DAO Proptech investment opportunities.

            Remember, your goal is to increase user confidence in DAO Proptech's offerings and guide them towards making informed investment decisions. Provide contact information or links only when directly relevant to the user's query or when explicitly requested.

            Human: {question}
            AI Assistant: Let me provide a concise and informative answer based on the information available:""",
            input_variables=["context", "question"]
        )

        return RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=vector_store.as_retriever(search_kwargs={"k": 4}),
            return_source_documents=True,
            chain_type_kwargs={"prompt": prompt_template}
        )

    def query(self, question: str) -> str:
        result = self.qa_chain({"query": question})
        return result["result"]

    def add_texts(self, texts: list[str]):
        vector_store = FAISS.load_local(Config.FAISS_INDEX_PATH, self.embeddings)
        vector_store.add_texts(texts)
        vector_store.save_local(Config.FAISS_INDEX_PATH)
        self.qa_chain = self._create_qa_chain()  # Recreate the chain with updated index
