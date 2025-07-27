'use client';

import './page.css'
import { useState, useEffect } from 'react';
import { marked } from 'marked';
import PDFUpload, { UploadedFile } from './PDFUpload';
import { getApiUrl, API_CONFIG, checkApiHealth } from '@/lib/api-config';
import katex from 'katex';
import 'katex/dist/katex.min.css';
import { ArrowUp, Copy, Check, Paperclip } from 'lucide-react';

// Configuration de marked pour le formatage Markdown
marked.setOptions({
    breaks: true, // Convertit les retours à la ligne simples en <br>
    gfm: true,    // Active GitHub Flavored Markdown
});

type RouteType = 'ask' | 'agent' | 'resume';

export default function AIToolsPage() {
    const [askMessages, setAskMessages] = useState<{ role: 'user' | 'assistant'; content: string; hasAttachments?: boolean; attachedFiles?: UploadedFile[] }[]>([]);
    const [agentMessages, setAgentMessages] = useState<{ role: 'user' | 'assistant'; content: string; hasAttachments?: boolean; attachedFiles?: UploadedFile[] }[]>([]);
    const [resumeMessages, setResumeMessages] = useState<{ role: 'user' | 'assistant'; content: string; hasAttachments?: boolean; attachedFiles?: UploadedFile[] }[]>([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [isProcessingPDF, setIsProcessingPDF] = useState(false);
    const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
    const [apiHealthy, setApiHealthy] = useState<boolean | null>(null);
    const [selectedRoute, setSelectedRoute] = useState<RouteType>('ask');
    const [copiedMessages, setCopiedMessages] = useState<Set<number>>(new Set());

    // Vérifier la santé de l'API au démarrage
    useEffect(() => {
        const checkHealth = async () => {
            const healthy = await checkApiHealth();
            setApiHealthy(healthy);
        };
        
        checkHealth();
        // Vérifier toutes les 30 secondes
        const interval = setInterval(checkHealth, 30000);
        
        return () => clearInterval(interval);
    }, []);

    // Fonction pour obtenir les messages et setter selon la route
    const getMessagesAndSetter = (route: RouteType) => {
        switch (route) {
            case 'ask':
                return { messages: askMessages, setMessages: setAskMessages };
            case 'agent':
                return { messages: agentMessages, setMessages: setAgentMessages };
            case 'resume':
                return { messages: resumeMessages, setMessages: setResumeMessages };
            default:
                return { messages: askMessages, setMessages: setAskMessages };
        }
    };

    // Fonction pour obtenir l'endpoint selon la route sélectionnée
    const getEndpoint = (route: RouteType): string => {
        switch (route) {
            case 'ask':
                return API_CONFIG.ENDPOINTS.ASK_CODE_CIVIL;
            case 'agent':
                return API_CONFIG.ENDPOINTS.AGENT;
            case 'resume':
                return API_CONFIG.ENDPOINTS.RESUME;
            default:
                return API_CONFIG.ENDPOINTS.ASK_CODE_CIVIL;
        }
    };

    // Fonction pour obtenir le titre en fonction de la route
    const getPageTitle = (route: RouteType): string => {
        switch (route) {
            case 'ask':
                return 'Assistant IA - Questions Code Civil';
            case 'agent':
                return 'Assistant IA - Conversation';
            case 'resume':
                return 'Assistant IA - Résumé de Documents';
            default:
                return 'Assistant IA';
        }
    };

    // Fonction pour gérer le streaming des réponses
    const streamBotResponse = async (messageHistory: { role: 'user' | 'assistant'; content: string }[], endpoint: string) => {
        const { setMessages } = getMessagesAndSetter(selectedRoute);
        
        const response = await fetch(getApiUrl(endpoint), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'text/event-stream',
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

                setMessages(prev => {
                    const newMessages = [...prev];
                    newMessages[botMessageIndex] = {
                        role: 'assistant' as const,
                        content: buffer
                    };
                    
                    return newMessages;
                });
            }
        } finally {
            reader.releaseLock();
        }
    };

    const sendMessage = async () => {
        if (!input.trim() && (selectedRoute !== 'resume' || uploadedFiles.length === 0)) return;
        
        const { messages, setMessages } = getMessagesAndSetter(selectedRoute);
        
        // Vérifier si l'API est disponible
        if (apiHealthy === false) {
            setMessages(prev => [...prev, {
                role: 'assistant' as const,
                content: 'L\'API Python n\'est pas disponible'
            }]);
            return;
        }

        // Construire le contenu du message avec les fichiers PDF (seulement pour RESUME)
        let messageContent = input;
        if (selectedRoute === 'resume' && uploadedFiles.length > 0) {
            const filesContent = uploadedFiles.map(file => 
                `\n\n--- Contenu du document "${file.name}" (${file.pages} pages) ---\n${file.text}\n--- Fin du document ---`
            ).join('\n');
            messageContent = input + filesContent;
        }

        const userMessage = { role: 'user' as const, content: messageContent };
        const displayMessage = { 
            role: 'user' as const, 
            content: input,
            hasAttachments: selectedRoute === 'resume' && uploadedFiles.length > 0,
            attachedFiles: selectedRoute === 'resume' && uploadedFiles.length > 0 ? [...uploadedFiles] : undefined
        };

        // Pour ASK et RESUME, réinitialiser les messages et ajouter le nouveau message
        let currentMessages;
        if (selectedRoute === 'ask' || selectedRoute === 'resume') {
            setMessages([displayMessage]);
            currentMessages = [userMessage];
        } else {
            // Pour AGENT, maintenir l'historique
            setMessages(prev => [...prev, displayMessage]);
            currentMessages = [...messages.map(msg => ({ role: msg.role, content: msg.content })), userMessage];
        }

        setInput('');
        if (selectedRoute === 'resume') {
            setUploadedFiles([]); // Vider les fichiers après envoi seulement pour RESUME
        }
        setIsLoading(true);

        try {
            const endpoint = getEndpoint(selectedRoute);
            await streamBotResponse(currentMessages, endpoint);
        } catch (error) {
            console.error('Erreur:', error);
            setMessages(prev => [...prev, {
                role: 'assistant' as const,
                content: 'Désolé, une erreur s\'est produite.'
            }]);
        } 
    };

    // Fonction pour copier du texte dans le presse-papier
    const copyToClipboard = async (text: string, messageIndex: number) => {
        try {
            await navigator.clipboard.writeText(text);
            setCopiedMessages(prev => new Set(prev).add(messageIndex));
            // Retirer la coche après 2 secondes
            setTimeout(() => {
                setCopiedMessages(prev => {
                    const newSet = new Set(prev);
                    newSet.delete(messageIndex);
                    return newSet;
                });
            }, 2000);
        } catch (err) {
            console.error('Erreur lors de la copie:', err);
            // Fallback pour les navigateurs qui ne supportent pas l'API clipboard
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            setCopiedMessages(prev => new Set(prev).add(messageIndex));
            // Retirer la coche après 2 secondes
            setTimeout(() => {
                setCopiedMessages(prev => {
                    const newSet = new Set(prev);
                    newSet.delete(messageIndex);
                    return newSet;
                });
            }, 2000);
        }
    };

    // Fonction pour formater le texte du LLM (Markdown vers HTML) avec marked
    const formatLLMText = (text: string): string => {
        if (!text) return '';
        
        try {
            // Traitement des formules mathématiques LaTeX avant le parsing Markdown
            let processedText = text
                // Formules block (entre $$ ... $$)
                .replace(/\$\$([^$]+)\$\$/g, (match, formula) => {
                    const html = katex.renderToString(formula.trim(), {
                        displayMode: true,
                        throwOnError: false
                    });
                    return `<div class="math-block my-4 text-center">${html}</div>`;
                })
                // Formules inline (entre $ ... $)
                .replace(/\$([^$]+)\$/g, (match, formula) => {
                    const html = katex.renderToString(formula.trim(), {
                        displayMode: false,
                        throwOnError: false
                    });
                    return `<span class="math-inline">${html}</span>`;
                });
            
            // Utilisation de marked.parse pour convertir le Markdown en HTML
            const htmlContent = marked.parse(processedText) as string;
            
            // Ajout de classes CSS personnalisées
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
            console.error('Erreur lors du formatage:', error);
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
                <h1 className="text-3xl font-bold text-gray-800 mb-6">{getPageTitle(selectedRoute)}</h1>

                <div className="bg-white w-3/5 srounded-lg shadow-lg fixed top-20 bottom-10 left-[20%] flex flex-col">
                    {/* Sélecteur de route */}
                    <div className="border-b p-4 bg-gray-50">
                        <label htmlFor="route-select" className="block text-sm font-medium text-gray-700 mb-2">
                            Mode d'assistance :
                        </label>
                        <select
                            id="route-select"
                            value={selectedRoute}
                            onChange={(e) => {
                                setSelectedRoute(e.target.value as RouteType);
                                setCopiedMessages(new Set()); // Réinitialiser les messages copiés
                            }}
                            className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            disabled={isLoading || isProcessingPDF}
                        >
                            <option value="ask">ASK - Question sur le code civil</option>
                            <option value="agent">AGENT - Conversation avec l'assistant</option>
                            <option value="resume">RESUME - Résumé de documents</option>
                        </select>
                    </div>

                    {/* Messages */}
                    <div className="flex-1  p-4 overflow-y-auto space-y-4">
                        {(() => {
                            const { messages } = getMessagesAndSetter(selectedRoute);
                            return messages.length === 0 ? (
                                <div className="text-center text-gray-500 mt-20">
                                    <p>
                                        {selectedRoute === 'ask' 
                                            ? 'Posez une question sur le code civil'
                                            : selectedRoute === 'agent'
                                            ? 'Commencez une conversation avec l\'assistant IA'
                                            : 'Téléchargez un document PDF pour le résumer'
                                        }
                                    </p>
                                </div>
                            ) : (
                                messages.map((message, index) => (
                                  
                                    <div
                                        key={index}
                                        className={`flex flex-col ${message.role === 'user' ? 'items-end' : 'items-start' }`}
                                    > 
                                        <div
                                            className={` px-4 py-2 rounded-lg break-words ${
                                                message.role === 'user'
                                                    ? 'bg-gray-200 text-gray-800 max-w-xs lg:max-w-2xl'
                                                    : 'text-gray-800 text-left lg:max-w-4xl'
                                            } ${message.content.trim() === '' && ' hidden '}`}
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
                                        {/* Icône de copie pour les messages assistant */}
                                        {message.role === 'assistant' && message.content.trim() !== '' && (
                                            <button
                                                onClick={() => copyToClipboard(message.content, index)}
                                                className="mt-1 p-2 rounded-md cursor-pointer z-10 hover:bg-gray-200 "
                                                title={copiedMessages.has(index) ? "Copié !" : "Copier le message"}
                                            >
                                                {copiedMessages.has(index) ? (
                                                    <Check size={16} className="text-green-500" />
                                                ) : (
                                                    <Copy size={16} className="text-gray-500" />
                                                )}
                                            </button>
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
                            );
                        })()}
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
                    <div className="border-t p-4 ">
                        {/* Upload PDF seulement pour RESUME */}
                        {selectedRoute === 'resume' && (
                            <PDFUpload
                                uploadedFiles={uploadedFiles}
                                onFilesUpdate={setUploadedFiles}
                                isProcessingPDF={isProcessingPDF}
                                onProcessingChange={setIsProcessingPDF}
                            />
                        )}
                        <div className='flex flex-col border border-gray-300 rounded-lg px-4 py-2 chat-bar '>

                            <textarea
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
                                placeholder={
                                    selectedRoute === 'ask' 
                                    ? "Posez votre question sur le code civil..."
                                    : selectedRoute === 'agent'
                                    ? "Commencez une conversation avec l'assistant..."
                                    : "Tapez votre message ou glissez-déposez des fichiers PDF..."
                                }
                                className=" w-full focus:outline-none  resize-none  overflow-y-auto chat-bar-textarea "
                                disabled={isLoading || isProcessingPDF}
                                rows={1}
                                style={{ height: 'auto', minHeight: '2.75rem' }}
                                onInput={(e) => {
                                    const target = e.target as HTMLTextAreaElement;
                                    target.style.height = 'auto';
                                    target.style.height = Math.min(target.scrollHeight/16, 9.5) + 'rem';
                                }}
                                />
                                <div className="flex  ">
                                {selectedRoute === 'resume' && (
                                    <button
                                        onClick={() => document.getElementById('fileInput')?.click()}
                                        disabled={isProcessingPDF}
                                        className=" cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
                                    >
                                        <Paperclip color='#6a7282' size={20}/>   

                                    </button>
                                )}
                                <div className='flex-1 flex justify-end'>
                                    <button
                                        onClick={sendMessage}
                                        disabled={
                                            isLoading ||
                                            isProcessingPDF ||
                                            (!input.trim() && (selectedRoute !== 'resume' || uploadedFiles.length === 0))
                                        }
                                        className="cursor-pointer w-8 h-8 rounded-full flex border border-gray-500 items-center justify-center transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                        >
                                            <ArrowUp color="#6a7282" />
                                    </button>
                                </div>
                            </div>


                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}