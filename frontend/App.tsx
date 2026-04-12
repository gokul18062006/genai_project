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
            const message = err instanceof Error ? err.message : 'Failed to analyze the document.';
            setError(message);
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
            const message = err instanceof Error ? err.message : 'Failed to translate the text.';
            setError(message);
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
            const message = err instanceof Error ? err.message : 'Sorry, I encountered an error. Please try again.';
            setChatMessages(prev => [...prev, { sender: 'ai', text: message }]);
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
            <main className="container mx-auto px-4 py-6 md:px-8 md:py-10">
                <div className="max-w-7xl mx-auto space-y-6">
                    {error && (
                        <div className="bg-red-50/95 border border-red-200 text-red-700 p-4 rounded-2xl shadow-sm" role="alert">
                            <p className="font-bold">Error</p>
                            <p>{error}</p>
                        </div>
                    )}
                    <section className="glass-panel rounded-3xl p-5 md:p-7 gradient-ring fade-in-stagger">
                        <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-5">
                            <div>
                                <div className="inline-flex items-center gap-2 rounded-full border border-cyan-200 bg-cyan-50 px-3 py-1 text-xs font-semibold text-cyan-800">
                                    <Icon name="sparkles" className="h-4 w-4" />
                                    AI-powered legal readability
                                </div>
                                <h2 className="section-title mt-3 text-2xl md:text-3xl font-extrabold text-slate-900">Understand legal documents in minutes</h2>
                                <p className="mt-2 text-sm md:text-base text-slate-600 max-w-3xl">Upload a contract, detect risky clauses, get plain-language explanations, and ask context-aware follow-up questions instantly.</p>
                            </div>
                            <div className="grid grid-cols-3 gap-2 text-center w-full lg:w-auto">
                                <div className="rounded-2xl bg-white/95 border border-slate-200 px-4 py-3 min-w-[90px]">
                                    <p className="text-lg font-extrabold text-cyan-800">1</p>
                                    <p className="text-xs text-slate-600">Upload</p>
                                </div>
                                <div className="rounded-2xl bg-white/95 border border-slate-200 px-4 py-3 min-w-[90px]">
                                    <p className="text-lg font-extrabold text-cyan-800">2</p>
                                    <p className="text-xs text-slate-600">Analyze</p>
                                </div>
                                <div className="rounded-2xl bg-white/95 border border-slate-200 px-4 py-3 min-w-[90px]">
                                    <p className="text-lg font-extrabold text-cyan-800">3</p>
                                    <p className="text-xs text-slate-600">Ask</p>
                                </div>
                            </div>
                        </div>
                    </section>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 fade-in-stagger">
                        <div className="rounded-2xl glass-panel px-4 py-3 text-sm text-slate-700">1. Add your legal document</div>
                        <div className="rounded-2xl glass-panel px-4 py-3 text-sm text-slate-700">2. Review risks and details</div>
                        <div className="rounded-2xl glass-panel px-4 py-3 text-sm text-slate-700">3. Ask follow-up questions in chat</div>
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
                                <div className="w-full h-full flex flex-col items-center justify-center glass-panel rounded-3xl p-8 min-h-[420px] text-center">
                                    <Icon name="loader" className="h-12 w-12 animate-spin text-cyan-700" />
                                    <p className="mt-4 text-lg font-semibold text-slate-700">Analyzing your document</p>
                                    <p className="text-slate-500">Extracting clauses, risks, and key details. This may take a moment.</p>
                                </div>
                            )}
                        
                            {!isLoading && !analysisResult && (
                                <div className="w-full h-full flex flex-col justify-center glass-panel rounded-3xl p-8 min-h-[420px]">
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