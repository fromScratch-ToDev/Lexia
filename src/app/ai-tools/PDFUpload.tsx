'use client';

import { useState } from 'react';
import { getApiUrl, API_CONFIG } from '@/lib/api-config';

interface UploadedFile {
    id: string;
    name: string;
    text: string;
    pages: number;
}

interface PDFUploadProps {
    uploadedFiles: UploadedFile[];
    onFilesUpdate: (files: UploadedFile[]) => void;
    isProcessingPDF: boolean;
    onProcessingChange: (isProcessing: boolean) => void;
}

export default function PDFUpload({ 
    uploadedFiles, 
    onFilesUpdate, 
    isProcessingPDF, 
    onProcessingChange 
}: PDFUploadProps) {
    const [isDragOver, setIsDragOver] = useState(false);

    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragOver(true);
    };

    const handleDragLeave = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragOver(false);
    };

    const handleDrop = async (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragOver(false);
        
        const files = Array.from(e.dataTransfer.files);
        const pdfFiles = files.filter(file => file.type === 'application/pdf');
        
        if (pdfFiles.length === 0) {
            alert('Veuillez déposer uniquement des fichiers PDF.');
            return;
        }

        for (const file of pdfFiles) {
            await extractPDFText(file);
        }
    };

    const extractPDFText = async (file: File) => {
        onProcessingChange(true);
        
        try {
            const formData = new FormData();
            formData.append('pdf', file);

            const response = await fetch(getApiUrl(API_CONFIG.ENDPOINTS.PDF_EXTRACT), {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                throw new Error('Erreur lors de l\'extraction du PDF');
            }

            const { text, filename, pages } = await response.json();
            
            // Ajouter le fichier à la liste des fichiers uploadés
            const newFile = {
                id: Math.random().toString(36).substr(2, 9),
                name: filename || file.name,
                text: text,
                pages: pages
            };
            onFilesUpdate([...uploadedFiles, newFile]);
            
        } catch (error) {
            console.error('Erreur:', error);
        } finally {
            onProcessingChange(false);
        }
    };

    const removeUploadedFile = (fileId: string) => {
        onFilesUpdate(uploadedFiles.filter(file => file.id !== fileId));
    };

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = Array.from(e.target.files || []);
        const pdfFiles = files.filter(file => file.type === 'application/pdf');
        
        if (pdfFiles.length === 0) {
            alert('Veuillez sélectionner uniquement des fichiers PDF.');
            return;
        }

        pdfFiles.forEach(file => {
            extractPDFText(file);
        });

        // Reset le input file
        e.target.value = '';
    };

    return (
        <div 
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
        >
            {isDragOver && (
                <div className="fixed inset-0 bg-blue-500 bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white p-8 rounded-lg shadow-lg text-center">
                        <div className="text-4xl mb-4">📄</div>
                        <p className="text-lg font-semibold">Déposez vos fichiers PDF ici</p>
                    </div>
                </div>
            )}

            {isProcessingPDF && (
                <div className="mb-3 p-2 bg-blue-50 border border-blue-200 rounded-lg text-blue-700 text-sm">
                    <div className="flex items-center">
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-700 mr-2"></div>
                        Extraction du texte en cours...
                    </div>
                </div>
            )}

            {/* Affichage des fichiers uploadés */}
            {uploadedFiles.length > 0 && (
                <div className="mb-3">
                    <div className="text-sm text-gray-600 mb-2">Fichiers joints :</div>
                    <div className="space-y-2">
                        {uploadedFiles.map((file) => (
                            <div
                                key={file.id}
                                className="flex items-center bg-green-50 border border-green-200 rounded-lg p-3 text-sm"
                            >
                                <div className="w-10 h-10 bg-red-500 rounded-lg flex items-center justify-center text-white text-xs font-bold mr-3 flex-shrink-0">
                                    PDF
                                </div>
                                <div className="flex-1 min-w-0 mr-3">
                                    <div className="font-medium text-green-800 word-wrap break-all">
                                        {file.name || 'Fichier PDF'}
                                    </div>
                                    <div className="text-green-600 text-xs mt-1">
                                        {file.pages} page{file.pages > 1 ? 's' : ''}
                                    </div>
                                </div>
                                <button
                                    onClick={() => removeUploadedFile(file.id)}
                                    className="text-green-600 hover:text-red-600 flex-shrink-0 w-6 h-6 flex items-center justify-center rounded-full hover:bg-red-100"
                                    title="Supprimer ce fichier"
                                >
                                    ✕
                                </button>
                            </div>
                        ))}
                    </div>
                </div>
            )}
            
            <div className="mb-2 text-xs text-gray-500">
                💡 Astuce : Glissez-déposez des fichiers PDF directement dans cette zone pour extraire leur contenu
            </div>
            
            {/* Bouton pour sélectionner des fichiers */}
            <div className="mb-3">
                <input
                    type="file"
                    id="fileInput"
                    multiple
                    accept=".pdf"
                    onChange={handleFileSelect}
                    className="hidden"
                />
               
            </div>
        </div>
    );
}

export type { UploadedFile };
