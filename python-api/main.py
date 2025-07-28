import re
from datetime import datetime
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List
from pdf_extractor import extract_pdf_text
import torch
from OllamaAgent import OllamaAgent, vectorstore, llm
from utils import convert_prompt_to_langchain_messages, get_specific_civil_code_article
from dict import find_numbers_in_string

# ------------------------------------------------------------------
# 0.  Configuration
# ------------------------------------------------------------------

is_load = False

# Création de l'application FastAPI
app = FastAPI(title="Assistant IA API", version="1.0.0")

# Initialiser l'agent RAG
rag_agent = OllamaAgent()

torch.cuda.empty_cache()

# ------------------------------------------------------------------
# 1.  CORS
# ------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------
# 2.  Modèles Pydantic
# ------------------------------------------------------------------
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]

# ------------------------------------------------------------------
# 3.  Utilitaires
# ------------------------------------------------------------------

def remove_think_tags(text: str) -> str:
    """Supprime les balises <think>...</think>"""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)

# ------------------------------------------------------------------
# 4.  Endpoints
# ------------------------------------------------------------------

@app.post("/api/resume")
async def resume_endpoint(request: ChatRequest):
    """
    Endpoint pour résumer un texte.
    """
    try:
        messages = [{"role": m.role, "content": m.content} for m in request.messages]

        # Ajouter un message système pour guider le LLM
        system_message = {
            "role": "system", 
            "content": "Vous êtes un assistant IA spécialisé dans la synthèse de textes juridiques. Votre tâche est de produire des résumés accessibles mais professionnels destinés à des praticiens du droit. Vos résumés doivent : 1) Être plus accessibles que le document original tout en conservant la précision juridique, 2) Être bien structurés avec des sections claires (contexte, éléments clés, implications, conclusions), 3) Être exhaustifs en couvrant tous les aspects importants du texte, 4) Maintenir un ton professionnel adapté aux juristes. Structurez votre résumé de manière logique et hiérarchisée."
        }
        messages.insert(0, system_message)

        messages = convert_prompt_to_langchain_messages(messages)

        def generate():
            for chunk in llm.stream(messages):
                yield remove_think_tags(chunk.content)
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du résumé: {str(e)}")

@app.post("/api/ask-code-civil")
async def ask_code_civil_endpoint(request: ChatRequest):
    """
    Endpoint pour interroger le code civil français.
    """
    
    try:
        
        messages = [{"role": m.role, "content": m.content} for m in request.messages]

        # Ajouter un message système pour guider le LLM
        system_message = {
            "role": "system", 
            "content": "Vous êtes un assistant juridique spécialisé dans le code civil français. Vous recevrez des informations juridiques dont certaines peuvent être pertinentes pour répondre à la question posée. Analysez ces informations et utilisez uniquement celles qui sont directement liées à la question de l'utilisateur. Ignorez les éléments non pertinents. Répondez de manière naturelle en vous basant exclusivement sur les informations pertinentes disponibles. Citez vos sources en mentionnant les articles pertinents et mettez entre guillemets et en italiques toutes les citations textuelles que vous faites."
        }
        messages.insert(0, system_message)

        for message in reversed(messages):
            if message["role"] == "user":
                user_messages = message["content"]
                message["content"] = "QUESTION DE L'UTILISATEUR: " + user_messages
                break

        context = "CONTEXTE: " + vectorstore.get_context(user_messages)
        print(context)
        article_number = find_numbers_in_string(user_messages)
        for article in article_number:
            art = get_specific_civil_code_article(article)
            context += f"\n\n{art}"
            
        messages.append({"role": "user", "content": context})
        messages = convert_prompt_to_langchain_messages(messages)

        def generate():
            for chunk in llm.stream(messages):
                yield chunk.content
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'interrogation du code civil: {str(e)}")

@app.post("/api/agent")
async def agent_chat_endpoint(request: ChatRequest):
    """
    Endpoint intelligent qui décide automatiquement s'il faut du contexte
    """
    try:
        messages = [{"role": m.role, "content": m.content} for m in request.messages]

        
        return StreamingResponse(
            rag_agent.process_message(messages),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du traitement intelligent: {str(e)}")


@app.post("/api/pdf-extract")
async def pdf_extract_endpoint(pdf: UploadFile = File(...)):
    if not pdf.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Le fichier doit être un PDF")
    try:
        return await extract_pdf_text(pdf)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/load")
async def load():
    global is_load
    if not is_load:
        llm.invoke("Bonjour")
        is_load = True
    return {"message": "Chargement des ressources..."}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/")
async def root():
    return {"message": "Assistant IA API", "version": "1.0.0"}

# ------------------------------------------------------------------
# 5.  Lancement
# ------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)