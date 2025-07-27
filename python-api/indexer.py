import os
import re
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.schema import Document

from qdrant_client import QdrantClient, models
from qdrant_client.models import Distance, VectorParams, PointStruct, SparseVectorParams
from sentence_transformers import SentenceTransformer

# Charger les variables d'environnement
load_dotenv()

class CodeCivilIndexer:
    def __init__(self):
        """
        Initialise l'indexer pour le Code Civil
        """
        self.embedded_model_name = os.getenv("EMBEDDED_MODEL", "BAAI/bge-m3")
        self.collection_name = "code-civil"
        self.vector_size = None  # Sera déterminé automatiquement
        self.chunk_size_words = 520
        self.chunk_overlap_words = 50
        
        # Configuration des chemins
        self.documents_path = Path(__file__).parent / "documents"
        self.code_civil_path = self.documents_path / "code-civil.txt"
        
        # Initialiser le client Qdrant avec le serveur distant
        # self.qdrant_client = QdrantClient(url="http://localhost:6333")
        
        # Alternative pour connexion locale (décommentez si nécessaire)
        self.qdrant_client = QdrantClient(path="./qdrant_db")
        
        # Initialiser le modèle d'embedding avec CPU
        self.embedding_model = HuggingFaceEmbeddings(
            model_name=self.embedded_model_name,
            #model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True, 'show_progress_bar': True}
        )
        
        # Initialiser SentenceTransformer pour la normalisation
        self.sentence_transformer = SentenceTransformer(
            self.embedded_model_name, 
            device='cpu'
        )
        
        # Déterminer automatiquement la taille des vecteurs
        self._determine_vector_size()
        
    def _determine_vector_size(self):
        """
        Détermine automatiquement la taille des vecteurs du modèle
        """
        print("Détermination de la taille des vecteurs...")
        test_text = "Test pour déterminer la dimension des vecteurs."
        test_embedding = self.sentence_transformer.encode([test_text], normalize_embeddings=True)
        self.vector_size = len(test_embedding[0])
        print(f"Taille des vecteurs détectée: {self.vector_size} dimensions")
        
    def _count_words(self, text: str) -> int:
        """
        Compte le nombre de mots dans un texte
        """
        return len(text.split())
    
    def _create_collection_if_not_exists(self):
        """
        Crée la collection Qdrant si elle n'existe pas
        """
        try:
            collections = self.qdrant_client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                print(f"Création de la collection '{self.collection_name}'...")
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config={
                        "dense": VectorParams(
                            size=self.vector_size,
                            distance=Distance.COSINE,
                            on_disk=True,                          # vecteurs denses sur disque
                            hnsw_config=models.HnswConfigDiff(on_disk=True)  # index HNSW sur disque
                        )
                    },
                    sparse_vectors_config={
                        "sparse": SparseVectorParams(
                            index=models.SparseIndexParams(on_disk=True)    # vecteurs creux sur disque
                        )
                    }
                )
                print(f"Collection '{self.collection_name}' créée avec succès.")
            else:
                print(f"La collection '{self.collection_name}' existe déjà.")
                
        except Exception as e:
            print(f"Erreur lors de la création de la collection: {e}")
            raise
    
    def _extract_structure_metadata(self, text: str, position: int) -> Dict[str, str]:
        """
        Extrait les métadonnées de structure (Livre, Titre, Chapitre, etc.) pour une position donnée
        """
        # Rechercher en arrière pour trouver la structure hiérarchique
        text_before = text[:position]
        
        # Patterns pour extraire la structure
        livre_pattern = r'Livre\s+([IVXLCDM]+)\s*:\s*(.+?)(?=\n|$)'
        titre_pattern = r'Titre\s+([IVXLCDM]+|préliminaire)\s*:\s*(.+?)(?=\n|$)'
        chapitre_pattern = r'Chapitre\s+([IVXLCDM]+)\s*:\s*(.+?)(?=\n|$)'
        section_pattern = r'Section\s+([IVXLCDM]+)\s*:\s*(.+?)(?=\n|$)'
        sous_section_pattern = r'Sous-section\s+([IVXLCDM]+)\s*:\s*(.+?)(?=\n|$)'
        
        # Chercher les dernières occurrences de chaque niveau hiérarchique
        livre_match = None
        for match in re.finditer(livre_pattern, text_before, re.IGNORECASE):
            livre_match = match
            
        titre_match = None
        for match in re.finditer(titre_pattern, text_before, re.IGNORECASE):
            titre_match = match
            
        chapitre_match = None
        for match in re.finditer(chapitre_pattern, text_before, re.IGNORECASE):
            chapitre_match = match
            
        section_match = None
        for match in re.finditer(section_pattern, text_before, re.IGNORECASE):
            section_match = match
            
        sous_section_match = None
        for match in re.finditer(sous_section_pattern, text_before, re.IGNORECASE):
            sous_section_match = match
        
        # Construire les métadonnées
        metadata = {}
        
        if livre_match:
            metadata["livre_numero"] = livre_match.group(1).strip()
            metadata["livre_titre"] = livre_match.group(2).strip()
            
        if titre_match:
            metadata["titre_numero"] = titre_match.group(1).strip()
            metadata["titre_titre"] = titre_match.group(2).strip()
            
        if chapitre_match:
            metadata["chapitre_numero"] = chapitre_match.group(1).strip()
            metadata["chapitre_titre"] = chapitre_match.group(2).strip()
            
        if section_match:
            metadata["section_numero"] = section_match.group(1).strip()
            metadata["section_titre"] = section_match.group(2).strip()
            
        if sous_section_match:
            metadata["sous_section_numero"] = sous_section_match.group(1).strip()
            metadata["sous_section_titre"] = sous_section_match.group(2).strip()
        
        return metadata
    
    def _extract_article_number(self, text: str) -> str:
        """
        Extrait le numéro d'article du début du texte (pour compatibilité)
        """
        # Pattern pour capturer les numéros d'articles (y compris avec tirets comme 6-1)
        article_pattern = r'^Article\s+(\d+(?:-\d+)*)'
        match = re.search(article_pattern, text.strip(), re.IGNORECASE)
        
        if match:
            return match.group(1)
        return ""
    
    def _extract_all_articles(self, text: str) -> List[str]:
        """
        Extrait tous les numéros d'articles présents dans le texte
        """
        # Pattern pour capturer tous les numéros d'articles dans le texte
        article_pattern = r'Article\s+(\d+(?:-\d+)*)'
        matches = re.findall(article_pattern, text, re.IGNORECASE)
        
        # Supprimer les doublons tout en préservant l'ordre
        seen = set()
        unique_articles = []
        for article in matches:
            if article not in seen:
                seen.add(article)
                unique_articles.append(article)
        
        return unique_articles
    
    def _load_and_preprocess_text(self) -> str:
        """
        Charge et préprocesse le fichier code-civil.txt
        """
        if not self.code_civil_path.exists():
            raise FileNotFoundError(f"Le fichier {self.code_civil_path} n'existe pas.")
        
        print(f"Chargement du fichier: {self.code_civil_path}")
        
        with open(self.code_civil_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Nettoyage basique du texte mais préservation des structures importantes
        content = re.sub(r'\n{3,}', '\n\n', content)  # Réduire les sauts de ligne excessifs
        content = re.sub(r'[ \t]+', ' ', content)     # Normaliser les espaces
        content = content.strip()
        
        print(f"Texte chargé: {len(content)} caractères, {self._count_words(content)} mots")
        return content
    
    def _create_chunks(self, text: str) -> List[Document]:
        """
        Découpe le texte en chunks de 520 mots avec recouvrement et métadonnées enrichies
        """
        print("Découpage du texte en chunks avec extraction des métadonnées...")
        
        # Estimation de la taille en caractères (moyenne 5 caractères par mot)
        chunk_size_chars = self.chunk_size_words * 5
        chunk_overlap_chars = self.chunk_overlap_words * 5
        
        # Utiliser RecursiveCharacterTextSplitter pour un découpage intelligent
        # Prioriser la séparation aux articles
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size_chars,
            chunk_overlap=chunk_overlap_chars,
            length_function=len,
            separators=["\n\nArticle ", "\n\nLivre ", "\n\nTitre ", "\n\nChapitre ", "\n\n", "\n", ". ", " ", ""]
        )
        
        # Créer des documents
        documents = text_splitter.create_documents([text])
        
        # Filtrer et ajuster les chunks pour respecter la limite de mots et ajouter les métadonnées
        filtered_docs = []
        for i, doc in enumerate(documents):
            word_count = self._count_words(doc.page_content)
            
            # Trouver la position du chunk dans le texte original pour extraire les métadonnées
            chunk_position = text.find(doc.page_content[:100])  # Utiliser les 100 premiers caractères
            if chunk_position == -1:
                chunk_position = 0
            
            # Extraire les métadonnées de structure
            structure_metadata = self._extract_structure_metadata(text, chunk_position)
            
            # Extraire le numéro d'article si présent (pour compatibilité)
            article_number = self._extract_article_number(doc.page_content)
            
            # Extraire tous les articles présents dans le chunk
            all_articles = self._extract_all_articles(doc.page_content)
            
            if word_count > self.chunk_size_words:
                # Si le chunk est trop long, le redécouper
                words = doc.page_content.split()
                while len(words) > self.chunk_size_words:
                    chunk_words = words[:self.chunk_size_words]
                    chunk_text = ' '.join(chunk_words)
                    
                    # Extraire le numéro d'article pour ce sous-chunk
                    sub_article_number = self._extract_article_number(chunk_text)
                    sub_all_articles = self._extract_all_articles(chunk_text)
                    
                    # Créer les métadonnées complètes
                    metadata = {
                        "source": "code-civil.txt",
                        "chunk_id": len(filtered_docs),
                        "word_count": len(chunk_words),
                        "article_number": sub_article_number or article_number,
                        "all_articles": sub_all_articles if sub_all_articles else all_articles,
                        "articles_count": len(sub_all_articles) if sub_all_articles else len(all_articles),
                        **structure_metadata
                    }
                    
                    # Ajouter des métadonnées de contexte pour la recherche
                    if sub_article_number or article_number or sub_all_articles or all_articles:
                        metadata["has_article"] = True
                        primary_article = sub_article_number or article_number
                        if primary_article:
                            metadata["article_text"] = f"Article {primary_article}"
                        elif sub_all_articles:
                            metadata["article_text"] = f"Articles {', '.join(sub_all_articles)}"
                        elif all_articles:
                            metadata["article_text"] = f"Articles {', '.join(all_articles)}"
                    else:
                        metadata["has_article"] = False
                    
                    filtered_docs.append(Document(
                        page_content=chunk_text,
                        metadata=metadata
                    ))
                    
                    # Retirer les mots traités avec un recouvrement
                    words = words[self.chunk_size_words - self.chunk_overlap_words:]
                
                # Traiter les mots restants s'il y en a
                if words:
                    chunk_text = ' '.join(words)
                    if self._count_words(chunk_text) > 10:  # Minimum 10 mots
                        sub_article_number = self._extract_article_number(chunk_text)
                        sub_all_articles = self._extract_all_articles(chunk_text)
                        
                        metadata = {
                            "source": "code-civil.txt",
                            "chunk_id": len(filtered_docs),
                            "word_count": len(words),
                            "article_number": sub_article_number or article_number,
                            "all_articles": sub_all_articles if sub_all_articles else all_articles,
                            "articles_count": len(sub_all_articles) if sub_all_articles else len(all_articles),
                            **structure_metadata
                        }
                        
                        if sub_article_number or article_number or sub_all_articles or all_articles:
                            metadata["has_article"] = True
                            primary_article = sub_article_number or article_number
                            if primary_article:
                                metadata["article_text"] = f"Article {primary_article}"
                            elif sub_all_articles:
                                metadata["article_text"] = f"Articles {', '.join(sub_all_articles)}"
                            elif all_articles:
                                metadata["article_text"] = f"Articles {', '.join(all_articles)}"
                        else:
                            metadata["has_article"] = False
                        
                        filtered_docs.append(Document(
                            page_content=chunk_text,
                            metadata=metadata
                        ))
            else:
                # Le chunk respecte la limite de mots
                metadata = {
                    "source": "code-civil.txt",
                    "chunk_id": i,
                    "word_count": word_count,
                    "article_number": article_number,
                    "all_articles": all_articles,
                    "articles_count": len(all_articles),
                    **structure_metadata
                }
                
                # Ajouter des métadonnées de contexte
                if article_number or all_articles:
                    metadata["has_article"] = True
                    if article_number:
                        metadata["article_text"] = f"Article {article_number}"
                    elif all_articles:
                        metadata["article_text"] = f"Articles {', '.join(all_articles)}"
                else:
                    metadata["has_article"] = False
                
                doc.metadata = metadata
                filtered_docs.append(doc)
        
        print(f"Nombre de chunks créés: {len(filtered_docs)}")
        
        # Afficher quelques statistiques sur les métadonnées
        articles_count = sum(1 for doc in filtered_docs if doc.metadata.get("has_article", False))
        print(f"Chunks contenant des articles: {articles_count}/{len(filtered_docs)}")
        
        return filtered_docs
    
    def _create_embeddings(self, documents: List[Document]) -> List[List[float]]:
        """
        Crée les embeddings pour les documents avec normalisation cosine
        """
        print("Création des embeddings...")
        
        texts = [doc.page_content for doc in documents]
        
        # Créer les embeddings avec SentenceTransformer pour plus de contrôle
        embeddings = self.sentence_transformer.encode(
            texts,
            normalize_embeddings=True,  # Normalisation cosine
            show_progress_bar=True,
            device='cpu'
        )
        
        # Convertir en liste de listes pour Qdrant
        embeddings_list = [embedding.tolist() for embedding in embeddings]
        
        print(f"Embeddings créés: {len(embeddings_list)} vecteurs de dimension {len(embeddings_list[0])}")
        return embeddings_list
    
    def _index_documents(self, documents: List[Document], embeddings: List[List[float]]):
        """
        Indexe les documents dans Qdrant avec la structure LangChain
        """
        print("Indexation des documents dans Qdrant...")
        
        # Vider la collection existante
        try:
            self.qdrant_client.delete_collection(self.collection_name)
        except:
            pass
        
        # Recréer la collection
        self._create_collection_if_not_exists()
        
        # Préparer les points pour l'insertion avec la structure LangChain enrichie
        points = []
        for i, (doc, embedding) in enumerate(zip(documents, embeddings)):
            point = PointStruct(
                id=i,
                vector={"dense": embedding},  # Utiliser le nom "dense" pour le vecteur
                payload={
                    "page_content": doc.page_content,  # Structure LangChain
                    "metadata": {  # Métadonnées enrichies dans un objet séparé
                        "source": doc.metadata.get("source", ""),
                        "chunk_id": doc.metadata.get("chunk_id", i),
                        "word_count": doc.metadata.get("word_count", 0),
                        "article_number": doc.metadata.get("article_number", ""),
                        "all_articles": doc.metadata.get("all_articles", []),
                        "articles_count": doc.metadata.get("articles_count", 0),
                        "article_text": doc.metadata.get("article_text", ""),
                        "has_article": doc.metadata.get("has_article", False),
                        "livre_numero": doc.metadata.get("livre_numero", ""),
                        "livre_titre": doc.metadata.get("livre_titre", ""),
                        "titre_numero": doc.metadata.get("titre_numero", ""),
                        "titre_titre": doc.metadata.get("titre_titre", ""),
                        "chapitre_numero": doc.metadata.get("chapitre_numero", ""),
                        "chapitre_titre": doc.metadata.get("chapitre_titre", ""),
                        "section_numero": doc.metadata.get("section_numero", ""),
                        "section_titre": doc.metadata.get("section_titre", ""),
                        "sous_section_numero": doc.metadata.get("sous_section_numero", ""),
                        "sous_section_titre": doc.metadata.get("sous_section_titre", "")
                    }
                }
            )
            points.append(point)
        
        # Insérer les points par batch
        batch_size = 100
        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=batch
            )
            print(f"Batch {i//batch_size + 1}/{(len(points)-1)//batch_size + 1} indexé")
        
        print(f"Indexation terminée: {len(points)} documents indexés dans la collection '{self.collection_name}'")
    
    def search_similar(self, query: str, limit: int = 5, filter_article: str = None, filter_livre: str = None, filter_titre: str = None) -> List[Dict[str, Any]]:
        """
        Effectue une recherche de similarité dans la collection avec filtres optionnels
        
        Args:
            query: Requête de recherche
            limit: Nombre maximum de résultats
            filter_article: Numéro d'article spécifique à rechercher (ex: "1", "6-1")
            filter_livre: Numéro de livre à filtrer (ex: "Ier", "II")
            filter_titre: Numéro de titre à filtrer (ex: "Ier", "préliminaire")
        """
        # Créer l'embedding de la requête
        query_embedding = self.sentence_transformer.encode(
            [query], 
            normalize_embeddings=True,
            device='cpu'
        )[0].tolist()
        
        # Construire les filtres si spécifiés
        search_filter = None
        if filter_article or filter_livre or filter_titre:
            conditions = []
            
            if filter_article:
                conditions.append({
                    "key": "metadata.article_number",
                    "match": {"value": filter_article}
                })
            
            if filter_livre:
                conditions.append({
                    "key": "metadata.livre_numero",
                    "match": {"value": filter_livre}
                })
                
            if filter_titre:
                conditions.append({
                    "key": "metadata.titre_numero",
                    "match": {"value": filter_titre}
                })
            
            if len(conditions) == 1:
                search_filter = conditions[0]
            else:
                search_filter = {"must": conditions}
        
        # Effectuer la recherche
        search_result = self.qdrant_client.search(
            collection_name=self.collection_name,
            query_vector=("dense", query_embedding),  # Utiliser le nom "dense" pour la recherche
            query_filter=search_filter,
            limit=limit
        )
        
        # Formater les résultats avec les métadonnées enrichies
        results = []
        for hit in search_result:
            metadata = hit.payload["metadata"]
            
            # Construire le contexte hiérarchique
            hierarchy_context = []
            if metadata.get("livre_numero") and metadata.get("livre_titre"):
                hierarchy_context.append(f"Livre {metadata['livre_numero']}: {metadata['livre_titre']}")
            if metadata.get("titre_numero") and metadata.get("titre_titre"):
                hierarchy_context.append(f"Titre {metadata['titre_numero']}: {metadata['titre_titre']}")
            if metadata.get("chapitre_numero") and metadata.get("chapitre_titre"):
                hierarchy_context.append(f"Chapitre {metadata['chapitre_numero']}: {metadata['chapitre_titre']}")
            if metadata.get("section_numero") and metadata.get("section_titre"):
                hierarchy_context.append(f"Section {metadata['section_numero']}: {metadata['section_titre']}")
            if metadata.get("sous_section_numero") and metadata.get("sous_section_titre"):
                hierarchy_context.append(f"Sous-section {metadata['sous_section_numero']}: {metadata['sous_section_titre']}")
            
            result = {
                "text": hit.payload["page_content"],
                "score": hit.score,
                "chunk_id": metadata["chunk_id"],
                "word_count": metadata["word_count"],
                "source": metadata["source"],
                "article_number": metadata.get("article_number", ""),
                "all_articles": metadata.get("all_articles", []),
                "articles_count": metadata.get("articles_count", 0),
                "article_text": metadata.get("article_text", ""),
                "has_article": metadata.get("has_article", False),
                "hierarchy_context": " > ".join(hierarchy_context) if hierarchy_context else "",
                "livre": {
                    "numero": metadata.get("livre_numero", ""),
                    "titre": metadata.get("livre_titre", "")
                },
                "titre": {
                    "numero": metadata.get("titre_numero", ""),
                    "titre": metadata.get("titre_titre", "")
                },
                "chapitre": {
                    "numero": metadata.get("chapitre_numero", ""),
                    "titre": metadata.get("chapitre_titre", "")
                },
                "section": {
                    "numero": metadata.get("section_numero", ""),
                    "titre": metadata.get("section_titre", "")
                },
                "sous_section": {
                    "numero": metadata.get("sous_section_numero", ""),
                    "titre": metadata.get("sous_section_titre", "")
                }
            }
            results.append(result)
        
        return results
    
    def search_by_article(self, article_number: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Recherche spécifique par numéro d'article
        """
        return self.search_similar(
            query=f"Article {article_number}",
            limit=limit,
            filter_article=article_number
        )
    
    def search_by_multiple_articles(self, article_numbers: List[str], limit: int = 10) -> List[Dict[str, Any]]:
        """
        Recherche dans les chunks contenant l'un des articles spécifiés
        """
        # Créer un filtre pour chercher les chunks contenant l'un des articles
        conditions = []
        for article in article_numbers:
            conditions.append({
                "key": "metadata.all_articles",
                "match": {"any": [article]}
            })
        
        search_filter = {"should": conditions} if len(conditions) > 1 else conditions[0]
        
        # Effectuer la recherche avec un embedding générique
        query_text = f"Articles {', '.join(article_numbers)}"
        query_embedding = self.sentence_transformer.encode(
            [query_text], 
            normalize_embeddings=True,
            device='cpu'
        )[0].tolist()
        
        search_result = self.qdrant_client.search(
            collection_name=self.collection_name,
            query_vector=("dense", query_embedding),
            query_filter=search_filter,
            limit=limit
        )
        
        # Formater les résultats
        results = []
        for hit in search_result:
            metadata = hit.payload["metadata"]
            
            # Construire le contexte hiérarchique
            hierarchy_context = []
            if metadata.get("livre_numero") and metadata.get("livre_titre"):
                hierarchy_context.append(f"Livre {metadata['livre_numero']}: {metadata['livre_titre']}")
            if metadata.get("titre_numero") and metadata.get("titre_titre"):
                hierarchy_context.append(f"Titre {metadata['titre_numero']}: {metadata['titre_titre']}")
            if metadata.get("chapitre_numero") and metadata.get("chapitre_titre"):
                hierarchy_context.append(f"Chapitre {metadata['chapitre_numero']}: {metadata['chapitre_titre']}")
            if metadata.get("section_numero") and metadata.get("section_titre"):
                hierarchy_context.append(f"Section {metadata['section_numero']}: {metadata['section_titre']}")
            if metadata.get("sous_section_numero") and metadata.get("sous_section_titre"):
                hierarchy_context.append(f"Sous-section {metadata['sous_section_numero']}: {metadata['sous_section_titre']}")
            
            result = {
                "text": hit.payload["page_content"],
                "score": hit.score,
                "chunk_id": metadata["chunk_id"],
                "word_count": metadata["word_count"],
                "source": metadata["source"],
                "article_number": metadata.get("article_number", ""),
                "all_articles": metadata.get("all_articles", []),
                "articles_count": metadata.get("articles_count", 0),
                "article_text": metadata.get("article_text", ""),
                "has_article": metadata.get("has_article", False),
                "hierarchy_context": " > ".join(hierarchy_context) if hierarchy_context else "",
                "matched_articles": [art for art in metadata.get("all_articles", []) if art in article_numbers],
                "livre": {
                    "numero": metadata.get("livre_numero", ""),
                    "titre": metadata.get("livre_titre", "")
                },
                "titre": {
                    "numero": metadata.get("titre_numero", ""),
                    "titre": metadata.get("titre_titre", "")
                },
                "chapitre": {
                    "numero": metadata.get("chapitre_numero", ""),
                    "titre": metadata.get("chapitre_titre", "")
                },
                "section": {
                    "numero": metadata.get("section_numero", ""),
                    "titre": metadata.get("section_titre", "")
                },
                "sous_section": {
                    "numero": metadata.get("sous_section_numero", ""),
                    "titre": metadata.get("sous_section_titre", "")
                }
            }
            results.append(result)
        
        return results
    
    def search_by_livre(self, livre_numero: str, query: str = "", limit: int = 10) -> List[Dict[str, Any]]:
        """
        Recherche dans un livre spécifique du Code Civil
        """
        search_query = query if query else f"Livre {livre_numero}"
        return self.search_similar(
            query=search_query,
            limit=limit,
            filter_livre=livre_numero
        )
    
    def index_code_civil(self):
        """
        Lance le processus complet d'indexation du Code Civil
        """
        print("=== Début de l'indexation du Code Civil ===")
        
        try:
            # 1. Créer la collection si nécessaire
            self._create_collection_if_not_exists()
            
            # 2. Charger et préprocesser le texte
            text = self._load_and_preprocess_text()
            
            # 3. Créer les chunks
            documents = self._create_chunks(text)
            
            # 4. Créer les embeddings
            embeddings = self._create_embeddings(documents)
            
            # 5. Indexer dans Qdrant
            self._index_documents(documents, embeddings)
            
            print("=== Indexation terminée avec succès ===")
            
            # Afficher les statistiques
            collection_info = self.qdrant_client.get_collection(self.collection_name)
            print(f"Collection '{self.collection_name}': {collection_info.points_count} points indexés")
            
        except Exception as e:
            print(f"Erreur lors de l'indexation: {e}")
            raise


def main():
    """
    Fonction principale pour lancer l'indexation
    """
    indexer = CodeCivilIndexer()
    indexer.index_code_civil()


if __name__ == "__main__":
    main()
