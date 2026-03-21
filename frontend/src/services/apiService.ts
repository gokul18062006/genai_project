import type { AnalysisResult, UploadedFile } from '../types';

// Backend API URL - update this if your backend runs on a different port
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

interface AnalyzeDocumentParams {
    documentText?: string;
    file?: UploadedFile | null;
}

// Simple in-memory chat session storage
let currentChatSessionId: string | null = null;

export const analyzeDocument = async ({ documentText, file }: AnalyzeDocumentParams): Promise<AnalysisResult> => {
    try {
        const response = await fetch(`${API_BASE_URL}/api/analyze`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                documentText: documentText || '',
                file: file || null,
            }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to analyze document');
        }

        const result: AnalysisResult = await response.json();
        return result;
    } catch (error) {
        console.error('Error analyzing document:', error);
        throw error;
    }
};

export const translateText = async (text: string, language: string): Promise<string> => {
    try {
        const response = await fetch(`${API_BASE_URL}/api/translate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                text,
                language,
            }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to translate text');
        }

        const result = await response.json();
        return result.translation;
    } catch (error) {
        console.error('Error translating text:', error);
        throw error;
    }
};

export const createChatSession = async ({ documentText, file }: AnalyzeDocumentParams): Promise<string> => {
    try {
        const response = await fetch(`${API_BASE_URL}/api/chat/create`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                documentText: documentText || '',
                file: file || null,
            }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create chat session');
        }

        const result = await response.json();
        currentChatSessionId = result.sessionId;
        return result.sessionId;
    } catch (error) {
        console.error('Error creating chat session:', error);
        throw error;
    }
};

export const continueChat = async (sessionId: string, message: string): Promise<string> => {
    try {
        const response = await fetch(`${API_BASE_URL}/api/chat/message`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                sessionId,
                message,
            }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to send message');
        }

        const result = await response.json();
        return result.response;
    } catch (error) {
        console.error('Error sending chat message:', error);
        throw error;
    }
};

export const getCurrentSessionId = (): string | null => {
    return currentChatSessionId;
};
