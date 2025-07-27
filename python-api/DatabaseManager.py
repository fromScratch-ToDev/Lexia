import os
from typing import Optional
from langchain_qdrant import QdrantVectorStore, FastEmbedSparse, RetrievalMode
from langchain_huggingface import HuggingFaceEmbeddings

# Configuration
COLLECTION_NAME = "code-civil-2"

class DatabaseManager:
    """Gestionnaire de connexion à la base de données Qdrant"""
    
    def __init__(self, embedding_model: str):
        self._collection_name = COLLECTION_NAME
        self._embeddings = embedding_model
        self._sparse_embeddings = None
        self._vectorstore = None
        self._initialize_embeddings()
        if not self._connect():
            raise Exception("❌ Impossible d'établir la connexion à la base de données")
        print("✅ Base de données Qdrant connectée avec succès")

    def _initialize_embeddings(self):
        """Initialise les modèles d'embeddings"""
        print("🔧 Initialisation des modèles d'embeddings...")
        
        self._embeddings = HuggingFaceEmbeddings(
            model_name=self._embeddings,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"device": "cpu"}  
        )
        
        self._sparse_embeddings = FastEmbedSparse(model_name="Qdrant/bm25")
        print("✅ Modèles d'embeddings initialisés")
    
    def _try_connect_qdrant(self) -> Optional[QdrantVectorStore]:
        """
        Tente de se connecter à la base de données Qdrant.
        Si la connexion échoue, supprime le fichier de verrouillage.
        """
        try:
            return self._connect_qdrant()
        except Exception as e:
            if "./qdrant_db is already accessed" in str(e):
                os.remove("./qdrant_db/.lock")
            return False
    
    def _connect_qdrant(self) -> QdrantVectorStore:
        """Établit la connexion à Qdrant"""
        return QdrantVectorStore.from_existing_collection(
            embedding=self._embeddings,
            collection_name=self._collection_name,
            path="./qdrant_db",
            retrieval_mode=RetrievalMode.HYBRID,
            vector_name="dense",
            sparse_vector_name="sparse",
            sparse_embedding=self._sparse_embeddings,
        )
    
    def _connect(self) -> bool:
        for i in range(3):
            print(f"Connexion à la base de données Qdrant (tentative {i+1}/3)...")
            self._vectorstore = self._try_connect_qdrant()
            if self._vectorstore is not False:
                break
        return self._vectorstore is not None
    
    def get_vectorstore(self) -> Optional[QdrantVectorStore]:
        """Retourne l'instance du vectorstore"""
        return self._vectorstore
    
