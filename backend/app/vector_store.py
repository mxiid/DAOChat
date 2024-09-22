from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType

from .config import Config

class VectorStore:
    def __init__(self):
        self.collection_name = "rag_documents"
        self.connect()
        self.create_collection()

    def connect(self):
        connections.connect(host=Config.MILVUS_HOST, port=Config.MILVUS_PORT)

    def create_collection(self):
        if not self.collection_exists():
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=1536)
            ]
            schema = CollectionSchema(fields, "RAG documents collection")
            self.collection = Collection(self.collection_name, schema)
            self.collection.create_index(field_name="embedding", index_params={"index_type": "IVF_FLAT", "metric_type": "L2", "params": {"nlist": 1024}})
        else:
            self.collection = Collection(self.collection_name)

    def collection_exists(self):
        return self.collection_name in self.list_collections()

    def list_collections(self):
        return connections.list_collections()

    # Add methods for inserting, searching, and managing vectors


