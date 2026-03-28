
import React, { useRef } from 'react';
import { Icon } from './Icon';
import { Loader } from './Loader';
import type { UploadedFile } from '../types';

interface DocumentInputProps {
    documentText: string;
    setDocumentText: (text: string) => void;
    uploadedFile: UploadedFile | null;
    setUploadedFile: (file: UploadedFile | null) => void;
    onAnalyze: () => void;
    isLoading: boolean;
}

export const DocumentInput: React.FC<DocumentInputProps> = ({ documentText, setDocumentText, uploadedFile, setUploadedFile, onAnalyze, isLoading }) => {
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleUploadClick = () => {
        fileInputRef.current?.click();
    };

    const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file) return;

        event.target.value = '';

        const validMimeTypes = [
            'text/plain', 
            'application/pdf', 
        ];

        if (!validMimeTypes.includes(file.type)) {
            alert('Unsupported file type. Please upload a .txt or .pdf file.');
            return;
        }

        const reader = new FileReader();
        reader.onload = (e) => {
            const dataUrl = e.target?.result as string;
            const base64Data = dataUrl.substring(dataUrl.indexOf(',') + 1);
            setUploadedFile({
                name: file.name,
                mimeType: file.type,
                data: base64Data,
            });
            setDocumentText(''); // Clear text area when file is uploaded
        };
        reader.onerror = () => {
            alert('Error reading the file.');
        };
        reader.readAsDataURL(file);
    };

    const handleRemoveFile = () => {
        setUploadedFile(null);
    }

    return (
        <div className="bg-white/95 p-6 rounded-3xl shadow-lg border border-slate-200">
            <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                <h2 className="text-xl font-bold text-slate-800 flex items-center">
                <Icon name="file" className="h-6 w-6 mr-2 text-cyan-700" />
                Your Legal Document
                </h2>
                <span className="text-xs font-semibold text-cyan-800 bg-cyan-50 border border-cyan-200 rounded-full px-2.5 py-1">
                    .txt / .pdf supported
                </span>
            </div>
            <p className="text-slate-500 mb-4 text-sm leading-relaxed">
                Paste the content of your legal document below, or upload a .txt or .pdf file.
            </p>

            {uploadedFile ? (
                <div className="w-full h-64 p-5 border border-cyan-200 rounded-2xl bg-gradient-to-b from-cyan-50 to-white flex flex-col items-center justify-center">
                    <div className="h-14 w-14 rounded-2xl bg-white border border-cyan-100 flex items-center justify-center">
                        <Icon name="document" className="h-8 w-8 text-cyan-700" />
                    </div>
                    <p className="font-semibold mt-3 text-slate-800 text-center break-all">{uploadedFile.name}</p>
                    <p className="text-xs text-slate-500 mt-1">Document uploaded and ready for analysis</p>
                    <button 
                        onClick={handleRemoveFile} 
                        className="mt-4 flex items-center text-sm text-red-600 hover:text-red-800 font-semibold"
                        disabled={isLoading}
                    >
                        <Icon name="remove" className="h-4 w-4 mr-1" />
                        Remove file
                    </button>
                </div>
            ) : (
                <div>
                    <textarea
                        value={documentText}
                        onChange={(e) => setDocumentText(e.target.value)}
                        placeholder="Paste legal text here..."
                        className="w-full h-64 p-4 border border-slate-300 rounded-2xl focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 transition duration-150 ease-in-out resize-y"
                        disabled={isLoading}
                    />
                    <div className="mt-2 flex items-center justify-between text-xs text-slate-500">
                        <span>Tip: Include full clauses for better risk detection</span>
                        <span>{documentText.length} characters</span>
                    </div>
                </div>
            )}
            
            <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileChange}
                className="hidden"
                accept=".txt,.pdf,text/plain,application/pdf"
            />
            <div className="mt-5 flex flex-col sm:flex-row gap-2">
                 <button
                    onClick={handleUploadClick}
                    disabled={isLoading}
                    className="w-full sm:w-auto flex items-center justify-center bg-white text-slate-700 font-semibold py-3 px-4 rounded-xl border border-slate-300 hover:bg-slate-50 disabled:bg-slate-100 disabled:cursor-not-allowed transition duration-150 ease-in-out"
                >
                    <Icon name="upload" className="h-5 w-5 mr-2" />
                    Upload Document
                </button>
                <button
                    onClick={onAnalyze}
                    disabled={isLoading || (!documentText.trim() && !uploadedFile)}
                    className="w-full sm:flex-1 flex items-center justify-center bg-gradient-to-r from-cyan-700 to-teal-700 text-white font-semibold py-3 px-4 rounded-xl hover:from-cyan-800 hover:to-teal-800 disabled:from-cyan-300 disabled:to-teal-300 disabled:cursor-not-allowed transition duration-150 ease-in-out shadow-sm"
                >
                    {isLoading ? (
                        <>
                            <Loader />
                            Analyzing...
                        </>
                    ) : (
                        <>
                        <Icon name="sparkles" className="h-5 w-5 mr-2" />
                            Analyze Document
                        </>
                    )}
                </button>
            </div>
            <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-2">
                <div className="text-xs text-slate-600 bg-slate-50 border border-slate-200 rounded-xl px-3 py-2">Step 1: Upload or paste your document</div>
                <div className="text-xs text-slate-600 bg-slate-50 border border-slate-200 rounded-xl px-3 py-2">Step 2: Click Analyze to generate insights</div>
            </div>
        </div>
    );
};