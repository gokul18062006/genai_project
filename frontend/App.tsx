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
        <div className="min-h-screen text-slate-900 font-sans app-shell">
            <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
                <div className="ambient-orb ambient-orb-cyan" />
                <div className="ambient-orb ambient-orb-amber" />
            </div>
            <Header />
            <main className="container mx-auto p-4 md:p-8">
                <div className="max-w-7xl mx-auto">
                    {error && (
                        <div className="bg-red-50/95 border border-red-200 text-red-700 p-4 rounded-2xl mb-6 shadow-sm" role="alert">
                            <p className="font-bold">Error</p>
                            <p>{error}</p>
                        </div>
                    )}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-6 fade-in-stagger">
                        <div className="rounded-2xl bg-white/90 border border-slate-200 px-4 py-3 text-sm text-slate-700 shadow-sm">1. Add your legal document</div>
                        <div className="rounded-2xl bg-white/90 border border-slate-200 px-4 py-3 text-sm text-slate-700 shadow-sm">2. Review risks and details</div>
                        <div className="rounded-2xl bg-white/90 border border-slate-200 px-4 py-3 text-sm text-slate-700 shadow-sm">3. Ask follow-up questions in chat</div>
                    </div>
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
                        <div className="lg:col-span-1 flex flex-col gap-8 lg:sticky lg:top-24">
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
                                <div className="w-full h-full flex flex-col items-center justify-center bg-white/95 rounded-3xl shadow-lg border border-slate-200 p-8 min-h-[420px] text-center">
                                    <Icon name="loader" className="h-12 w-12 animate-spin text-cyan-700" />
                                    <p className="mt-4 text-lg font-semibold text-slate-700">Analyzing your document</p>
                                    <p className="text-slate-500">Extracting clauses, risks, and key details. This may take a moment.</p>
                                </div>
                            )}
                        
                            {!isLoading && !analysisResult && (
                                <div className="w-full h-full flex flex-col justify-center bg-white/95 rounded-3xl shadow-lg p-8 min-h-[420px] border border-slate-200">
                                    <div className="inline-flex items-center gap-2 self-start rounded-full bg-cyan-50 border border-cyan-200 px-3 py-1 text-xs font-semibold text-cyan-800">
                                        <Icon name="sparkles" className="h-4 w-4" />
                                        Smart legal assistant
                                    </div>
                                    <h3 className="mt-4 text-2xl md:text-3xl font-bold text-slate-900">Get instant legal clarity</h3>
                                    <p className="text-slate-500 mt-2 max-w-xl">Upload or paste your document and get simplified text, risk analysis, key clauses, and a chat assistant for follow-up questions.</p>
                                    <div className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-3">
                                        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                                            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Simplify</p>
                                            <p className="text-sm text-slate-700 mt-1">Convert complex legal text into plain language.</p>
                                        </div>
                                        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                                            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Detect Risks</p>
                                            <p className="text-sm text-slate-700 mt-1">Spot high-impact legal concerns and mitigations.</p>
                                        </div>
                                        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                                            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Ask Anything</p>
                                            <p className="text-sm text-slate-700 mt-1">Chat with AI using your uploaded document context.</p>
                                        </div>
                                    </div>
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