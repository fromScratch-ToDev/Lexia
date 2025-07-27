import os
import re
import json
from typing import List, Dict, Tuple, Optional
from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore, FastEmbedSparse, RetrievalMode
from langchain_huggingface import HuggingFaceEmbeddings
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, SparseVectorParams
import numpy as np


class CodeCivilIndexer:
    def __init__(self):
        # Charger les variables d'environnement
        load_dotenv("../.env")
        
        # Initialiser les embeddings
        self.embeddings = HuggingFaceEmbeddings(
            model_name=os.getenv("EMBEDDED_MODEL"),
            model_kwargs={"device": "cpu"},
            encode_kwargs={"device": "cpu"}
        )
        
        # Initialiser les sparse embeddings
        self.sparse_embeddings = FastEmbedSparse(model_name="Qdrant/bm25")
        
        # Chemin vers le fichier du code civil
        self.code_civil_path = "./documents/code-civil.txt"
        
        # Collection name
        self.collection_name = "code-civil-2"
        
        # Qdrant database path
        self.db_path = "./qdrant_db"
        
        # Taille maximale des chunks en mots
        self.max_chunk_words = 520
        
    def detect_embedding_dimensions(self) -> int:
        """Détecte automatiquement le nombre de dimensions du modèle d'embedding."""
        sample_text = "Ceci est un texte d'exemple pour détecter les dimensions."
        sample_embedding = self.embeddings.embed_query(sample_text)
        return len(sample_embedding)
    
    def parse_structure_line(self, line: str) -> Tuple[str, str]:
        """Parse une ligne pour identifier le type de structure et son contenu."""
        line = line.strip()
        
        # Patterns pour identifier les différentes structures
        patterns = {
            "Titre": r"^Titre\s+(.+)$",
            "Livre": r"^Livre\s+(.+)$", 
            "Chapitre": r"^Chapitre\s+(.+)$",
            "Section": r"^Section\s+(.+)$",
            "Sous-section": r"^Sous-section\s+(.+)$",
            "Article": r"^Article\s+(.+)$"
        }
        
        for structure_type, pattern in patterns.items():
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                return structure_type, match.group(1).strip()
        
        return None, None
    
    def count_words(self, text: str) -> int:
        """Compte le nombre de mots dans un texte."""
        return len(text.split())
    
    def parse_code_civil(self) -> List[Dict]:
        """Parse le fichier code-civil.txt et retourne une liste de chunks avec métadonnées."""
        with open(self.code_civil_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        chunks = []
        current_metadata = {
            "Livre": "",
            "Titre": "",
            "Chapitre": "",
            "Section": "",
            "SousSection": "",
            "Articles": []
        }
        
        current_chunk_text = ""
        current_articles = []
        
        def reset_metadata_from_level(level: str):
            """Reset les métadonnées à partir d'un certain niveau hiérarchique."""
            levels = ["Titre", "Livre", "Chapitre", "Section", "SousSection", "Articles"]
            reset_index = levels.index(level)
            
            for i in range(reset_index + 1, len(levels)):
                if levels[i] == "Articles":
                    current_metadata["Articles"] = []
                else:
                    current_metadata[levels[i]] = ""
        
        def save_current_chunk():
            """Sauvegarde le chunk actuel s'il contient du texte."""
            if current_chunk_text.strip():
                chunk_metadata = current_metadata.copy()
                chunk_metadata["Articles"] = current_articles.copy()
                
                chunks.append({
                    "text": current_chunk_text.strip(),
                    "metadata": chunk_metadata
                })
        
        def start_new_chunk():
            """Démarre un nouveau chunk."""
            nonlocal current_chunk_text, current_articles
            current_chunk_text = ""
            current_articles = []
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Ignorer les lignes vides
            if not line:
                i += 1
                continue
            
            # Identifier le type de structure
            structure_type, content = self.parse_structure_line(line)
            
            if structure_type:
                if structure_type in ["Titre", "Livre", "Chapitre", "Section", "SousSection"]:
                    # Pour ces niveaux, on sauvegarde le chunk actuel et on en démarre un nouveau
                    save_current_chunk()
                    start_new_chunk()
                    
                    # Mettre à jour les métadonnées
                    if structure_type == "SousSection":
                        current_metadata["SousSection"] = content
                        reset_metadata_from_level("SousSection")
                    else:
                        current_metadata[structure_type] = content
                        reset_metadata_from_level(structure_type)
                
                elif structure_type == "Article":
                    # Collecter le contenu de l'article
                    article_content = []
                    i += 1
                    
                    # Lire le contenu de l'article jusqu'à la prochaine structure
                    while i < len(lines):
                        next_line = lines[i].strip()
                        if not next_line:
                            i += 1
                            continue
                        
                        next_structure_type, _ = self.parse_structure_line(next_line)
                        if next_structure_type:
                            i -= 1  # Revenir en arrière pour traiter cette ligne au prochain tour
                            break
                        
                        article_content.append(next_line)
                        i += 1
                    
                    article_text = " ".join(article_content)
                    
                    # Créer les métadonnées de l'article
                    article_info = {
                        "Article": content,
                        "First_Sentence": "",
                        "Last_Sentence": ""
                    }
                    
                    # Extraire la première et dernière phrase si possible
                    if article_text:
                        sentences = re.split(r'[.!?]+', article_text)
                        sentences = [s.strip() for s in sentences if s.strip()]
                        
                        if sentences:
                            article_info["First_Sentence"] = sentences[0]
                            article_info["Last_Sentence"] = sentences[-1]
                    
                    # Vérifier si ajouter cet article dépasserait la limite de mots
                    potential_text = current_chunk_text + f"\n\nArticle {content}\n\n{article_text}"
                    
                    if self.count_words(potential_text) > self.max_chunk_words and current_chunk_text.strip():
                        # Sauvegarder le chunk actuel et démarrer un nouveau
                        save_current_chunk()
                        start_new_chunk()
                    
                    # Ajouter l'article au chunk actuel
                    current_chunk_text += f"\n\nArticle {content}\n\n{article_text}"
                    current_articles.append(article_info)
            
            i += 1
        
        # Sauvegarder le dernier chunk
        save_current_chunk()
        
        return chunks
    
    def create_qdrant_collection(self):
        """Crée ou recrée la collection Qdrant."""
        client = QdrantClient(path=self.db_path)
        
        # Supprimer la collection si elle existe
        try:
            client.delete_collection(self.collection_name)
            print(f"Collection '{self.collection_name}' supprimée.")
        except Exception:
            print(f"Collection '{self.collection_name}' n'existait pas.")
        
        # Détecter les dimensions
        vector_size = self.detect_embedding_dimensions()
        print(f"Dimensions détectées: {vector_size}")
        
        # Créer la nouvelle collection
        client.create_collection(
            collection_name=self.collection_name,
            vectors_config={
                "dense": VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE
                )
            },
            sparse_vectors_config={
                "sparse": SparseVectorParams()
            }
        )
        
        print(f"Collection '{self.collection_name}' créée avec succès.")
    
    def index_documents(self):
        """Index les documents dans Qdrant."""
        print("Parsing du Code Civil...")
        chunks = self.parse_code_civil()
        print(f"Nombre de chunks créés: {len(chunks)}")
        
        print("Création de la collection Qdrant...")
        self.create_qdrant_collection()
        
        print("Conversion en documents Langchain...")
        documents = []
        for i, chunk in enumerate(chunks):
            doc = Document(
                page_content=chunk["text"],
                metadata={
                    **chunk["metadata"],
                    "chunk_id": i
                }
            )
            documents.append(doc)
        
        print("Indexation dans Qdrant...")
        vector_store = QdrantVectorStore.from_documents(
            documents=documents,
            embedding=self.embeddings,
            collection_name=self.collection_name,
            path=self.db_path,
            retrieval_mode=RetrievalMode.HYBRID,
            vector_name="dense",
            sparse_vector_name="sparse",
            sparse_embedding=self.sparse_embeddings,
        )
        
        print(f"Indexation terminée! {len(documents)} documents indexés dans la collection '{self.collection_name}'.")
        
        # Afficher quelques statistiques
        print("\n=== Statistiques ===")
        print(f"Nombre total de chunks: {len(chunks)}")
        
        word_counts = [self.count_words(chunk["text"]) for chunk in chunks]
        print(f"Mots par chunk - Min: {min(word_counts)}, Max: {max(word_counts)}, Moyenne: {sum(word_counts)/len(word_counts):.1f}")
        
        # Exemples de métadonnées
        print("\n=== Exemple de métadonnées ===")
        for i, chunk in enumerate(chunks[:3]):
            print(f"Chunk {i+1}:")
            print(f"  Livre: {chunk['metadata']['Livre']}")
            print(f"  Titre: {chunk['metadata']['Titre']}")
            print(f"  Chapitre: {chunk['metadata']['Chapitre']}")
            print(f"  Section: {chunk['metadata']['Section']}")
            print(f"  Sous-section: {chunk['metadata']['SousSection']}")
            print(f"  Nombre d'articles: {len(chunk['metadata']['Articles'])}")
            if chunk['metadata']['Articles']:
                print(f"  Premier article: {chunk['metadata']['Articles'][0]['Article']}")
            print(f"  Nombre de mots: {self.count_words(chunk['text'])}")
            print()


def main():
    """Fonction principale pour lancer l'indexation."""
    indexer = CodeCivilIndexer()
    indexer.index_documents()


if __name__ == "__main__":
    main()
