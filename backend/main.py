from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import base64
from dotenv import load_dotenv
from google import genai
from google.genai.types import GenerateContentConfig, Part

# Load environment variables from .env file
load_dotenv()

app = FastAPI(title="LegalEase AI Backend")

# CORS Configuration - Allow frontend to communicate
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Gemini AI client
API_KEY = os.getenv("GEMINI_API_KEY", "")
if not API_KEY:
    print("Warning: GEMINI_API_KEY not set. Please set it in your environment.")

client = genai.Client(api_key=API_KEY)

# Store active chat sessions (in production, use Redis or a database)
chat_sessions: Dict[str, Any] = {}

# Pydantic Models
class UploadedFile(BaseModel):
    name: str
    mimeType: str
    data: str  # base64 encoded

class AnalyzeDocumentRequest(BaseModel):
    documentText: Optional[str] = ""
    file: Optional[UploadedFile] = None

class KeyClause(BaseModel):
    type: str
    clause: str
    explanation: str

class RiskItem(BaseModel):
    risk: str
    mitigation: str
    severity: str
    applicableLaw: str
    punishment: str

class DocumentDetails(BaseModel):
    documentType: str
    partiesOrEntities: List[str]
    date: str
    duration: str
    jurisdiction: str
    purpose: str

class AnalysisResult(BaseModel):
    simplifiedText: str
    summary: str
    keyClauses: List[KeyClause]
    riskAnalysis: List[RiskItem]
    documentDetails: DocumentDetails

class TranslateRequest(BaseModel):
    text: str
    language: str

class ChatCreateRequest(BaseModel):
    documentText: Optional[str] = ""
    file: Optional[UploadedFile] = None

class ChatMessageRequest(BaseModel):
    sessionId: str
    message: str

class ChatResponse(BaseModel):
    response: str

class ChatCreateResponse(BaseModel):
    sessionId: str
    initialMessage: str

# Analysis schema for structured output
analysis_schema = {
    "type": "object",
    "properties": {
        "simplifiedText": {
            "type": "string",
            "description": "The entire legal document rewritten in simple, easy-to-understand plain English. Preserve the original meaning and structure."
        },
        "summary": {
            "type": "string",
            "description": "A concise summary of the document's main purpose and most critical points."
        },
        "keyClauses": {
            "type": "array",
            "description": "An array of important clauses identified in the document.",
            "items": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "description": "The category of the clause. Examples: 'Obligation', 'Penalty', 'Date', 'Right', 'Condition', 'Other'."
                    },
                    "clause": {
                        "type": "string",
                        "description": "The exact text of the clause from the original document."
                    },
                    "explanation": {
                        "type": "string",
                        "description": "A simple, one-sentence explanation of what this clause means for the user."
                    }
                },
                "required": ["type", "clause", "explanation"]
            }
        },
        "riskAnalysis": {
            "type": "array",
            "description": "An array of potential risks identified in the document, along with mitigation strategies, applicable Indian laws, and punishments for violation.",
            "items": {
                "type": "object",
                "properties": {
                    "risk": {
                        "type": "string",
                        "description": "A clear description of a potential risk or unfavorable clause for the user."
                    },
                    "mitigation": {
                        "type": "string",
                        "description": "A suggested solution or action to mitigate or overcome the identified risk."
                    },
                    "severity": {
                        "type": "string",
                        "description": "The severity of the risk. Must be one of: 'High', 'Medium', 'Low'."
                    },
                    "applicableLaw": {
                        "type": "string",
                        "description": "The specific Indian law or act (e.g., Indian Contract Act, 1872) that governs this clause or agreement."
                    },
                    "punishment": {
                        "type": "string",
                        "description": "The potential punishment or legal consequence under Indian law if this part of the agreement is violated."
                    }
                },
                "required": ["risk", "mitigation", "severity", "applicableLaw", "punishment"]
            }
        },
        "documentDetails": {
            "type": "object",
            "description": "Key details extracted from the document. Always populate all fields regardless of document type.",
            "properties": {
                "documentType": {"type": "string", "description": "The type of document (e.g., 'Employment Agreement', 'Court Order', 'Legal Notice', 'Sale Deed', 'Rental Agreement', 'Policy Document', etc.)."},
                "partiesOrEntities": {"type": "array", "items": {"type": "string"}, "description": "All parties, persons, organizations, or entities mentioned in the document."},
                "date": {"type": "string", "description": "The date, effective date, or issue date of the document. Use 'Not specified' if none found."},
                "duration": {"type": "string", "description": "The term or duration of the document (e.g., '1 year', '6 months'). Use 'Not applicable' if no duration."},
                "jurisdiction": {"type": "string", "description": "The governing law or jurisdiction stated in the document. Use 'Not specified' if none."},
                "purpose": {"type": "string", "description": "A brief one-sentence description of the document's main purpose or subject matter."}
            },
            "required": ["documentType", "partiesOrEntities", "date", "duration", "jurisdiction", "purpose"]
        }
    },
    "required": ["simplifiedText", "summary", "keyClauses", "riskAnalysis", "documentDetails"]
}

@app.get("/")
def read_root():
    return {"message": "LegalEase AI Backend API", "status": "running"}

@app.post("/api/analyze", response_model=AnalysisResult)
async def analyze_document(request: AnalyzeDocumentRequest):
    """Analyze a legal document and return structured analysis"""
    try:
        prompt = """Analyze the following document from the perspective of an Indian legal expert. Your task is to simplify it, summarize it, extract key clauses, perform a detailed risk analysis, and extract its document details. Provide the output in a structured JSON format.

Document Details (ALWAYS populate for any document type):
- documentType: Identify what kind of document this is (e.g., 'Employment Agreement', 'Court Order', 'Legal Notice', 'Sale Deed', 'Rental Agreement', 'Affidavit', 'Power of Attorney', etc.).
- partiesOrEntities: List ALL persons, organizations, companies, or government entities mentioned.
- date: The document's date, issue date, or effective date (or 'Not specified' if absent).
- duration: The term or duration if applicable (or 'Not applicable').
- jurisdiction: The governing law or jurisdiction (or 'Not specified').
- purpose: One sentence describing the document's main purpose.

For the risk analysis, for each identified risk, you must provide:
1.  **Risk**: A description of the potential risk.
2.  **Mitigation**: A solution on how to overcome the risk.
3.  **Severity**: The severity of the risk, classified as 'High', 'Medium', or 'Low'.
4.  **Applicable Law**: The relevant Indian laws that apply to this document or provision.
5.  **Punishment**: The potential legal consequences or penalties under Indian law if violated."""

        # Build the request content
        if request.file:
            # Decode base64 data to bytes
            file_bytes = base64.b64decode(request.file.data)
            contents = [
                prompt,
                Part.from_bytes(
                    data=file_bytes,
                    mime_type=request.file.mimeType
                )
            ]
        else:
            contents = f"{prompt}\n\nDocument:\n---\n{request.documentText}\n---"

        # Generate content with structured output
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=analysis_schema
            )
        )

        # Parse and return the result
        import json
        result = json.loads(response.text)
        return result

    except Exception as e:
        print(f"Error in analyze_document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze document: {str(e)}")

@app.post("/api/translate")
async def translate_text(request: TranslateRequest):
    """Translate text to a specified language"""
    try:
        prompt = f"""Translate the following English text into {request.language}. Provide only the translated text.

Text:
---
{request.text}
---
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        return {"translation": response.text.strip()}

    except Exception as e:
        print(f"Error in translate_text: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to translate text: {str(e)}")

@app.post("/api/chat/create", response_model=ChatCreateResponse)
async def create_chat_session(request: ChatCreateRequest):
    """Create a new chat session with document context"""
    try:
        import uuid
        session_id = str(uuid.uuid4())

        system_instruction = """You are an expert legal assistant specializing in Indian law. Your primary role is to help users understand the provided legal document.

When a user asks a question directly about the document's content (e.g., "What is the termination clause?", "Who are the parties involved?"), your answer must be based exclusively on the information within that document.

If the user asks for a definition of a legal term or a general concept mentioned in the document (e.g., "What does 'indemnification' mean under Indian law?"), you should use your broader knowledge to provide a clear, accurate explanation relevant to the Indian legal system.

Always prioritize the document's text for specific queries. Do not provide financial or legal advice. Your goal is to explain and clarify, not to advise."""

        # Create chat session
        chat = client.chats.create(
            model="gemini-2.5-flash",
            config=GenerateContentConfig(
                system_instruction=system_instruction
            )
        )

        # Send initial context
        context_instruction = "Here is the legal document I want to ask questions about. All my future questions will refer to this text:\n\n---\n"
        
        if request.file:
            # Decode base64 data to bytes
            file_bytes = base64.b64decode(request.file.data)
            context_message = [
                context_instruction,
                Part.from_bytes(
                    data=file_bytes,
                    mime_type=request.file.mimeType
                )
            ]
        else:
            context_message = f"{context_instruction}{request.documentText}\n---"

        chat.send_message(context_message)

        # Store session
        chat_sessions[session_id] = chat

        return ChatCreateResponse(
            sessionId=session_id,
            initialMessage="I have read the document. How can I help you?"
        )

    except Exception as e:
        print(f"Error in create_chat_session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create chat session: {str(e)}")

@app.post("/api/chat/message", response_model=ChatResponse)
async def send_chat_message(request: ChatMessageRequest):
    """Send a message in an existing chat session"""
    try:
        if request.sessionId not in chat_sessions:
            raise HTTPException(status_code=404, detail="Chat session not found")

        chat = chat_sessions[request.sessionId]
        response = chat.send_message(request.message)

        return ChatResponse(response=response.text.strip())

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in send_chat_message: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
