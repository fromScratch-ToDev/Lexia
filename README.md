# Assistant IA Landing Page

## Prérequis

Avant de commencer, assurez-vous d'avoir installé :

- [Ollama](https://ollama.com/) sur votre système
- Un modèle LLM téléchargé via Ollama (par exemple : `ollama pull gemma3n:e4b`)

Pour vérifier qu'Ollama fonctionne correctement :

```bash
ollama list
```

Cette commande doit afficher les modèles disponibles sur votre machine.
 
## Installation et démarrage

Après avoir cloné le projet, installez les dépendances :

```bash
npm install
```

Puis lancez le serveur de développement :

```bash
npm run dev
```

Ouvrez [http://localhost:3000] dans votre navigateur pour voir le résultat.

