'use client';

import { useState } from 'react';
import { marked } from 'marked';
import PDFUpload, { UploadedFile } from './PDFUpload';

// Configuration de marked pour le formatage Markdown
marked.setOptions({
    breaks: true, // Convertit les retours à la ligne simples en <br>
    gfm: true,    // Active GitHub Flavored Markdown
});

const preprompt = `
Je suis un assistant juridique français, conçu pour assister des professionnels du droit (avocats, juristes d’entreprise, cabinets) en leur faisant gagner un temps précieux sur leurs tâches rédactionnelles et documentaires.

Contexte d'utilisation :
- Je suis utilisé localement sur l’ordinateur de l’utilisateur. 
- Toutes les données traitées sont strictement confidentielles et ne quittent jamais l’environnement local.

Mon rôle :
- Résumer avec précision et clarté des documents juridiques (contrats, jugements, CGV, mémos…).
- Corriger, reformuler ou simplifier des clauses juridiques complexes ou maladroites.
- Identifier les incohérences, risques ou contradictions dans un texte juridique.
- Assister dans la relecture, l’organisation et la structuration de contenus juridiques.
- Extraire les points essentiels et les classer de manière professionnelle.

Mes caractéristiques :
- Mes réponses sont **structurées**, **rigoureuses**, **claires** et **adaptées à un usage professionnel**.
- J’utilise une **mise en page aérée**, avec des paragraphes distincts, des listes claires et des titres si nécessaire, pour améliorer la **lisibilité**.
- Je veille à produire des textes **faciles à lire**, même pour des lecteurs non juristes.
- Je ne fournis **aucun conseil juridique personnalisé**, mais des analyses, reformulations et suggestions basées sur les bonnes pratiques et les principes juridiques généraux.
- Je cite des sources ou des références juridiques uniquement lorsqu'elles sont utiles et pertinentes.

Il suffit de me fournir un contenu ou un objectif, et j’agis comme un collaborateur discret, fiable et rapide.
`;


export default function AIToolsPage() {
    const [messages, setMessages] = useState<{ role: 'user' | 'assistant'; content: string; hasAttachments?: boolean; attachedFiles?: UploadedFile[] }[]>([{ role: 'assistant', content: preprompt }]);
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
        const displayMessage = { 
            role: 'user' as const, 
            content: input,
            hasAttachments: uploadedFiles.length > 0,
            attachedFiles: uploadedFiles.length > 0 ? [...uploadedFiles] : undefined
        }; // Message à afficher sans le contenu PDF
    
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


    // Fonction pour formater le texte du LLM (Markdown vers HTML) avec marked
    const formatLLMText = (text: string): string => {
        if (!text) return '';
        
        try {
            // Utilisation de marked.parse pour convertir le Markdown en HTML de façon synchrone
            const htmlContent = marked.parse(text) as string;
            
            // Ajout de classes CSS personnalisées pour améliorer le style
            return htmlContent
                .replace(/<p>/g, '<p class="mb-4">')
                .replace(/<ul>/g, '<ul class="list-disc ml-6 mb-4">')
                .replace(/<ol>/g, '<ol class="list-decimal ml-6 mb-4">')
                .replace(/<hr>/g, '<hr class="my-4 border-gray-300" />')
                .replace(/<h1>/g, '<h1 class="text-xl font-bold mb-4">')
                .replace(/<h2>/g, '<h2 class="text-lg font-bold mb-3">')
                .replace(/<h3>/g, '<h3 class="text-md font-bold mb-2">')
                .replace(/<blockquote>/g, '<blockquote class="border-l-4 border-gray-300 pl-4 italic my-4">');
        } catch (error) {
            console.error('Erreur lors du formatage Markdown:', error);
            // Retour au texte brut en cas d'erreur
            return text.replace(/\n/g, '<br />');
        }
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
                                    className={`flex flex-col ${message.role === 'user' ? 'items-end' : 'items-start' }`}
                                >
                                    <div
                                        className={` px-4 py-2 rounded-lg break-words ${
                                            message.role === 'user'
                                                ? 'bg-blue-500 text-white max-w-xs lg:max-w-2xl'
                                                : 'bg-gray-200 text-gray-800 text-left lg:max-w-4xl'
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
                                        {/* Affichage des fichiers attachés pour les messages utilisateur */}
                                        {message.role === 'user' && message.hasAttachments && message.attachedFiles && (
                                            <div className="mb-2 pb-2 border-b border-blue-400/30 ">
                                                <div className="flex items-center text-xs  mb-1">
                                                    <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                                                        <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" />
                                                    </svg>
                                                    Fichiers joints :
                                                </div>
                                                {message.attachedFiles.map((file, fileIndex) => (
                                                    <div key={fileIndex} className="flex items-center text-xs bg-blue-600/30 rounded p-2 mb-1">
                                                        <div className="w-6 h-6 bg-red-500 rounded text-white text-[10px] font-bold flex items-center justify-center mr-2 flex-shrink-0">
                                                            PDF
                                                        </div>
                                                        <div className="flex-1 min-w-0">
                                                            <div className="truncate font-medium ">{file.name}</div>
                                                            <div className=" text-[10px]">
                                                                {file.pages} page{file.pages > 1 ? 's' : ''}
                                                            </div>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
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