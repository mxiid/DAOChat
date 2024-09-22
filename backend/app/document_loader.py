import os
from typing import List
from langchain_community.document_loaders import TextLoader, PDFMinerLoader, CSVLoader
from langchain.schema import Document

def load_documents_from_directory(directory_path: str) -> List[Document]:
    documents = []
    for filename in os.listdir(directory_path):
        file_path = os.path.join(directory_path, filename)
        if filename.endswith('.txt'):
            loader = TextLoader(file_path)
        elif filename.endswith('.pdf'):
            loader = PDFMinerLoader(file_path)
        elif filename.endswith('.csv'):
            loader = CSVLoader(file_path)
        else:
            continue  # Skip unsupported file types
        documents.extend(loader.load())
    return documents
