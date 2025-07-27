import os
import re

def clean_file(file_path: str, output_path: str = None):
    """
    Supprime toutes les occurrences de la chaîne spécifique d'un fichier .txt
    et normalise les retours à la ligne multiples
    
    Args:
        file_path: Chemin vers le fichier à nettoyer
        output_path: Chemin de sortie (optionnel, par défaut remplace le fichier original)
    """
    # Chaîne à supprimer
    text_to_remove = "Code civil - Dernière modification le 25 juin 2025 - Document généré le 19 juillet 2025"
    
    try:
        # Lire le fichier
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Compter les occurrences avant nettoyage
        occurrences_count = content.count(text_to_remove)
        print(f"Trouvé {occurrences_count} occurrence(s) à supprimer dans {file_path}")
        
        # Supprimer toutes les occurrences
        cleaned_content = content.replace(text_to_remove, "")
        
        # Remplacer les retours à la ligne supérieurs à 2 par exactement 2
        cleaned_content = re.sub(r'\n{3,}', '\n\n', cleaned_content)
        
        # Définir le fichier de sortie
        if output_path is None:
            output_path = file_path
        
        # Écrire le contenu nettoyé
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(cleaned_content)
        
        print(f"Fichier nettoyé sauvegardé: {output_path}")
        print(f"{occurrences_count} occurrence(s) supprimée(s)")
        
    except FileNotFoundError:
        print(f"Erreur: Le fichier {file_path} n'existe pas")
    except Exception as e:
        print(f"Erreur lors du traitement: {e}")

def clean_directory(directory_path: str):
    """
    Nettoie tous les fichiers .txt d'un répertoire
    
    Args:
        directory_path: Chemin vers le répertoire contenant les fichiers .txt
    """
    if not os.path.exists(directory_path):
        print(f"Erreur: Le répertoire {directory_path} n'existe pas")
        return
    
    txt_files = [f for f in os.listdir(directory_path) if f.endswith('.txt')]
    
    if not txt_files:
        print(f"Aucun fichier .txt trouvé dans {directory_path}")
        return
    
    print(f"Trouvé {len(txt_files)} fichier(s) .txt à traiter")
    
    for filename in txt_files:
        file_path = os.path.join(directory_path, filename)
        print(f"\nTraitement de: {filename}")
        clean_file(file_path)

if __name__ == "__main__":
    # Option 1: Nettoyer un fichier spécifique
    clean_file("./documents/code-civil.txt")
    
    # Option 2: Nettoyer tous les fichiers .txt d'un répertoire
    #clean_directory("documents")
    
    # Option 3: Nettoyer avec sauvegarde (garde l'original)
    # clean_file("documents/original.txt", "documents/original_cleaned.txt")