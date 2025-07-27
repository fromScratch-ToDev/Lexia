from fastapi import UploadFile, File, HTTPException
import pdfplumber
import PyPDF2
from io import BytesIO

async def extract_pdf_text(file: UploadFile) -> dict:
    """Extrait le texte d'un fichier PDF"""
    try:
        # Lire le contenu du fichier
        content = await file.read()
        
        # Méthode 1: Essayer avec pdfplumber (meilleure qualité)
        try:
            with BytesIO(content) as pdf_buffer:
                with pdfplumber.open(pdf_buffer) as pdf:
                    text = ""
                    page_count = len(pdf.pages)
                    
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                    
                    if text.strip():
                        return {
                            "text": text.strip(),
                            "filename": file.filename,
                            "pages": page_count,
                            "method": "pdfplumber"
                        }
        except Exception as e:
            print(f"Erreur avec pdfplumber: {e}")
        
        # Méthode 2: Fallback avec PyPDF2
        try:
            with BytesIO(content) as pdf_buffer:
                pdf_reader = PyPDF2.PdfReader(pdf_buffer)
                text = ""
                page_count = len(pdf_reader.pages)
                
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                
                if text.strip():
                    return {
                        "text": text.strip(),
                        "filename": file.filename,
                        "pages": page_count,
                        "method": "PyPDF2"
                    }
        except Exception as e:
            print(f"Erreur avec PyPDF2: {e}")
        
        # Si aucune méthode n'a fonctionné
        raise HTTPException(
            status_code=400, 
            detail="Impossible d'extraire le texte de ce PDF. Le fichier pourrait être corrompu ou protégé."
        )
        
    except Exception as e:
        print(f"Erreur générale lors de l'extraction PDF: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Erreur lors du traitement du PDF: {str(e)}"
        )