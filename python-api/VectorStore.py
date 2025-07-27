from typing import List
from langchain_core.documents import Document



# Configuration
VECTOR_TOP_K = 5



class VectorStore:
    """Classe utilitaire pour les opérations sur le vectorstore"""
    
    def __init__(self, db_manager):
        self.vectorstore = db_manager.get_vectorstore()
    
    def _retrieve_documents(
        self,
        query: str,
        vector_top_k: int = VECTOR_TOP_K
    ) -> List[Document]:
        """
        Récupère les documents pertinents depuis une base Qdrant avec recherche hybride.
        
        :param query: La requête utilisateur
        :param vector_top_k: Nombre de documents à récupérer via recherche hybride
        :return: Liste des documents pertinents
        """
        relevant_docs = self.vectorstore.similarity_search(query, k=vector_top_k)
        if not relevant_docs:
            print("Aucun document pertinent trouvé.")

        return relevant_docs

    def get_context(self, query: str) -> str:
        """
        Récupère les documents pertinents depuis une base Qdrant avec recherche hybride
        et retourne le contexte final (concaténé) pour un prompt RAG.
        
        :param query: La requête utilisateur
        :return: Contexte concaténé des documents pertinents
        """
        # 1. Recherche hybride
        documents = self._retrieve_documents(query, vector_top_k=VECTOR_TOP_K)
        top_docs = [doc.page_content for doc in documents]
        top_docs.reverse()
        
        # 2. Construction du contexte
        context = "\n\n".join(top_docs)
        
        return context
    


