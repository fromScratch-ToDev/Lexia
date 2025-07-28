import os
import re
import json
from typing import List, Generator
from langchain_core.messages import (
    ToolMessage
)
from langchain_core.tools import tool
from DatabaseManager import DatabaseManager
from VectorStore import VectorStore
from langchain_ollama import ChatOllama
from utils import convert_prompt_to_langchain_messages, get_specific_civil_code_article as get_article
from dotenv import load_dotenv

load_dotenv("../.env")

user_messages = []  # Liste pour stocker les messages de l'utilisateur # Pas utilisé pour actuellement

MAX_TOKENS = 4096  # Nombre maximum de tokens pour le modèle
MAX_ITERATIONS = 3  # Nombre maximum d'itérations pour la conversation

db_manager = DatabaseManager(os.getenv("EMBEDDED_MODEL"))
vectorstore = VectorStore(db_manager=db_manager)
llm = ChatOllama(
            model=os.getenv("OLLAMA_MODEL"),
            temperature=0.7,
            num_ctx=MAX_TOKENS,
            reasoning=False,
        )



@tool
def get_specific_civil_code_article(article_number: str) -> str:
    """
    Récupère un article spécifique du code civil français à partir de son numéro.
        param article_number: Le numéro de l'article à récupérer 
        return: Le texte complet de l'article du code civil
    """

    print(f"🔍 Recherche de l'article {article_number} dans le code civil...")

    return get_article(article_number)


# Pas utilisé actuellement
@tool
def get_previous_user_message() -> List[str]:
    """
    A utiliser lorsque tu ne comprends pas la question de l'utilisateur pour voir ce qu'il a dit précédemment.
    Récupère le dernier message de l'utilisateur.
        return: Dernier message de l'utilisateur
    """
    global user_messages

    if not user_messages:
        return "Aucun message utilisateur précédent disponible."
    return [message for message in user_messages]


@tool
def get_context_on_french_civil_code(query: str) -> str:
    """
    Permet de faire une recherche à l'intérieur du code civil français.
        param query: La requête utilisateur
        return: Contexte issus du code civil français
    """

    context = vectorstore.get_context(query)
    print(f"Contexte récupéré pour la requête '{query}': {context[:100]}...")  # Affiche les 100 premiers caractères du contexte
    return context



    

class OllamaAgent:
    def __init__(self):
        self._max_iterations = MAX_ITERATIONS
        
        # Initialiser le LLM avec des paramètres optimisés
        self._llm = llm

    def process_message(self, messages: list[dict[str,str]]) -> Generator[str, None, None]:
        global user_messages

        system_message = {
            "role": "system",
            "content": """   
            Vous êtes un assistant IA capable d'avoir une conversation et d'utiliser plusieurs outils pour répondre aux questions des utilisateurs.
            Votre réponse doit être basée UNIQUEMENT sur les informations obtenues via ces outils et JAMAIS à partir de votre propre connaissance.

            RÈGLES FONDAMENTALES :
            1. ANALYSEZ d'abord la question pour déterminer quels outils sont nécessaires
            2. UTILISEZ les outils appropriés pour collecter les informations requises
            3. COMBINEZ les résultats de tous les outils utilisés pour formuler une réponse complète
            4. RÉPONDEZ UNIQUEMENT basé sur les informations obtenues via les outils
            5. CITEZ toujours les sources (articles du code civil, résultats d'opérations, etc.) dans votre réponse
            6. RÉPONDEZ de manière naturelle et conversationnelle, ne mentionnez JAMAIS les outils que vous utilisez
            
            PROCESSUS DE TRAVAIL :
            - Identifiez les informations manquantes pour répondre à la question
            - Sélectionnez et utilisez les outils pertinents (vous pouvez en utiliser plusieurs)
            - Attendez les résultats de tous les outils avant de répondre
            - Synthétisez les informations collectées en une réponse cohérente et structurée
            
            PRÉSENTATION DES RÉPONSES :
            - Structurez votre réponse de manière claire avec des sections si nécessaire
            - Indiquez les sources des informations
            - Si les outils ne fournissent pas assez d'informations, demandez des précisions
            - Répondez comme si vous aviez naturellement accès à ces informations
            
            N'inventez jamais d'informations. Utilisez exclusivement les données obtenues via les outils disponibles.
            Ne faites jamais référence aux "outils", "recherches" ou "bases de données" dans vos réponses.
            """
        }

        processed_messages = []
        user_messages = [] # Réinitialiser la liste des messages de l'utilisateur

        # Limiter le nombre de messages à 10 derniers messages pour éviter les surcharges
        for message_num in range(len(messages)-1, len(messages) - 11, -1):
            if message_num < 0:
                break
            else :
                processed_messages.insert(0, messages[message_num])

        # Récupérer tous les messages précédents de l'utilisateur
        for message in reversed(messages):
            if message["role"] == "user":
                user_messages.append(message["content"])


        # Créer un agent React avec les outils nécessaires
        agent = self._llm.bind_tools([get_context_on_french_civil_code, get_specific_civil_code_article])
        processed_messages.insert(0, system_message)
        processed_messages = convert_prompt_to_langchain_messages(processed_messages)

        for i in range(1, self._max_iterations+1):
            # Appel au LLM
            response = agent.invoke(processed_messages)

            # Vérifier s'il y a des appels d'outils
            if response.tool_calls and i < self._max_iterations:
                
                
                # Traiter tous les appels d'outils
                tools_results = []
                for tool_call in response.tool_calls:
                    if tool_call["name"] == "get_context_on_french_civil_code":
                        print("🔧 Utilisation de l'outil de récupération de contexte")
                        content = str(get_context_on_french_civil_code.invoke(tool_call["args"]))
                        tools_results.append(ToolMessage(content=content, tool_call_id=tool_call["id"]))
                    elif tool_call["name"] == "get_previous_user_message":
                        print("🔧 Utilisation de l'outil de récupération du message utilisateur précédent")
                        content = str(get_previous_user_message.invoke(tool_call["args"]))
                        tools_results.append(ToolMessage(content=content, tool_call_id=tool_call["id"]))
                    elif tool_call["name"] == "get_specific_civil_code_article":
                        print("🔧 Utilisation de l'outil de récupération d'un article spécifique du code civil")
                        content = str(get_specific_civil_code_article.invoke(tool_call["args"]))
                        tools_results.append(ToolMessage(content=content, tool_call_id=tool_call["id"]))

                # Ajouter les résultats des outils aux processed_messages
                processed_messages.extend(tools_results)
                continue  # Retourner au début de la boucle pour traiter la réponse suivante
            
            else:
                # Pas d'appels d'outils, streamer la réponse finale
                for chunk in agent.stream(processed_messages):
                    yield chunk.content

                break  # Sortir de la boucle après avoir traité la réponse finale


    

if __name__ == "__main__":

    agent = OllamaAgent("qwen3:4b")
    #"llama3.2:3b-instruct-q5_1"

    message = {"role": "user", "content": " 4 * 7 = ?."}
    agent.process_message(message)
    
    