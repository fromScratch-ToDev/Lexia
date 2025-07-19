'use client';

import { useState } from 'react';
import PDFUpload, { UploadedFile } from './PDFUpload';


const preprompt = `Je suis un assistant juridique intelligent, conçu pour accompagner des professionnels du droit (avocats, juristes d’entreprise, cabinets) en leur faisant gagner un temps précieux sur leurs tâches rédactionnelles et documentaires.

Mon rôle :

    Résumer avec précision et clarté des documents juridiques (contrats, jugements, CGV, mémos…).

    Corriger, reformuler ou simplifier des clauses juridiques complexes ou maladroites.

    Identifier les incohérences, risques ou contradictions dans un texte juridique.

    Assister dans la relecture, l’organisation et la structuration de contenus juridiques.

    Extraire les points essentiels et les classer de manière professionnelle.

Caractéristiques :

    Mes réponses sont structurées, rigoureuses, claires et adaptées à un usage professionnel.

    Je ne donne aucun conseil juridique personnalisé, mais je fournis des éléments d’analyse ou de reformulation basés sur les bonnes pratiques et les principes juridiques généraux.

    Je cite des sources ou des références juridiques uniquement lorsque cela est utile et pertinent.

Il suffit de me fournir un contenu ou un objectif, et j’agis comme un collaborateur discret, fiable et rapide.
`;

export default function AIToolsPage() {
    const [messages, setMessages] = useState<{ role: 'user' | 'assistant'; content: string }[]>([{ role: 'assistant', content: preprompt }]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [isProcessingPDF, setIsProcessingPDF] = useState(false);
    const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);

    const sendMessage = async () => {
        if (!input.trim() && uploadedFiles.length === 0) return;

        // Construire le contenu du message avec les fichiers PDF
        let messageContent = input;
        if (uploadedFiles.length > 0) {
            const filesContent = uploadedFiles.map(file => 
                `\n\n--- Contenu du document "${file.name}" (${file.pages} pages) ---\n${file.text}\n--- Fin du document ---`
            ).join('\n');
            messageContent = input + filesContent;
        }

        const userMessage = { role: 'user' as const, content: messageContent };
        const displayMessage = { role: 'user' as const, content: input }; // Message à afficher sans le contenu PDF
    
        setMessages(prev => [...prev, displayMessage]);          
        setInput('');
        setUploadedFiles([]); // Vider les fichiers après envoi
        setIsLoading(true);

        try {
            await streamBotResponse([...messages, userMessage]);
        } catch (error) {
            console.error('Erreur:', error);
            setMessages(prev => [...prev, {
                role: 'assistant' as const,
                content: 'Désolé, une erreur s\'est produite.'
            }]);
        } finally {
            console.log(messages);
            
        }
    };

    const streamBotResponse = async (messageHistory: { role: 'user' | 'assistant'; content: string }[]) => {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ messages: messageHistory }),
        });

        if (!response.ok) {
            throw new Error('Failed to fetch assistant response');
        }

        const reader = response.body?.getReader();
        setIsLoading(false);
        
        if (!reader) {
            throw new Error('No response body');
        }

        // Add an empty assistant message that we'll update
        let botMessageIndex = -1;
        setMessages(prev => {
            const newMessages = [...prev, { role: 'assistant' as const, content: '' }];
            botMessageIndex = newMessages.length - 1;
            return newMessages;
        });

        const decoder = new TextDecoder();
        let buffer = '';

        try {
            while (true) {
                const { done, value } = await reader.read();
                
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                
                // Process complete lines, keep the last incomplete line in buffer
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            
                            if (data.error) {
                                setMessages(prev => {
                                    const newMessages = [...prev];
                                    newMessages[botMessageIndex] = {
                                        role: 'assistant' as const,
                                        content: data.content
                                    };
                                    return newMessages;
                                });
                                break;
                            }

                            // Update the assistant message with the latest full content
                            if (data.fullContent !== undefined) {
                                setMessages(prev => {
                                    const newMessages = [...prev];
                                    newMessages[botMessageIndex] = {
                                        role: 'assistant' as const,
                                        content: data.fullContent
                                    };
                                    return newMessages;
                                });
                            }

                            if (data.done) {
                                break;
                            }
                        } catch (e) {
                            console.error('Error parsing SSE data:', e);
                        }
                    }
                }
            }
        } finally {
            reader.releaseLock();
        }
    };

    // Fonction pour formater le texte du LLM
    const formatLLMText = (text: string): string => {
        if (!text) return '';
        
        // Remplacer les astérisques simples par des retours à la ligne
        let formatted = text.replace(/(?<!\*)\*(?!\*)/g, '<br><br>');
        
        // Remplacer le texte entre ** par du texte en gras
        formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        return formatted;
    }; 

    return (
        <div 
            className="min-h-screen bg-gray-50 p-4"
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => e.preventDefault()}
        >
            <div className=" mx-auto w-4/5 text-center">
                <h1 className="text-3xl font-bold text-gray-800 mb-6">Assistant IA</h1>

                <div className="bg-white w-3/5 srounded-lg shadow-lg fixed top-20 bottom-10 left-[20%] flex flex-col">
                    {/* Messages */}
                    <div className="flex-1 p-4 overflow-y-auto space-y-4">
                        {messages.length === 0 ? (
                            <div className="text-center text-gray-500 mt-20">
                                <p>Commencez une conversation avec l'assistant IA</p>
                            </div>
                        ) : (
                            messages.map((message, index) => (
                                index !== 0 &&
                                <div
                                    key={index}
                                    className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                                >
                                    <div
                                        className={`max-w-xs lg:max-w-lg px-4 py-2 rounded-lg ${
                                            message.role === 'user'
                                                ? 'bg-blue-500 text-white'
                                                : 'bg-gray-200 text-gray-800'
                                        }`}
                                    >
                                        {message.role === 'assistant' ? (
                                            <div 
                                                dangerouslySetInnerHTML={{ 
                                                    __html: formatLLMText(message.content) 
                                                }} 
                                            />
                                        ) : (
                                            message.content
                                        )}
                                    </div>
                                </div>
                            ))
                        )}
                        {isLoading && (
                            <div className="flex justify-start">
                                <div className="bg-gray-200 text-gray-800 px-4 py-2 rounded-lg">
                                    <div className="flex space-x-1">
                                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Input */}
                    <div className="border-t p-4">
                        <PDFUpload
                            uploadedFiles={uploadedFiles}
                            onFilesUpdate={setUploadedFiles}
                            isProcessingPDF={isProcessingPDF}
                            onProcessingChange={setIsProcessingPDF}
                        />
                        
                        <div className="flex space-x-2">
                            <textarea
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
                                placeholder="Tapez votre message ou glissez-déposez des fichiers PDF..."
                                className="flex-1 border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[60px] resize-none"
                                disabled={isLoading || isProcessingPDF}
                                rows={3}
                            />
                            <button
                                onClick={sendMessage}
                                disabled={isLoading || isProcessingPDF || (!input.trim() && uploadedFiles.length === 0)}
                                className="bg-blue-500 text-white px-6 py-2 rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed self-end"
                            >
                                Envoyer
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}