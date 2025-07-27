import os
import re
from typing import List, Dict
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

def convert_prompt_to_langchain_messages(messages: List[Dict[str, str]]) -> List:
    # Convertir les messages au format LangChain
    
    langchain_messages = []
    try:
        for msg in messages:
            if msg["role"] == "system":
                langchain_messages.append(SystemMessage(content=msg["content"]))
            elif msg["role"] == "user":
                langchain_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                langchain_messages.append(AIMessage(content=msg["content"]))
    except Exception as e:
        raise ValueError(f"Erreur lors de la conversion des messages: {str(e)}")
    
    return langchain_messages


def get_specific_civil_code_article(article_number: str) -> str:
    """
    Récupère un article spécifique du code civil français à partir de son numéro.
        param article_number: Le numéro de l'article à récupérer 
        return: Le texte complet de l'article du code civil
    """

    print(f"🔍 Recherche de l'article {article_number} dans le code civil...")
    
    try:
        # Chemin vers le fichier du code civil
        file_path = "./documents/code-civil.txt"
        
        # Vérifier si le fichier existe
        if not os.path.exists(file_path):
            return f"Erreur: Le fichier {file_path} n'existe pas."
        
        # Lire le contenu du fichier
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Pattern pour trouver l'article spécifique
        pattern = rf"Article {re.escape(article_number)}\b.*?(?=Article \d+|$)"
        
        # Rechercher l'article
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        
        if match:
            article_text = match.group(0).strip()
            return article_text
        else:
            return f"Article {article_number} non trouvé dans le code civil."
            
    except Exception as e:
        return f"Erreur lors de la lecture du code civil: {str(e)}"