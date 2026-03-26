from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Set, Tuple
from io import BytesIO
import os
import re
import math
import json
import base64
import uuid

from dotenv import load_dotenv
from google import genai
from google.genai.types import GenerateContentConfig, Part
from pypdf import PdfReader

# Load environment variables from .env file
load_dotenv()

app = FastAPI(title="LegalEase AI Backend")

# CORS Configuration - Allow frontend to communicate locally and in production
default_origins = ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]
configured_origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "").split(",") if origin.strip()]
allowed_origins = list(dict.fromkeys(default_origins + configured_origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=os.getenv("CORS_ORIGIN_REGEX", r"https://.*\.onrender\.com"),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Gemini AI client
API_KEY = os.getenv("GEMINI_API_KEY", "")
if not API_KEY:
    print("Warning: GEMINI_API_KEY not set. Please set it in your environment.")

client = genai.Client(api_key=API_KEY)

# RAG settings
EMBED_MODEL = os.getenv("RAG_EMBED_MODEL", "text-embedding-004")
CHAT_MODEL = os.getenv("RAG_CHAT_MODEL", "gemini-2.5-flash")
ANALYSIS_MODEL = os.getenv("RAG_ANALYSIS_MODEL", "gemini-2.5-flash")
MAX_CHUNK_CHARS = int(os.getenv("RAG_MAX_CHUNK_CHARS", "1400"))
CHUNK_OVERLAP_CHARS = int(os.getenv("RAG_CHUNK_OVERLAP_CHARS", "250"))
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "8"))
HISTORY_WINDOW = int(os.getenv("RAG_HISTORY_WINDOW", "6"))

# VLM settings for scanned/image-heavy PDFs
VLM_ENABLED = os.getenv("VLM_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
VLM_MODEL = os.getenv("VLM_MODEL", "gemini-2.5-flash")
VLM_MIN_EXTRACTED_CHARS = int(os.getenv("VLM_MIN_EXTRACTED_CHARS", "1200"))
VLM_MIN_TEXT_PAGE_RATIO = float(os.getenv("VLM_MIN_TEXT_PAGE_RATIO", "0.5"))

STOPWORDS: Set[str] = {
    "a", "an", "the", "and", "or", "to", "of", "in", "on", "for", "with", "as", "by", "from",
    "at", "is", "are", "was", "were", "be", "been", "being", "this", "that", "it", "its", "if",
    "then", "than", "into", "under", "over", "about", "can", "could", "should", "would", "will",
    "shall", "may", "might", "must", "do", "does", "did", "have", "has", "had", "we", "you", "they"
}

# Store active chat sessions (in production, move to Redis/DB)
chat_sessions: Dict[str, Dict[str, Any]] = {}


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
                "documentType": {"type": "string", "description": "The type of document (e.g., Employment Agreement, Court Order, Legal Notice, Sale Deed, Rental Agreement, Policy Document, etc.)."},
                "partiesOrEntities": {"type": "array", "items": {"type": "string"}, "description": "All parties, persons, organizations, or entities mentioned in the document."},
                "date": {"type": "string", "description": "The date, effective date, or issue date of the document. Use 'Not specified' if none found."},
                "duration": {"type": "string", "description": "The term or duration of the document (e.g., 1 year, 6 months). Use 'Not applicable' if no duration."},
                "jurisdiction": {"type": "string", "description": "The governing law or jurisdiction stated in the document. Use 'Not specified' if none."},
                "purpose": {"type": "string", "description": "A brief one-sentence description of the document's main purpose or subject matter."}
            },
            "required": ["documentType", "partiesOrEntities", "date", "duration", "jurisdiction", "purpose"]
        }
    },
    "required": ["simplifiedText", "summary", "keyClauses", "riskAnalysis", "documentDetails"]
}


def _normalize_whitespace(text: str) -> str:
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[\t\f\v]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ ]{2,}", " ", text)
    return text.strip()


def _tokenize(text: str) -> List[str]:
    words = re.findall(r"[a-zA-Z0-9_\-]+", text.lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 1]


def _extract_pdf_text_with_vlm(pdf_bytes: bytes) -> str:
    """Fallback extractor for scanned/low-text PDFs using a multimodal model."""
    prompt = """You are a legal document OCR and layout extractor.

Extract all readable text from this PDF in reading order.
Rules:
1) Preserve section numbering, clause numbering, and headings.
2) Add page separators in the form: [PAGE N].
3) Keep the original wording as much as possible.
4) If a small fragment is unreadable, use [unclear].
5) Return plain text only. Do not return JSON or markdown.
"""

    try:
        response = client.models.generate_content(
            model=VLM_MODEL,
            contents=[
                prompt,
                Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")
            ],
            config=GenerateContentConfig(temperature=0.0)
        )
        return _normalize_whitespace(response.text or "")
    except Exception as err:
        print(f"VLM PDF extraction failed: {err}")
        return ""


def _is_pdf_text_quality_sufficient(total_pages: int, pages_with_text: int, extracted_chars: int) -> bool:
    if total_pages <= 0:
        return False
    text_page_ratio = pages_with_text / total_pages
    return extracted_chars >= VLM_MIN_EXTRACTED_CHARS and text_page_ratio >= VLM_MIN_TEXT_PAGE_RATIO


def _extract_text_from_uploaded_file(uploaded_file: UploadedFile) -> str:
    raw = base64.b64decode(uploaded_file.data)
    mime = (uploaded_file.mimeType or "").lower()
    name = (uploaded_file.name or "").lower()

    if mime == "application/pdf" or name.endswith(".pdf"):
        reader = PdfReader(BytesIO(raw))
        page_count = len(reader.pages)
        pages: List[str] = []
        pages_with_text = 0
        extracted_chars = 0

        for i, page in enumerate(reader.pages, start=1):
            page_text = (page.extract_text() or "").strip()
            if page_text:
                pages_with_text += 1
                extracted_chars += len(page_text)
                pages.append(f"[PAGE {i}]\n{page_text}")

        pypdf_text = _normalize_whitespace("\n\n".join(pages)) if pages else ""
        if _is_pdf_text_quality_sufficient(page_count, pages_with_text, extracted_chars):
            return pypdf_text

        if VLM_ENABLED:
            vlm_text = _extract_pdf_text_with_vlm(raw)
            if vlm_text:
                return vlm_text

        if pypdf_text:
            return pypdf_text

        raise HTTPException(
            status_code=400,
            detail="Could not extract usable text from the uploaded PDF. Try a clearer file or enable VLM fallback."
        )

    if mime in {"text/plain", "application/octet-stream"} or name.endswith(".txt"):
        for encoding in ("utf-8", "utf-16", "latin-1"):
            try:
                return _normalize_whitespace(raw.decode(encoding))
            except UnicodeDecodeError:
                continue
        raise HTTPException(status_code=400, detail="Could not decode uploaded text file.")

    raise HTTPException(status_code=400, detail="Unsupported file type. Please upload a TXT or PDF file.")


def _extract_document_text(document_text: str, uploaded_file: Optional[UploadedFile]) -> str:
    if uploaded_file:
        extracted = _extract_text_from_uploaded_file(uploaded_file)
        if extracted:
            return extracted
    return _normalize_whitespace(document_text or "")


def _chunk_document(text: str) -> List[Dict[str, Any]]:
    if not text:
        return []

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: List[Dict[str, Any]] = []
    buffer = ""
    chunk_id = 1

    for para in paragraphs:
        candidate = para if not buffer else f"{buffer}\n\n{para}"
        if len(candidate) <= MAX_CHUNK_CHARS:
            buffer = candidate
            continue

        if buffer:
            chunk_text = buffer.strip()
            chunks.append({
                "id": f"chunk_{chunk_id}",
                "text": chunk_text,
                "tokens": _tokenize(chunk_text)
            })
            chunk_id += 1

            overlap_seed = chunk_text[-CHUNK_OVERLAP_CHARS:] if CHUNK_OVERLAP_CHARS > 0 else ""
            buffer = (overlap_seed + "\n\n" + para).strip()
            if len(buffer) > MAX_CHUNK_CHARS:
                buffer = para
        else:
            # Extremely long paragraph fallback split
            start = 0
            step = max(200, MAX_CHUNK_CHARS - CHUNK_OVERLAP_CHARS)
            while start < len(para):
                part = para[start:start + MAX_CHUNK_CHARS]
                if not part:
                    break
                chunks.append({
                    "id": f"chunk_{chunk_id}",
                    "text": part,
                    "tokens": _tokenize(part)
                })
                chunk_id += 1
                start += step
            buffer = ""

    if buffer:
        chunk_text = buffer.strip()
        chunks.append({
            "id": f"chunk_{chunk_id}",
            "text": chunk_text,
            "tokens": _tokenize(chunk_text)
        })

    return chunks


def _extract_embedding_values(item: Any) -> Optional[List[float]]:
    values = getattr(item, "values", None)
    if isinstance(values, list):
        return values

    embedding = getattr(item, "embedding", None)
    if embedding is not None:
        nested_values = getattr(embedding, "values", None)
        if isinstance(nested_values, list):
            return nested_values
        if isinstance(embedding, list):
            return embedding

    if isinstance(item, dict):
        if isinstance(item.get("values"), list):
            return item["values"]
        emb = item.get("embedding")
        if isinstance(emb, dict) and isinstance(emb.get("values"), list):
            return emb["values"]
        if isinstance(emb, list):
            return emb

    return None


def _embed_texts(texts: List[str]) -> Optional[List[List[float]]]:
    if not texts:
        return []

    try:
        response = client.models.embed_content(model=EMBED_MODEL, contents=texts)
        items = getattr(response, "embeddings", None)
        if items is None and isinstance(response, dict):
            items = response.get("embeddings")

        if not items:
            return None

        vectors: List[List[float]] = []
        for item in items:
            values = _extract_embedding_values(item)
            if values is None:
                return None
            vectors.append(values)

        if len(vectors) != len(texts):
            return None
        return vectors
    except Exception as err:
        print(f"Embedding unavailable, using lexical retrieval only: {err}")
        return None


def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    if len(vec_a) != len(vec_b) or not vec_a:
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _build_idf(chunks: List[Dict[str, Any]]) -> Dict[str, float]:
    doc_count = len(chunks)
    term_df: Dict[str, int] = {}
    for chunk in chunks:
        seen = set(chunk["tokens"])
        for token in seen:
            term_df[token] = term_df.get(token, 0) + 1

    idf: Dict[str, float] = {}
    for token, df in term_df.items():
        idf[token] = math.log(1 + (doc_count - df + 0.5) / (df + 0.5))
    return idf


def _bm25_score(query_tokens: List[str], chunk_tokens: List[str], idf: Dict[str, float], avg_dl: float) -> float:
    if not query_tokens or not chunk_tokens:
        return 0.0

    k1 = 1.5
    b = 0.75
    dl = len(chunk_tokens)
    tf: Dict[str, int] = {}
    for token in chunk_tokens:
        tf[token] = tf.get(token, 0) + 1

    score = 0.0
    for token in query_tokens:
        if token not in tf:
            continue
        term_idf = idf.get(token, 0.0)
        freq = tf[token]
        numerator = freq * (k1 + 1)
        denominator = freq + k1 * (1 - b + b * (dl / max(avg_dl, 1.0)))
        score += term_idf * (numerator / denominator)
    return score


def _normalize_scores(raw_scores: List[float]) -> List[float]:
    if not raw_scores:
        return []
    min_s = min(raw_scores)
    max_s = max(raw_scores)
    if max_s == min_s:
        return [0.0 for _ in raw_scores]
    return [(s - min_s) / (max_s - min_s) for s in raw_scores]


def _retrieve_relevant_chunks(
    session: Dict[str, Any],
    query: str,
    top_k: int = RAG_TOP_K
) -> List[Tuple[Dict[str, Any], float]]:
    chunks: List[Dict[str, Any]] = session.get("chunks", [])
    if not chunks:
        return []

    query_tokens = _tokenize(query)
    idf = session.get("idf", {})
    avg_dl = session.get("avg_doc_len", 1.0)
    lexical_scores = [_bm25_score(query_tokens, c["tokens"], idf, avg_dl) for c in chunks]

    semantic_scores = [0.0 for _ in chunks]
    chunk_embeddings: Optional[List[List[float]]] = session.get("chunk_embeddings")
    if chunk_embeddings:
        query_embedding_batch = _embed_texts([query])
        if query_embedding_batch and len(query_embedding_batch) == 1:
            query_vec = query_embedding_batch[0]
            for idx, chunk_vec in enumerate(chunk_embeddings):
                semantic_scores[idx] = _cosine_similarity(query_vec, chunk_vec)

    normalized_lexical = _normalize_scores(lexical_scores)
    normalized_semantic = _normalize_scores(semantic_scores)

    ranked: List[Tuple[Dict[str, Any], float]] = []
    for i, chunk in enumerate(chunks):
        overlap_hits = sum(1 for t in query_tokens if t in set(chunk["tokens"]))
        coverage_boost = min(0.15, overlap_hits * 0.02)
        combined = (
            0.55 * normalized_semantic[i]
            + 0.35 * normalized_lexical[i]
            + coverage_boost
        )
        ranked.append((chunk, combined))

    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked[:max(1, top_k)]


def _format_context_for_prompt(retrieved: List[Tuple[Dict[str, Any], float]]) -> str:
    context_blocks: List[str] = []
    for chunk, score in retrieved:
        context_blocks.append(
            f"[{chunk['id']}] (score={score:.3f})\n{chunk['text']}"
        )
    return "\n\n".join(context_blocks)


def _build_rag_prompt(question: str, history: List[Dict[str, str]], context: str) -> str:
    recent = history[-HISTORY_WINDOW:]
    history_text = "\n".join(
        [f"{item['role'].upper()}: {item['content']}" for item in recent]
    )

    return f"""You are an expert legal assistant specializing in Indian law.

Answer ONLY using the provided context chunks. If the answer is not available in context, say exactly:
"I could not find that in the uploaded document."

Rules:
1) Do not invent facts.
2) Keep the answer clear and concise.
3) When using facts, cite chunk ids like [chunk_3], [chunk_7].
4) If law explanation is requested and context mentions the term but not enough details, provide a general legal explanation and clearly label it as "General legal context".

Conversation history:
{history_text if history_text else 'No prior history.'}

Retrieved context:
{context if context else 'No retrieved context.'}

User question:
{question}
"""


@app.get("/")
def read_root():
    return {"message": "LegalEase AI Backend API", "status": "running", "rag": "enabled"}


@app.post("/api/analyze", response_model=AnalysisResult)
async def analyze_document(request: AnalyzeDocumentRequest):
    """Analyze a legal document and return structured analysis"""
    try:
        document_text = _extract_document_text(request.documentText or "", request.file)
        if not document_text:
            raise HTTPException(status_code=400, detail="Please provide legal text or upload a document.")

        prompt = """Analyze the following document from the perspective of an Indian legal expert. Your task is to simplify it, summarize it, extract key clauses, perform a detailed risk analysis, and extract its document details. Provide the output in a structured JSON format.

Document Details (ALWAYS populate for any document type):
- documentType: Identify what kind of document this is (e.g., Employment Agreement, Court Order, Legal Notice, Sale Deed, Rental Agreement, Affidavit, Power of Attorney, etc.).
- partiesOrEntities: List ALL persons, organizations, companies, or government entities mentioned.
- date: The document's date, issue date, or effective date (or Not specified if absent).
- duration: The term or duration if applicable (or Not applicable).
- jurisdiction: The governing law or jurisdiction (or Not specified).
- purpose: One sentence describing the document's main purpose.

For the risk analysis, for each identified risk, you must provide:
1) Risk: A description of the potential risk.
2) Mitigation: A solution on how to overcome the risk.
3) Severity: One of High, Medium, or Low.
4) Applicable Law: Relevant Indian law.
5) Punishment: Potential legal consequence if violated.

Document:
---
"""

        contents = f"{prompt}\n{document_text}\n---"

        response = client.models.generate_content(
            model=ANALYSIS_MODEL,
            contents=contents,
            config=GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=analysis_schema
            )
        )

        result = json.loads(response.text)
        return result

    except HTTPException:
        raise
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
            model=CHAT_MODEL,
            contents=prompt
        )

        return {"translation": response.text.strip()}

    except Exception as e:
        print(f"Error in translate_text: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to translate text: {str(e)}")


@app.post("/api/chat/create", response_model=ChatCreateResponse)
async def create_chat_session(request: ChatCreateRequest):
    """Create a new chat session with indexed document chunks for hybrid retrieval"""
    try:
        document_text = _extract_document_text(request.documentText or "", request.file)
        if not document_text:
            raise HTTPException(status_code=400, detail="Please provide legal text or upload a document before starting chat.")

        chunks = _chunk_document(document_text)
        if not chunks:
            raise HTTPException(status_code=400, detail="Unable to build searchable chunks from the provided document.")

        chunk_texts = [chunk["text"] for chunk in chunks]
        chunk_embeddings = _embed_texts(chunk_texts)
        avg_doc_len = sum(len(c["tokens"]) for c in chunks) / max(1, len(chunks))

        session_id = str(uuid.uuid4())
        chat_sessions[session_id] = {
            "document_text": document_text,
            "chunks": chunks,
            "chunk_embeddings": chunk_embeddings,
            "idf": _build_idf(chunks),
            "avg_doc_len": avg_doc_len,
            "history": []
        }

        return ChatCreateResponse(
            sessionId=session_id,
            initialMessage="I have read and indexed the document. Ask me anything about it."
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in create_chat_session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create chat session: {str(e)}")


@app.post("/api/chat/message", response_model=ChatResponse)
async def send_chat_message(request: ChatMessageRequest):
    """Send a message in an existing RAG chat session"""
    try:
        session = chat_sessions.get(request.sessionId)
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")

        question = _normalize_whitespace(request.message or "")
        if not question:
            raise HTTPException(status_code=400, detail="Question cannot be empty")

        retrieved = _retrieve_relevant_chunks(session, question, top_k=RAG_TOP_K)
        context = _format_context_for_prompt(retrieved)
        prompt = _build_rag_prompt(question, session.get("history", []), context)

        response = client.models.generate_content(
            model=CHAT_MODEL,
            contents=prompt,
        )
        answer = (response.text or "").strip()

        session["history"].append({"role": "user", "content": question})
        session["history"].append({"role": "assistant", "content": answer})

        return ChatResponse(response=answer)

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in send_chat_message: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
