import { GoogleGenAI, Type, Chat, Part } from "@google/genai";
import type { AnalysisResult, UploadedFile } from '../../types';

// Read the API key from environment so we don't hardcode secrets in source.
// Vite will inject process.env.GEMINI_API_KEY when using loadEnv/define in vite.config.
const API_KEY = process.env.GEMINI_API_KEY || '';
if (!API_KEY) {
    // Warn in development if not set — helps debugging.
    // It's intentionally a console.warn (not throw) so app can still run in non-AI flows.
    console.warn('GEMINI_API_KEY is not set. Add it to a .env.local file at the project root or set the environment variable.');
}

const ai = new GoogleGenAI({ apiKey: API_KEY });

const analysisSchema = {
    type: Type.OBJECT,
    properties: {
        simplifiedText: {
            type: Type.STRING,
            description: "The entire legal document rewritten in simple, easy-to-understand plain English. Preserve the original meaning and structure."
        },
        summary: {
            type: Type.STRING,
            description: "A concise summary of the document's main purpose and most critical points."
        },
        keyClauses: {
            type: Type.ARRAY,
            description: "An array of important clauses identified in the document.",
            items: {
                type: Type.OBJECT,
                properties: {
                    type: {
                        type: Type.STRING,
                        description: "The category of the clause. Examples: 'Obligation', 'Penalty', 'Date', 'Right', 'Condition', 'Other'."
                    },
                    clause: {
                        type: Type.STRING,
                        description: "The exact text of the clause from the original document."
                    },
                    explanation: {
                        type: Type.STRING,
                        description: "A simple, one-sentence explanation of what this clause means for the user."
                    }
                },
                required: ["type", "clause", "explanation"]
            }
        },
        riskAnalysis: {
            type: Type.ARRAY,
            description: "An array of potential risks identified in the document, along with mitigation strategies, applicable Indian laws, and punishments for violation.",
            items: {
                type: Type.OBJECT,
                properties: {
                    risk: {
                        type: Type.STRING,
                        description: "A clear description of a potential risk or unfavorable clause for the user."
                    },
                    mitigation: {
                        type: Type.STRING,
                        description: "A suggested solution or action to mitigate or overcome the identified risk."
                    },
                    severity: {
                        type: Type.STRING,
                        description: "The severity of the risk. Must be one of: 'High', 'Medium', 'Low'."
                    },
                    applicableLaw: {
                        type: Type.STRING,
                        description: "The specific Indian law or act (e.g., Indian Contract Act, 1872) that governs this clause or agreement."
                    },
                    punishment: {
                        type: Type.STRING,
                        description: "The potential punishment or legal consequence under Indian law if this part of the agreement is violated."
                    }
                },
                required: ["risk", "mitigation", "severity", "applicableLaw", "punishment"]
            }
        },
        agreementDetails: {
            type: Type.OBJECT,
            description: "If the document is a legal agreement, extract its key details. If it is not a legal agreement (e.g., a court ruling, a letter), return null for this entire object.",
            nullable: true,
            properties: {
                agreementType: { type: Type.STRING, description: "The type of agreement (e.g., 'Employment Agreement', 'Lease Agreement')." },
                parties: { type: Type.ARRAY, items: { type: Type.STRING }, description: "The names of the parties involved in the agreement." },
                effectiveDate: { type: Type.STRING, description: "The effective or start date of the agreement." },
                term: { type: Type.STRING, description: "The term or duration of the agreement." },
                governingLaw: { type: Type.STRING, description: "The governing law or jurisdiction of the agreement (e.g., 'State of California, USA', 'Republic of India')." }
            },
            required: ["agreementType", "parties", "effectiveDate", "term", "governingLaw"]
        }
    },
    required: ["simplifiedText", "summary", "keyClauses", "riskAnalysis", "agreementDetails"]
};

interface AnalyzeDocumentParams {
    documentText?: string;
    file?: UploadedFile | null;
}

export const analyzeDocument = async ({ documentText, file }: AnalyzeDocumentParams): Promise<AnalysisResult> => {
    const prompt = `Analyze the following legal document from the perspective of an Indian legal expert. Your task is to simplify it, summarize it, extract key clauses, perform a detailed risk analysis, and identify its core agreement details. Provide the output in a structured JSON format.

If the document is a formal legal agreement, extract the following details:
- The type of agreement.
- The parties involved.
- The effective date.
- The term/duration.
- The governing law.
If the document is not a formal agreement, please return null for the 'agreementDetails' field.

For the risk analysis, for each identified risk, you must provide:
1.  **Risk**: A description of the potential risk.
2.  **Mitigation**: A solution on how to overcome the risk.
3.  **Severity**: The severity of the risk, classified as 'High', 'Medium', or 'Low'.
4.  **Applicable Law**: The relevant Indian laws under which the agreement has been made.
5.  **Punishment**: The punishment under the Indian constitution or relevant laws if the rules or agreement are violated.`;

    let requestContents: string | { parts: Part[] };

    if (file) {
        requestContents = {
            parts: [
                { text: prompt },
                { inlineData: { mimeType: file.mimeType, data: file.data } }
            ]
        };
    } else {
        requestContents = `${prompt}\n\nDocument:\n---\n${documentText}\n---`;
    }

    const response = await ai.models.generateContent({
        model: "gemini-2.5-flash",
        contents: requestContents,
        config: {
            responseMimeType: "application/json",
            responseSchema: analysisSchema,
        },
    });

    const jsonString = response.text.trim();
    try {
        const parsedJson = JSON.parse(jsonString);
        return parsedJson as AnalysisResult;
    } catch (e) {
        console.error("Failed to parse Gemini response:", jsonString);
        throw new Error("The AI returned an invalid response format.");
    }
};

export const translateText = async (text: string, language: string): Promise<string> => {
    const prompt = `Translate the following English text into ${language}. Provide only the translated text.

Text:
---
${text}
---
`;

    const response = await ai.models.generateContent({
        model: "gemini-2.5-flash",
        contents: prompt,
    });
    
    return response.text.trim();
};

export const createChatSession = async ({ documentText, file }: AnalyzeDocumentParams): Promise<Chat> => {
    const chat = ai.chats.create({
        model: 'gemini-2.5-flash',
        config: {
            systemInstruction: `You are an expert legal assistant specializing in Indian law. Your primary role is to help users understand the provided legal document.

When a user asks a question directly about the document's content (e.g., "What is the termination clause?", "Who are the parties involved?"), your answer must be based exclusively on the information within that document.

If the user asks for a definition of a legal term or a general concept mentioned in the document (e.g., "What does 'indemnification' mean under Indian law?"), you should use your broader knowledge to provide a clear, accurate explanation relevant to the Indian legal system.

Always prioritize the document's text for specific queries. Do not provide financial or legal advice. Your goal is to explain and clarify, not to advise.`,
        },
    });

    const contextInstruction = `Here is the legal document I want to ask questions about. All my future questions will refer to this text:\n\n---\n`;
    let contextMessage: string | Part[];
    
    if (file) {
        contextMessage = [
            { text: contextInstruction },
            { inlineData: { mimeType: file.mimeType, data: file.data } }
        ];
    } else {
        contextMessage = `${contextInstruction}${documentText}\n---`;
    }

    // Send the document context to prime the chat session
    await chat.sendMessage({ message: contextMessage });

    return chat;
};

export const continueChat = async (chat: Chat, message: string): Promise<string> => {
    const response = await chat.sendMessage({ message });
    return response.text.trim();
};
