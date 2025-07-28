// Configuration de l'API Python
export const API_CONFIG = {
  BASE_URL: process.env.NEXT_PUBLIC_PYTHON_API_URL || 'http://localhost:8000',
  ENDPOINTS: {
    LOAD : '/api/load',
    AGENT: '/api/agent',
    ASK_CODE_CIVIL: '/api/ask-code-civil',
    RESUME: '/api/resume',
    PDF_EXTRACT: '/api/pdf-extract',
    HEALTH: '/health'
  } as const
};

// Fonction utilitaire pour construire les URLs complètes
export const getApiUrl = (endpoint: string): string => {
  return `${API_CONFIG.BASE_URL}${endpoint}`;
};

// Fonction pour vérifier la santé de l'API
export const checkApiHealth = async (): Promise<boolean> => {
  try {
    const response = await fetch(getApiUrl(API_CONFIG.ENDPOINTS.HEALTH));
    return response.ok;
  } catch (error) {
    console.error('Erreur lors de la vérification de l\'API:', error);
    return false;
  }
};
