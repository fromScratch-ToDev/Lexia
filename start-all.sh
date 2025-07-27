#!/bin/bash

# Script pour démarrer l'ensemble de l'application

echo "🚀 Démarrage de l'Assistant IA complet..."

# Vérifier les prérequis
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 n'est pas installé"
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo "❌ Node.js n'est pas installé"
    exit 1
fi

if ! command -v ollama &> /dev/null; then
    echo "❌ Ollama n'est pas installé"
    echo "   Téléchargez depuis: https://ollama.ai/"
    exit 1
fi

# Vérifier qu'au moins un modèle est disponible
if ! ollama list | grep -q "qwen3:4b\|llama"; then
    echo "⚠️  Aucun modèle compatible trouvé. Installation du modèle par défaut..."
    ollama pull qwen3:4b
fi

echo "✅ Tous les prérequis sont satisfaits"

# Démarrer l'API Python en arrière-plan
echo "🐍 Démarrage de l'API Python..."
cd python-api

# Créer et activer l'environnement virtuel si nécessaire
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt

# Démarrer l'API en arrière-plan
python3 main.py &
API_PID=$!

cd ..

# Attendre que l'API soit prête
echo "⏳ Attente du démarrage de l'API..."
for i in {1..300}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ API Python prête sur http://localhost:8000"
        break
    fi
    if [ $i -eq 900 ]; then
        echo "❌ L'API Python n'a pas démarré dans les temps"
        kill $API_PID 2>/dev/null
        exit 1
    fi
    sleep 1
done

# Installer les dépendances Next.js si nécessaire
if [ ! -d "node_modules" ]; then
    echo "📦 Installation des dépendances Next.js..."
    npm install
fi

# Fonction de nettoyage
cleanup() {
    echo "🧹 Arrêt des services..."
    kill $API_PID 2>/dev/null
    exit
}

# Capturer les signaux d'arrêt
trap cleanup SIGINT SIGTERM

echo "🌐 Démarrage de l'application Next.js sur http://localhost:3000"
echo "📚 Documentation API disponible sur http://localhost:8000/docs"
echo "💡 Appuyez sur Ctrl+C pour arrêter tous les services"

# Démarrer Next.js
npm run dev
