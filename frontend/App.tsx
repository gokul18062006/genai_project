import React, { useState, useCallback } from 'react';
import { Header } from './components/Header';
import { DocumentInput } from './components/DocumentInput';
import { AnalysisOutput } from './components/AnalysisOutput';
import { ChatInterface } from './components/ChatInterface';
import type { AnalysisResult, ChatMessage, UploadedFile } from '../types';
import { analyzeDocument, translateText, createChatSession, continueChat } from '../backend/services/apiService';
import { LANGUAGES } from './constants';
import { Icon } from './components/Icon';

const App: React.FC = () => {
    const [documentText, setDocumentText] = useState<string>('');
    const [uploadedFile, setUploadedFile] = useState<UploadedFile | null>(null);
    const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);

    const [targetLanguage, setTargetLanguage] = useState<string>(LANGUAGES[0].code);
    const [translatedText, setTranslatedText] = useState<string>('');
    const [isTranslating, setIsTranslating] = useState<boolean>(false);

    const [chatSessionId, setChatSessionId] = useState<string | null>(null);
    const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
    const [isChatting, setIsChatting] = useState<boolean>(false);

    const handleAnalyze = useCallback(async () => {
        if (!documentText.trim() && !uploadedFile) {
            setError('Please enter some legal text or upload a document to analyze.');
            return;
        }
        setIsLoading(true);
        setError(null);
        setAnalysisResult(null);
        setTranslatedText('');
        setChatMessages([]);
        setChatSessionId(null);

        try {
            const analysisPayload = { documentText: documentText.trim(), file: uploadedFile };
            const result = await analyzeDocument(analysisPayload);
            setAnalysisResult(result);

            // Initialize chat session after successful analysis
            const sessionId = await createChatSession(analysisPayload);
            setChatSessionId(sessionId);
            setChatMessages([{ sender: 'ai', text: 'I have read the document. How can I help you?' }]);

        } catch (err) {
            console.error(err);
            setError('Failed to analyze the document. Please check your API key and try again.');
        } finally {
            setIsLoading(false);
        }
    }, [documentText, uploadedFile]);
    
    const handleTranslate = useCallback(async () => {
        if (!analysisResult?.simplifiedText) {
            setError('Please analyze a document first to generate simplified text for translation.');
            return;
        }
        setIsTranslating(true);
        try {
            const translation = await translateText(analysisResult.simplifiedText, targetLanguage);
            setTranslatedText(translation);
        } catch (err) {
            console.error(err);
            setError('Failed to translate the text.');
        } finally {
            setIsTranslating(false);
        }
    }, [analysisResult, targetLanguage]);

    const handleSendMessage = useCallback(async (message: string) => {
        if (!chatSessionId) {
            setError('Chat session not initialized. Please analyze a document first.');
            return;
        }
        
        setChatMessages(prev => [...prev, { sender: 'user', text: message }]);
        setIsChatting(true);

        try {
            const response = await continueChat(chatSessionId, message);
            setChatMessages(prev => [...prev, { sender: 'ai', text: response }]);
        } catch (err)
 {
            console.error(err);
            setChatMessages(prev => [...prev, { sender: 'ai', text: 'Sorry, I encountered an error. Please try again.' }]);
        } finally {
            setIsChatting(false);
        }
    }, [chatSessionId]);


    return (
        <div className="min-h-screen text-slate-800 font-sans">
            <Header />
            <main className="container mx-auto p-4 md:p-8">
                <div className="max-w-7xl mx-auto">
                    {error && (
                        <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 rounded-md mb-6" role="alert">
                            <p className="font-bold">Error</p>
                            <p>{error}</p>
                        </div>
                    )}
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                        <div className="lg:col-span-1 flex flex-col gap-8">
                            <DocumentInput 
                                documentText={documentText}
                                setDocumentText={setDocumentText}
                                uploadedFile={uploadedFile}
                                setUploadedFile={setUploadedFile}
                                onAnalyze={handleAnalyze}
                                isLoading={isLoading}
                            />
                        </div>
                        <div className="lg:col-span-2 flex flex-col gap-8">
                            {isLoading && (
                                <div className="w-full h-full flex flex-col items-center justify-center bg-white/50 rounded-lg shadow-md p-6 min-h-[400px]">
                                    <Icon name="loader" className="h-12 w-12 animate-spin text-indigo-600" />
                                    <p className="mt-4 text-lg font-semibold text-slate-700">Analyzing Document...</p>
                                    <p className="text-slate-500">This may take a moment.</p>
                                </div>
                            )}
                        
                            {!isLoading && !analysisResult && (
                                <div className="w-full h-full flex flex-col items-center justify-center bg-gradient-to-br from-indigo-50 to-white rounded-lg shadow-md p-8 min-h-[400px] border border-slate-200 text-center">
                                    <Icon name="logo" className="h-20 w-20 text-indigo-300" />
                                    <h3 className="mt-4 text-2xl font-bold text-slate-700">
                                        Unlock Legal Clarity
                                    </h3>
                                    <p className="text-slate-500 mt-2 max-w-md">
                                        Upload or paste your legal document to receive a complete AI-powered analysis, including simplification, risk assessment, and more.
                                    </p>
                                </div>
                            )}

                            {analysisResult && !isLoading && (
                                <>
                                    <AnalysisOutput 
                                        analysis={analysisResult}
                                        translation={translatedText}
                                        targetLanguage={targetLanguage}
                                        setTargetLanguage={setTargetLanguage}
                                        onTranslate={handleTranslate}
                                        isTranslating={isTranslating}
                                    />
                                    <ChatInterface
                                        messages={chatMessages}
                                        onSendMessage={handleSendMessage}
                                        isLoading={isChatting}
                                    />
                                </>
                            )}
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
};

export default App;