import React, { useState, useCallback } from 'react';
import { Header } from './components/Header';
import { DocumentInput } from './components/DocumentInput';
import { AnalysisOutput } from './components/AnalysisOutput';
import { ChatInterface } from './components/ChatInterface';
import type { AnalysisResult, ChatMessage, UploadedFile } from './types';
import { analyzeDocument, translateText, createChatSession, continueChat } from './services/apiService';
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
            const message = err instanceof Error ? err.message : 'Failed to analyze the document.';
            setError(`Failed to analyze the document: ${message}`);
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
        <div className="min-h-screen text-slate-800 font-sans bg-[radial-gradient(circle_at_top,_#eef2ff_0%,_#f8fafc_45%,_#ffffff_100%)]">
            <Header />
            <main className="container mx-auto p-4 md:p-8">
                <div className="max-w-7xl mx-auto">
                    {error && (
                        <div className="mb-4 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg">
                            {error}
                        </div>
                    )}
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
                        <div className="lg:col-span-2">
                            <DocumentInput
                                documentText={documentText}
                                setDocumentText={setDocumentText}
                                uploadedFile={uploadedFile}
                                setUploadedFile={setUploadedFile}
                                onAnalyze={handleAnalyze}
                                isLoading={isLoading}
                            />
                        </div>
                    </div>

                    {analysisResult && (
                        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                            <div className="lg:col-span-2">
                                <AnalysisOutput
                                    analysis={analysisResult}
                                    translation={translatedText}
                                    targetLanguage={targetLanguage}
                                    setTargetLanguage={setTargetLanguage}
                                    onTranslate={handleTranslate}
                                    isTranslating={isTranslating}
                                />
                            </div>
                            <div>
                                <ChatInterface
                                    messages={chatMessages}
                                    onSendMessage={handleSendMessage}
                                    isLoading={isChatting}
                                />
                            </div>
                        </div>
                    )}
                </div>
            </main>
        </div>
    );
};

export default App;
