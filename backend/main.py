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
import time
from difflib import SequenceMatcher

from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader
import urllib.request
from urllib.error import HTTPError, URLError

try:
    import pypdfium2 as pdfium
except Exception:
    pdfium = None

try:
    from PIL import Image
except Exception:
    Image = None

load_dotenv()

app = FastAPI(title="LegalEase AI Backend")


default_origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
]
configured_origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "").split(",") if origin.strip()]
allowed_origins = list(dict.fromkeys(default_origins + configured_origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=os.getenv(
        "CORS_ORIGIN_REGEX",
        r"(https://.*\.onrender\.com)|(http://localhost:\d+)|(http://127\.0\.0\.1:\d+)"
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini").strip().lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
OPENAI_EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL_CANDIDATES = [
    m.strip() for m in os.getenv(
        "GEMINI_MODEL_CANDIDATES",
        "gemini-2.5-flash,gemini-2.0-flash,gemini-flash-latest,gemini-pro-latest"
    ).split(",") if m.strip()
]
GEMINI_CHAT_MODEL = os.getenv("GEMINI_CHAT_MODEL", GEMINI_MODEL_CANDIDATES[0] if GEMINI_MODEL_CANDIDATES else "gemini-1.5-flash")
GEMINI_ANALYSIS_MODEL = os.getenv("GEMINI_ANALYSIS_MODEL", GEMINI_MODEL_CANDIDATES[0] if GEMINI_MODEL_CANDIDATES else "gemini-1.5-flash")
GEMINI_EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL", "gemini-embedding-001")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_TEXT_MODEL = os.getenv("OLLAMA_TEXT_MODEL", "llama3.1:8b")
OLLAMA_ANALYSIS_MODEL = os.getenv("OLLAMA_ANALYSIS_MODEL", OLLAMA_TEXT_MODEL)
OLLAMA_CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", OLLAMA_TEXT_MODEL)
OLLAMA_TRANSLATE_MODEL = os.getenv("OLLAMA_TRANSLATE_MODEL", "gemma3:1b")
OLLAMA_VLM_MODEL = os.getenv("OLLAMA_VLM_MODEL", "llava:13b")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
OLLAMA_TIMEOUT_SECONDS = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120"))
OLLAMA_MAX_VLM_PAGES = int(os.getenv("OLLAMA_MAX_VLM_PAGES", "3"))
TRANSLATE_MAX_CHARS = int(os.getenv("TRANSLATE_MAX_CHARS", "3500"))
TRANSLATE_CHUNK_CHARS = int(os.getenv("TRANSLATE_CHUNK_CHARS", "1200"))
SIMPLIFY_REWRITE_ENABLED = os.getenv("SIMPLIFY_REWRITE_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
SIMPLIFY_REWRITE_SOURCE_CHAR_LIMIT = int(os.getenv("SIMPLIFY_REWRITE_SOURCE_CHAR_LIMIT", "18000"))
SIMPLIFY_SIMILARITY_THRESHOLD = float(os.getenv("SIMPLIFY_SIMILARITY_THRESHOLD", "0.78"))
SUMMARY_REWRITE_ENABLED = os.getenv("SUMMARY_REWRITE_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
SUMMARY_REWRITE_SOURCE_CHAR_LIMIT = int(os.getenv("SUMMARY_REWRITE_SOURCE_CHAR_LIMIT", "14000"))
SUMMARY_SIMILARITY_THRESHOLD = float(os.getenv("SUMMARY_SIMILARITY_THRESHOLD", "0.72"))
RISK_REWRITE_ENABLED = os.getenv("RISK_REWRITE_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
RISK_REWRITE_SOURCE_CHAR_LIMIT = int(os.getenv("RISK_REWRITE_SOURCE_CHAR_LIMIT", "16000"))
RISK_REWRITE_MIN_ITEMS = int(os.getenv("RISK_REWRITE_MIN_ITEMS", "3"))
openai_client = None
if AI_PROVIDER == "openai":
    if not OPENAI_API_KEY:
        print("Warning: OPENAI_API_KEY not set. Please set it in your environment.")
    else:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
elif AI_PROVIDER == "gemini":
    if not GEMINI_API_KEY:
        print("Warning: GEMINI_API_KEY not set. Please set it in your environment.")
elif AI_PROVIDER == "ollama":
    if not OLLAMA_BASE_URL:
        print("Warning: OLLAMA_BASE_URL not set. Please set it in your environment.")

# RAG settings
EMBED_MODEL = os.getenv(
    "RAG_EMBED_MODEL",
    OPENAI_EMBED_MODEL if AI_PROVIDER == "openai" else (GEMINI_EMBED_MODEL if AI_PROVIDER == "gemini" else OLLAMA_EMBED_MODEL)
)
CHAT_MODEL = os.getenv(
    "CHAT_MODEL",
    OPENAI_MODEL if AI_PROVIDER == "openai" else (GEMINI_CHAT_MODEL if AI_PROVIDER == "gemini" else OLLAMA_CHAT_MODEL)
)
TRANSLATE_MODEL = os.getenv(
    "TRANSLATE_MODEL",
    OPENAI_MODEL if AI_PROVIDER == "openai" else (GEMINI_CHAT_MODEL if AI_PROVIDER == "gemini" else OLLAMA_TRANSLATE_MODEL)
)
ANALYSIS_MODEL = os.getenv(
    "ANALYSIS_MODEL",
    OPENAI_MODEL if AI_PROVIDER == "openai" else (GEMINI_ANALYSIS_MODEL if AI_PROVIDER == "gemini" else OLLAMA_ANALYSIS_MODEL)
)
ANALYSIS_FALLBACK_MODELS = [
    m.strip() for m in os.getenv(
        "ANALYSIS_FALLBACK_MODELS",
        ",".join(
            [OPENAI_MODEL] if AI_PROVIDER == "openai" else (
                GEMINI_MODEL_CANDIDATES if AI_PROVIDER == "gemini" else [OLLAMA_ANALYSIS_MODEL, OLLAMA_TEXT_MODEL]
            )
        )
    ).split(",") if m.strip()
]
CHAT_FALLBACK_MODELS = [
    m.strip() for m in os.getenv(
        "CHAT_FALLBACK_MODELS",
        ",".join(
            [OPENAI_MODEL] if AI_PROVIDER == "openai" else (
                GEMINI_MODEL_CANDIDATES if AI_PROVIDER == "gemini" else [OLLAMA_CHAT_MODEL, OLLAMA_TEXT_MODEL]
            )
        )
    ).split(",") if m.strip()
]
TRANSLATE_FALLBACK_MODELS = [
    m.strip() for m in os.getenv(
        "TRANSLATE_FALLBACK_MODELS",
        ",".join(
            [OPENAI_MODEL] if AI_PROVIDER == "openai" else (
                GEMINI_MODEL_CANDIDATES if AI_PROVIDER == "gemini" else [OLLAMA_TRANSLATE_MODEL, OLLAMA_TEXT_MODEL]
            )
        )
    ).split(",") if m.strip()
]
GENAI_RETRY_ATTEMPTS = int(os.getenv("GENAI_RETRY_ATTEMPTS", "3"))
GENAI_RETRY_BASE_DELAY = float(os.getenv("GENAI_RETRY_BASE_DELAY", "1.2"))
ENABLE_LOCAL_ANALYSIS_FALLBACK = os.getenv("ENABLE_LOCAL_ANALYSIS_FALLBACK", "true").strip().lower() in {"1", "true", "yes", "on"}
MAX_CHUNK_CHARS = int(os.getenv("RAG_MAX_CHUNK_CHARS", "1400"))
CHUNK_OVERLAP_CHARS = int(os.getenv("RAG_CHUNK_OVERLAP_CHARS", "250"))
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "8"))
HISTORY_WINDOW = int(os.getenv("RAG_HISTORY_WINDOW", "6"))

# VLM settings for scanned/image-heavy PDFs
VLM_ENABLED = os.getenv("VLM_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
VLM_MODEL = os.getenv("VLM_MODEL", "")
VLM_PDF_STRATEGY = os.getenv("VLM_PDF_STRATEGY", "always").strip().lower()
VLM_MIN_EXTRACTED_CHARS = int(os.getenv("VLM_MIN_EXTRACTED_CHARS", "1200"))
VLM_MIN_TEXT_PAGE_RATIO = float(os.getenv("VLM_MIN_TEXT_PAGE_RATIO", "0.5"))

ANALYZE_PERF_PROFILE = os.getenv("ANALYZE_PERF_PROFILE", "balanced").strip().lower()
_ANALYZE_PROFILES: Dict[str, Dict[str, int]] = {
    "fast": {
        "direct_char_limit": 22000,
        "chunk_char_limit": 9000,
        "chunk_overlap": 800,
        "max_chunks": 12,
        "max_key_clauses": 28,
        "max_risks": 20,
        "hard_char_limit": 220000,
        "max_simplified_chars": 14000,
    },
    "balanced": {
        "direct_char_limit": 32000,
        "chunk_char_limit": 12000,
        "chunk_overlap": 1200,
        "max_chunks": 20,
        "max_key_clauses": 40,
        "max_risks": 30,
        "hard_char_limit": 500000,
        "max_simplified_chars": 26000,
    },
    "deep": {
        "direct_char_limit": 42000,
        "chunk_char_limit": 14000,
        "chunk_overlap": 1600,
        "max_chunks": 32,
        "max_key_clauses": 60,
        "max_risks": 45,
        "hard_char_limit": 900000,
        "max_simplified_chars": 42000,
    },
}
_analyze_profile = _ANALYZE_PROFILES.get(ANALYZE_PERF_PROFILE, _ANALYZE_PROFILES["balanced"])

# Large-document analysis settings (profile defaults, env overrides supported)
ANALYZE_DIRECT_CHAR_LIMIT = int(os.getenv("ANALYZE_DIRECT_CHAR_LIMIT", str(_analyze_profile["direct_char_limit"])))
ANALYZE_CHUNK_CHAR_LIMIT = int(os.getenv("ANALYZE_CHUNK_CHAR_LIMIT", str(_analyze_profile["chunk_char_limit"])))
ANALYZE_CHUNK_OVERLAP = int(os.getenv("ANALYZE_CHUNK_OVERLAP", str(_analyze_profile["chunk_overlap"])))
ANALYZE_MAX_CHUNKS = int(os.getenv("ANALYZE_MAX_CHUNKS", str(_analyze_profile["max_chunks"])))
ANALYZE_MAX_KEY_CLAUSES = int(os.getenv("ANALYZE_MAX_KEY_CLAUSES", str(_analyze_profile["max_key_clauses"])))
ANALYZE_MAX_RISKS = int(os.getenv("ANALYZE_MAX_RISKS", str(_analyze_profile["max_risks"])))
ANALYZE_HARD_CHAR_LIMIT = int(os.getenv("ANALYZE_HARD_CHAR_LIMIT", str(_analyze_profile["hard_char_limit"])))
ANALYZE_MAX_SIMPLIFIED_CHARS = int(os.getenv("ANALYZE_MAX_SIMPLIFIED_CHARS", str(_analyze_profile["max_simplified_chars"])))

STOPWORDS: Set[str] = {
    "a", "an", "the", "and", "or", "to", "of", "in", "on", "for", "with", "as", "by", "from",
    "at", "is", "are", "was", "were", "be", "been", "being", "this", "that", "it", "its", "if",
    "then", "than", "into", "under", "over", "about", "can", "could", "should", "would", "will",
    "shall", "may", "might", "must", "do", "does", "did", "have", "has", "had", "we", "you", "they"
}


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


def _is_low_confidence_vlm_text(text: str) -> bool:
    cleaned = _normalize_whitespace(text or "")
    if len(cleaned) < 120:
        return True

    low = cleaned.lower()
    bad_signals = [
        "unable to read",
        "cannot read",
        "can't read",
        "not clear",
        "blurry",
        "unclear",
        "provide a clearer image",
        "please provide a clearer",
        "scanned or photographed document",
        "i am unable to",
    ]
    return any(signal in low for signal in bad_signals)


def _strip_markdown_noise(text: str) -> str:
    cleaned = text or ""
    cleaned = re.sub(r"```(?:[a-zA-Z]+)?", "", cleaned)
    cleaned = cleaned.replace("```", "")
    cleaned = re.sub(r"(?m)^\s*#+\s*", "", cleaned)
    cleaned = cleaned.replace("**", "")
    cleaned = cleaned.replace("__", "")
    cleaned = re.sub(r"(?m)^\s*[-*]\s+", "", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return _normalize_whitespace(cleaned)


def _normalized_similarity(a: str, b: str) -> float:
    left = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", (a or "").lower())).strip()
    right = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", (b or "").lower())).strip()
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()


def _looks_unsimplified(simplified_text: str, source_text: str) -> bool:
    simplified = _normalize_whitespace(simplified_text or "")
    source = _normalize_whitespace(source_text or "")
    if not source:
        return False
    if not simplified:
        return True

    if len(simplified) < min(180, max(240, int(len(source) * 0.12))) and len(source) > 1000:
        return True

    similarity = _normalized_similarity(simplified, source)
    legalese_signals = [
        "hereinafter",
        "shall",
        "whereas",
        "supersedes",
        "force majeure",
        "jurisdiction",
        "subject to",
    ]
    legalese_hits = sum(1 for signal in legalese_signals if signal in simplified.lower())

    page_markers = bool(re.search(r"\[\s*page\s*\d+\s*\]", simplified, flags=re.IGNORECASE))
    if page_markers:
        return True

    if similarity >= SIMPLIFY_SIMILARITY_THRESHOLD and legalese_hits >= 2:
        return True

    return similarity >= max(0.86, SIMPLIFY_SIMILARITY_THRESHOLD + 0.08)


def _rewrite_simplified_text(source_text: str) -> str:
    source = _normalize_whitespace(source_text or "")[:SIMPLIFY_REWRITE_SOURCE_CHAR_LIMIT]
    if not source:
        return ""

    rewrite_prompt = f"""Rewrite the legal text below into clear plain English for a non-lawyer.

Rules:
1) Keep all important facts, numbers, dates, payment amounts, and obligations accurate.
2) Replace legal jargon with simple words.
3) Keep structure readable with short paragraphs and bullet points where useful.
4) Do not copy the original wording sentence-by-sentence.
5) Return plain text only.

Legal text:
---
{source}
---
"""

    rewritten = _generate_content_with_retry(
        primary_model=ANALYSIS_MODEL,
        fallback_models=ANALYSIS_FALLBACK_MODELS,
        contents=rewrite_prompt,
    )
    return _strip_markdown_noise(rewritten)


def _ensure_simplified_text_quality(simplified_text: str, source_text: str) -> str:
    candidate = _strip_markdown_noise(simplified_text or "")
    source = _normalize_whitespace(source_text or "")

    if not SIMPLIFY_REWRITE_ENABLED or not source:
        return candidate or source[:ANALYZE_MAX_SIMPLIFIED_CHARS]

    if not _looks_unsimplified(candidate, source):
        return candidate[:ANALYZE_MAX_SIMPLIFIED_CHARS]

    try:
        rewritten = _rewrite_simplified_text(source)
        if rewritten and not _looks_unsimplified(rewritten, source):
            return rewritten[:ANALYZE_MAX_SIMPLIFIED_CHARS]
        if rewritten:
            return rewritten[:ANALYZE_MAX_SIMPLIFIED_CHARS]
    except Exception as err:
        print(f"Simplified-text rewrite failed: {err}")

    return (candidate or source)[:ANALYZE_MAX_SIMPLIFIED_CHARS]


def _looks_weak_summary(summary_text: str, source_text: str) -> bool:
    summary = _normalize_whitespace(summary_text or "")
    source = _normalize_whitespace(source_text or "")
    if not source:
        return False
    if not summary:
        return True

    if bool(re.search(r"\[\s*page\s*\d+\s*\]", summary, flags=re.IGNORECASE)):
        return True

    if len(source) > 1800 and len(summary) < 260:
        return True

    similarity = _normalized_similarity(summary, source)
    if similarity >= SUMMARY_SIMILARITY_THRESHOLD and len(summary) > 180:
        return True

    coverage_topics = [
        ("payment", ["payment", "fee", "cost", "inr", "%"]),
        ("duration", ["valid", "effective", "until", "term", "duration"]),
        ("termination", ["terminate", "termination", "notice"]),
        ("confidentiality", ["confidential", "non-disclosure"]),
        ("jurisdiction", ["jurisdiction", "court", "dispute"]),
    ]
    missing_important = 0
    src_low = source.lower()
    sum_low = summary.lower()
    for _, keys in coverage_topics:
        if any(k in src_low for k in keys) and not any(k in sum_low for k in keys):
            missing_important += 1

    return missing_important >= 2


def _rewrite_summary_text(source_text: str) -> str:
    source = _normalize_whitespace(source_text or "")[:SUMMARY_REWRITE_SOURCE_CHAR_LIMIT]
    if not source:
        return ""

    prompt = f"""Create an executive summary of the legal document below in plain English.

Requirements:
1) Keep it concise (6-10 bullet points).
2) Include parties, purpose, duration/effective dates, payment terms, confidentiality, termination, and dispute jurisdiction when available.
3) Mention critical risk-sensitive points clearly.
4) Do not copy the original wording.
5) Return plain text only.

Document:
---
{source}
---
"""

    rewritten = _generate_content_with_retry(
        primary_model=ANALYSIS_MODEL,
        fallback_models=ANALYSIS_FALLBACK_MODELS,
        contents=prompt,
    )
    return _strip_markdown_noise(rewritten)


def _ensure_summary_quality(summary_text: str, source_text: str) -> str:
    candidate = _strip_markdown_noise(summary_text or "")
    source = _normalize_whitespace(source_text or "")

    if not SUMMARY_REWRITE_ENABLED or not source:
        return candidate or "Summary could not be generated for this document."

    if not _looks_weak_summary(candidate, source):
        return candidate

    try:
        rewritten = _rewrite_summary_text(source)
        if rewritten:
            return rewritten
    except Exception as err:
        print(f"Summary rewrite failed: {err}")

    return candidate or source[:360]


def _normalize_risk_entries(risk_items: Any) -> List[Dict[str, str]]:
    normalized_risks: List[Dict[str, str]] = []
    items = risk_items if isinstance(risk_items, list) else []
    for item in items:
        if isinstance(item, dict):
            severity = _strip_markdown_noise(str(item.get("severity") or "Medium")).strip().capitalize()
            if severity not in {"High", "Medium", "Low"}:
                severity = "Medium"
            normalized_risks.append({
                "risk": _strip_markdown_noise(str(item.get("risk") or "Potential contractual risk identified."))[:360],
                "mitigation": _strip_markdown_noise(str(item.get("mitigation") or "Review this clause with legal counsel before signing."))[:360],
                "severity": severity,
                "applicableLaw": _strip_markdown_noise(str(item.get("applicableLaw") or "Not specified"))[:220],
                "punishment": _strip_markdown_noise(str(item.get("punishment") or "Not specified"))[:280],
            })
        elif isinstance(item, str):
            normalized_risks.append({
                "risk": _strip_markdown_noise(item)[:360],
                "mitigation": "Review this clause with legal counsel before signing.",
                "severity": "Medium",
                "applicableLaw": "Not specified",
                "punishment": "Not specified",
            })
    return [r for r in normalized_risks if r.get("risk")][:ANALYZE_MAX_RISKS]


def _extract_clause_evidence_for_risk(risk_text: str, source_text: str) -> str:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", _normalize_whitespace(source_text or "")) if len(s.strip()) >= 30]
    if not sentences:
        return ""

    risk_tokens = set(re.findall(r"[a-z0-9]+", (risk_text or "").lower()))
    best_sentence = ""
    best_score = 0
    for sentence in sentences:
        tokens = set(re.findall(r"[a-z0-9]+", sentence.lower()))
        score = len(risk_tokens.intersection(tokens))
        if score > best_score:
            best_score = score
            best_sentence = sentence

    if best_sentence and best_score >= 2:
        return best_sentence[:220]
    return ""


def _calibrate_risk_severity(risk_text: str, source_text: str, current: str) -> str:
    text = f"{risk_text} {_extract_clause_evidence_for_risk(risk_text, source_text)}".lower()
    high_signals = ["termination", "indemnity", "liability", "penalty", "damages", "confidential", "breach", "interest"]
    medium_signals = ["delay", "scope", "dispute", "jurisdiction", "payment", "notice", "change request"]

    high_hits = sum(1 for signal in high_signals if signal in text)
    medium_hits = sum(1 for signal in medium_signals if signal in text)

    if high_hits >= 2:
        return "High"
    if high_hits == 1 or medium_hits >= 2:
        return "Medium"
    if current in {"High", "Medium", "Low"}:
        return current
    return "Low"


def _infer_indian_law_context(risk_text: str, source_text: str) -> Tuple[str, str]:
    risk_only = (risk_text or "").lower()
    text = f"{risk_text} {source_text}".lower()
    mapping = [
        (
            ["confidential", "data", "privacy", "disclosure"],
            "Indian Contract Act, 1872 and Information Technology Act, 2000",
            "Unauthorized disclosure can trigger civil damages and potential action under data-protection related provisions.",
        ),
        (
            ["termination", "notice", "breach"],
            "Indian Contract Act, 1872",
            "Wrongful termination may result in compensation claims for losses caused by breach.",
        ),
        (
            ["liability", "indemnity", "damages"],
            "Indian Contract Act, 1872",
            "Parties may be liable for compensatory damages for proven contractual breaches.",
        ),
        (
            ["intellectual property", "ip", "copyright", "ownership"],
            "Copyright Act, 1957 and Indian Contract Act, 1872",
            "IP disputes may result in injunctions, damages, or restrictions on software use/ownership.",
        ),
        (
            ["payment", "fee", "interest", "default"],
            "Indian Contract Act, 1872",
            "Breach can lead to recovery of dues, interest claims, and damages through civil action.",
        ),
        (
            ["jurisdiction", "court", "dispute"],
            "Code of Civil Procedure, 1908",
            "Disputes may proceed in designated courts; parties can face litigation costs and adverse decrees.",
        ),
    ]

    # Prefer the risk sentence itself to avoid unrelated-topic leakage from full document text.
    for signals, law, punishment in mapping:
        if any(signal in risk_only for signal in signals):
            return law, punishment

    for signals, law, punishment in mapping:
        if any(signal in text for signal in signals):
            return law, punishment

    return "Indian Contract Act, 1872", "Breach of contractual terms can lead to civil remedies including damages and specific performance."


def _risk_priority_score(risk: Dict[str, str]) -> int:
    severity_weight = {"High": 90, "Medium": 55, "Low": 20}.get(str(risk.get("severity") or "Medium"), 40)
    text = str(risk.get("risk") or "").lower()
    bonus = 0
    for key, weight in [
        ("payment", 12),
        ("interest", 12),
        ("termination", 14),
        ("confidential", 14),
        ("liability", 14),
        ("indemnity", 14),
        ("jurisdiction", 10),
    ]:
        if key in text:
            bonus += weight
    return severity_weight + bonus


def _enrich_risk_entries(risk_items: List[Dict[str, str]], source_text: str) -> List[Dict[str, str]]:
    enriched: List[Dict[str, str]] = []
    seen: Set[str] = set()
    for item in _normalize_risk_entries(risk_items):
        risk_text = _strip_markdown_noise(str(item.get("risk") or ""))[:360]
        if not risk_text:
            continue
        key = risk_text.lower()
        if key in seen:
            continue
        seen.add(key)

        severity = _calibrate_risk_severity(risk_text, source_text, str(item.get("severity") or "Medium"))
        evidence = _extract_clause_evidence_for_risk(risk_text, source_text)

        law = _strip_markdown_noise(str(item.get("applicableLaw") or "")).strip()
        punishment = _strip_markdown_noise(str(item.get("punishment") or "")).strip()
        if law.lower() in {"", "not specified"} or punishment.lower() in {"", "not specified"}:
            inferred_law, inferred_punishment = _infer_indian_law_context(risk_text, source_text)
            law = law if law.lower() not in {"", "not specified"} else inferred_law
            punishment = punishment if punishment.lower() not in {"", "not specified"} else inferred_punishment

        mitigation = _strip_markdown_noise(str(item.get("mitigation") or "")).strip()
        if not mitigation or "review this clause" in mitigation.lower():
            mitigation = "Define explicit controls, timelines, and contractual safeguards for this clause, and document acceptance criteria."
        if evidence:
            mitigation = f"{mitigation} Trigger clause: {evidence}"

        enriched.append({
            "risk": risk_text,
            "mitigation": mitigation[:360],
            "severity": severity,
            "applicableLaw": law[:220],
            "punishment": punishment[:280],
        })

    enriched.sort(key=_risk_priority_score, reverse=True)
    return enriched[:ANALYZE_MAX_RISKS]


def _looks_weak_risk_analysis(risk_items: List[Dict[str, str]], source_text: str) -> bool:
    if not risk_items:
        return True

    low_risks = [str(item.get("risk") or "").lower() for item in risk_items]
    generic_signals = [
        "detailed risk extraction was limited",
        "temporarily unavailable",
        "retry with a larger local model",
        "not specified",
    ]
    generic_hits = sum(1 for risk in low_risks if any(sig in risk for sig in generic_signals))
    if generic_hits >= max(1, math.ceil(len(low_risks) * 0.5)):
        return True

    src_low = (source_text or "").lower()
    likely_topics = [
        ["payment", "fee", "interest"],
        ["terminate", "termination", "notice"],
        ["confidential", "non-disclosure"],
        ["jurisdiction", "court", "dispute"],
        ["liability", "indemnity", "damages"],
    ]
    topic_count = sum(1 for topic in likely_topics if any(k in src_low for k in topic))
    if topic_count >= 3 and len(risk_items) < RISK_REWRITE_MIN_ITEMS:
        return True

    return False


def _rewrite_risk_analysis(source_text: str) -> List[Dict[str, str]]:
    source = _normalize_whitespace(source_text or "")[:RISK_REWRITE_SOURCE_CHAR_LIMIT]
    if not source:
        return []

    prompt = f"""Analyze the legal document below and return only document-specific legal risks.

Return STRICT JSON in this shape only:
{{
  "riskAnalysis": [
    {{
      "risk": "...",
      "mitigation": "...",
      "severity": "High|Medium|Low",
      "applicableLaw": "Relevant Indian law",
      "punishment": "Potential legal consequence"
    }}
  ]
}}

Rules:
1) Return 4 to 8 risks if available from the document.
2) Risks must be concrete and tied to actual clauses.
3) Avoid generic placeholders.
4) Mention Indian legal context where possible.
5) JSON only, no markdown.

Document:
---
{source}
---
"""

    parsed = _run_structured_analysis(prompt)
    if isinstance(parsed, dict):
        return _normalize_risk_entries(parsed.get("riskAnalysis"))
    return []


def _ensure_risk_analysis_quality(risk_items: List[Dict[str, str]], source_text: str) -> List[Dict[str, str]]:
    current = _enrich_risk_entries(risk_items, source_text)
    if not RISK_REWRITE_ENABLED:
        return current

    if not _looks_weak_risk_analysis(current, source_text):
        return current

    try:
        rewritten = _rewrite_risk_analysis(source_text)
        rewritten = _enrich_risk_entries(rewritten, source_text)
        if rewritten and not _looks_weak_risk_analysis(rewritten, source_text):
            return rewritten[:ANALYZE_MAX_RISKS]
        if rewritten:
            return rewritten[:ANALYZE_MAX_RISKS]
    except Exception as err:
        print(f"Risk rewrite failed: {err}")

    return current


def _extract_pdf_text_with_vlm(pdf_bytes: bytes) -> str:
    if not VLM_ENABLED:
        return ""
    if AI_PROVIDER != "ollama":
        return ""
    if not OLLAMA_VLM_MODEL:
        return ""
    if pdfium is None or Image is None:
        print("VLM extraction skipped: install pypdfium2 and Pillow for PDF page rendering.")
        return ""

    try:
        document = pdfium.PdfDocument(BytesIO(pdf_bytes))
    except Exception as err:
        print(f"VLM extraction skipped: failed to read PDF with pdfium: {err}")
        return ""

    page_count = min(len(document), max(1, OLLAMA_MAX_VLM_PAGES))
    excerpts: List[str] = []
    for idx in range(page_count):
        try:
            page = document[idx]
            bitmap = page.render(scale=2.0)
            pil_image = bitmap.to_pil()
            image_buffer = BytesIO()
            pil_image.save(image_buffer, format="JPEG", quality=85)
            image_b64 = base64.b64encode(image_buffer.getvalue()).decode("utf-8")

            prompt = (
                "Extract readable legal text from this document page. "
                "Return plain text only, preserving important clauses and numbers."
            )
            page_text = _ollama_generate_content(OLLAMA_VLM_MODEL, prompt, images=[image_b64])
            page_text = _normalize_whitespace(page_text)
            if page_text and not _is_low_confidence_vlm_text(page_text):
                excerpts.append(f"[PAGE {idx + 1}]\n{page_text}")
            else:
                print(f"VLM extraction page {idx + 1} returned low-confidence text, skipping VLM page output.")
        except Exception as err:
            print(f"VLM extraction page {idx + 1} failed: {err}")

    return _normalize_whitespace("\n\n".join(excerpts)) if excerpts else ""


def _ollama_http_request(endpoint: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{OLLAMA_BASE_URL}{endpoint}"
    payload = json.dumps(request_data).encode("utf-8")
    headers = {"Content-Type": "application/json"}

    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=OLLAMA_TIMEOUT_SECONDS) as response:
            raw = response.read().decode("utf-8")
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                # Some Ollama setups return NDJSON chunks; merge them safely.
                parts: List[Dict[str, Any]] = []
                for line in raw.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        item = json.loads(line)
                        if isinstance(item, dict):
                            parts.append(item)
                    except json.JSONDecodeError:
                        continue

                if not parts:
                    raise

                merged: Dict[str, Any] = {}
                if any("response" in p for p in parts):
                    merged["response"] = "".join(str(p.get("response", "")) for p in parts)

                # Keep terminal metadata from the final chunk.
                for key, value in parts[-1].items():
                    if key != "response":
                        merged[key] = value

                return merged
    except HTTPError as err:
        body = err.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Ollama request failed: {err.code} {err.reason} {body}")
    except URLError as err:
        raise RuntimeError(f"Ollama request failed: {err.reason}")


def _ollama_generate_content(model_name: str, contents: Any, images: Optional[List[str]] = None) -> str:
    if isinstance(contents, list):
        prompt = "\n\n".join([str(item) for item in contents])
    else:
        prompt = str(contents)

    request_data: Dict[str, Any] = {
        "model": model_name,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0,
        }
    }
    if images:
        request_data["images"] = images

    response = _ollama_http_request("/api/generate", request_data)
    text = str(response.get("response", "")).strip()
    if not text:
        raise RuntimeError("Ollama response did not contain generated text.")
    return text
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
        # Strategy: run VLM first for PDFs when requested (best for scanned/image-heavy docs).
        if VLM_ENABLED and VLM_PDF_STRATEGY == "always":
            vlm_text = _extract_pdf_text_with_vlm(raw)
            if vlm_text:
                return vlm_text

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


def _run_structured_analysis(contents: str) -> Dict[str, Any]:
    response_text = _generate_content_with_retry(
        primary_model=ANALYSIS_MODEL,
        fallback_models=ANALYSIS_FALLBACK_MODELS,
        contents=contents
    )
    cleaned = response_text.strip()

    # Handle fenced JSON blocks often returned by LLMs.
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Recover JSON if model wrapped it with extra explanatory text.
        decoder = json.JSONDecoder()
        start_positions = [m.start() for m in re.finditer(r"\{", cleaned)]
        for start in start_positions:
            try:
                obj, _ = decoder.raw_decode(cleaned[start:])
                if isinstance(obj, dict):
                    return obj
            except json.JSONDecodeError:
                continue

        # Last resort for local models that don't follow strict JSON output.
        return {
            "simplifiedText": cleaned,
            "summary": cleaned[:800],
        }


def _is_transient_model_error(err: Exception) -> bool:
    msg = str(err).lower()
    transient_signals = [
        "503",
        "unavailable",
        "high demand",
        "resource exhausted",
        "rate limit",
        "deadline exceeded",
        "temporarily"
    ]
    return any(signal in msg for signal in transient_signals)


def _openai_generate_content(model_name: str, contents: Any) -> str:
    if isinstance(contents, list):
        user_content = "\n\n".join([str(item) for item in contents])
    else:
        user_content = str(contents)

    response = openai_client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "You are an expert legal assistant."},
            {"role": "user", "content": user_content}
        ],
        temperature=0.0,
        max_tokens=2000,
    )
    return response.choices[0].message["content"].strip()


def _gemini_http_request(endpoint: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{endpoint}?key={GEMINI_API_KEY}"
    payload = json.dumps(request_data).encode("utf-8")
    headers = {"Content-Type": "application/json"}

    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as err:
        body = err.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Gemini API request failed: {err.code} {err.reason} {body}")
    except URLError as err:
        raise RuntimeError(f"Gemini API request failed: {err.reason}")


def _gemini_generate_content(model_name: str, contents: Any) -> str:
    if isinstance(contents, list):
        user_content = "\n\n".join([str(item) for item in contents])
    else:
        user_content = str(contents)

    prompt_text = "You are an expert legal assistant.\n\n" + user_content

    # Preferred modern endpoint for Gemini.
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
    response = _gemini_http_request(endpoint, {
        "contents": [{"parts": [{"text": prompt_text}]}],
        "generationConfig": {
            "temperature": 0.0,
            "maxOutputTokens": 2000,
        },
    })

    candidates = response.get("candidates") or []
    if candidates:
        parts = ((candidates[0].get("content") or {}).get("parts") or [])
        text = "".join(str(p.get("text", "")) for p in parts if isinstance(p, dict)).strip()
        if text:
            return text

        legacy_output = str(candidates[0].get("output", "")).strip()
        if legacy_output:
            return legacy_output

    output = response.get("output")
    if isinstance(output, str) and output.strip():
        return output.strip()

    raise RuntimeError("Gemini response did not contain generated text.")


def _generate_content_with_retry(
    primary_model: str,
    fallback_models: List[str],
    contents: Any,
    config: Optional[Any] = None
):
    models_to_try = [primary_model] + [m for m in fallback_models if m != primary_model]
    attempts = max(1, GENAI_RETRY_ATTEMPTS)
    last_error: Optional[Exception] = None

    for model_name in models_to_try:
        for attempt in range(1, attempts + 1):
            try:
                if AI_PROVIDER == "openai":
                    return _openai_generate_content(model_name, contents)
                if AI_PROVIDER == "gemini":
                    return _gemini_generate_content(model_name, contents)
                if AI_PROVIDER == "ollama":
                    return _ollama_generate_content(model_name, contents)
                raise RuntimeError(f"Unsupported AI_PROVIDER: {AI_PROVIDER}")
            except Exception as err:
                last_error = err
                if not _is_transient_model_error(err):
                    raise
                if attempt < attempts:
                    time.sleep(GENAI_RETRY_BASE_DELAY * attempt)
        print(f"Model {model_name} failed after {attempts} attempt(s). Trying fallback if available...")

    raise RuntimeError(f"All configured models failed after retries. Last error: {last_error}")


def _sanitize_provider_error(err: Exception) -> str:
    # Remove any accidental API key leakage in upstream SDK error strings.
    raw = re.sub(r"(AIza[0-9A-Za-z\-_]{20,}|sk-[0-9A-Za-z\-_]{40,})", "[REDACTED_API_KEY]", str(err))
    low = raw.lower()

    if "consumer_suspended" in low or "has been suspended" in low:
        return "API key is suspended. Use an active API key or check provider account status."
    if "permission_denied" in low or "403" in low:
        return "API access denied. Check your API key validity, billing, and provider access."
    if "503" in low or "unavailable" in low or "high demand" in low:
        return "The AI service is temporarily unavailable due to high demand. Please retry in a moment."
    if "resource_exhausted" in low or "resource exhausted" in low or "quota" in low or "free_tier" in low or "rate limit" in low:
        return "API quota or rate limit has been reached. Please check your billing/quota and retry later."

    return f"AI request failed: {raw}"


def _is_provider_failure(err: Exception) -> bool:
    msg = str(err).lower()
    provider_signals = [
        "permission_denied",
        "consumer_suspended",
        "resource_exhausted",
        "rate limit",
        "quota",
        "unavailable",
        "googleapis",
        "openai",
        "ollama",
        "connection refused",
        "failed to connect",
        "404",
        "not found",
        "requested entity was not found",
        "gemini api request failed"
    ]
    return any(signal in msg for signal in provider_signals)


def _detect_document_type(text: str) -> str:
    low = text.lower()
    patterns = [
        ("employment", "Employment Agreement"),
        ("lease", "Lease Agreement"),
        ("rental", "Rental Agreement"),
        ("service", "Service Agreement"),
        ("nda", "Non-Disclosure Agreement"),
        ("non-disclosure", "Non-Disclosure Agreement"),
        ("purchase", "Purchase Agreement"),
        ("sale deed", "Sale Deed"),
        ("policy", "Policy Document"),
        ("notice", "Legal Notice"),
    ]
    for key, label in patterns:
        if key in low:
            return label
    return "Legal Document"


def _extract_parties(text: str) -> List[str]:
    parties: List[str] = []
    between_match = re.search(r"between\s+(.+?)\s+and\s+(.+?)(?:[\.,;\n]|$)", text, flags=re.IGNORECASE)
    if between_match:
        for val in between_match.groups():
            party = re.sub(r"\s+", " ", val).strip(" .,;:-")
            if party:
                parties.append(party)

    title_case_hits = re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\b", text[:4000])
    for hit in title_case_hits:
        if hit.lower() in {"this", "that", "agreement", "document", "party"}:
            continue
        if hit not in parties:
            parties.append(hit)
        if len(parties) >= 8:
            break

    return parties[:8] or ["Not specified"]


def _local_clause_type(sentence: str) -> str:
    low = sentence.lower()
    if any(k in low for k in ["confidential", "non-disclosure", "nda", "privacy"]):
        return "Confidentiality"
    if any(k in low for k in ["terminate", "termination", "cancel", "rescission", "notice period"]):
        return "Termination"
    if any(k in low for k in ["payment", "fee", "invoice", "consideration", "payable", "charges"]):
        return "Payment"
    if any(k in low for k in ["indemnity", "liability", "warranty", "limitation of liability"]):
        return "Liability"
    if any(k in low for k in ["means", "hereinafter", "referred to as", "collectively referred"]):
        return "Definition"
    if any(k in low for k in ["scope", "services", "deliverables", "statement of work", "purpose"]):
        return "Scope"
    if any(k in low for k in ["penalty", "liquidated", "damages", "fine"]):
        return "Penalty"
    if any(k in low for k in ["effective date", "term", "duration", "expiry", "expires"]):
        return "Date"
    if any(k in low for k in ["shall", "must", "required", "obligation"]):
        return "Obligation"
    if any(k in low for k in ["entitled", "right", "may"]):
        return "Right"
    if any(k in low for k in ["if", "provided that", "subject to", "condition"]):
        return "Condition"
    return "Other"


def _normalize_clause_type(clause_type: str, clause_text: str) -> str:
    raw = (clause_type or "").strip().lower()
    aliases = {
        "obligation": "Obligation",
        "duty": "Obligation",
        "penalty": "Penalty",
        "date": "Date",
        "right": "Right",
        "condition": "Condition",
        "confidentiality": "Confidentiality",
        "non-disclosure": "Confidentiality",
        "termination": "Termination",
        "payment": "Payment",
        "fees": "Payment",
        "liability": "Liability",
        "indemnity": "Liability",
        "definition": "Definition",
        "scope": "Scope",
        "other": "Other",
        "": "Other",
    }
    normalized = aliases.get(raw, "")
    if normalized and normalized != "Other":
        return normalized
    return _local_clause_type(clause_text)


def _clean_clause_text(text: str) -> str:
    cleaned = _strip_markdown_noise(text or "")
    cleaned = re.sub(r"\[\s*page\s*\d+\s*\]", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(in simple terms|summary|note)\s*:\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"[""'`“”‘’]", "", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip(" -:;,.\n\t")


def _split_clause_candidates(text: str, max_items: int = 4) -> List[str]:
    cleaned = _clean_clause_text(text)
    if not cleaned:
        return []

    protected = re.sub(r"\b(Mr|Mrs|Ms|Dr)\.", lambda m: m.group(1) + "<DOT>", cleaned)
    sentence_parts = [
        s.replace("<DOT>", ".").strip()
        for s in re.split(r"(?<=[.!?])\s+", protected)
        if s.strip()
    ]

    pieces: List[str] = []
    carry = ""
    for sentence in sentence_parts:
        normalized = sentence.strip(" -")
        if not normalized:
            continue
        if carry:
            normalized = f"{carry} {normalized}".strip()
            carry = ""
        if len(normalized) < 55:
            carry = normalized
            continue
        pieces.append(normalized)

    if carry and len(carry) >= 45:
        pieces.append(carry)

    if not pieces and len(cleaned) >= 30:
        pieces = [cleaned]

    deduped: List[str] = []
    seen: Set[str] = set()
    for piece in pieces:
        key = piece.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(piece[:420])
        if len(deduped) >= max_items:
            break

    return deduped


def _clause_priority_score(clause: str, clause_type: str) -> int:
    low = clause.lower()
    score = 0

    type_weights = {
        "Termination": 90,
        "Liability": 90,
        "Penalty": 85,
        "Payment": 80,
        "Confidentiality": 80,
        "Obligation": 70,
        "Condition": 60,
        "Date": 40,
        "Right": 35,
        "Scope": 25,
        "Definition": 20,
        "Other": 5,
    }
    score += type_weights.get(clause_type, 0)

    keyword_weights = [
        ("terminate", 45),
        ("termination", 45),
        ("indemnity", 40),
        ("liability", 40),
        ("damages", 36),
        ("penalty", 36),
        ("payment", 34),
        ("fee", 30),
        ("invoice", 28),
        ("confidential", 34),
        ("non-disclosure", 34),
        ("notice", 20),
        ("shall", 12),
        ("must", 12),
    ]
    for key, weight in keyword_weights:
        if key in low:
            score += weight

    if "entered into on" in low:
        score -= 18
    if "collectively referred" in low:
        score -= 14
    if len(clause) < 45:
        score -= 10

    return score


def _build_clause_explanation(clause_type: str, clause_text: str) -> str:
    low = clause_text.lower()
    templates = {
        "Obligation": "This sets a mandatory duty that at least one party must perform.",
        "Right": "This gives a party a permission or entitlement under the agreement.",
        "Condition": "This applies only when a specific condition is met.",
        "Date": "This defines timing, duration, or validity period of the agreement.",
        "Payment": "This specifies payment responsibilities, charges, or billing timelines.",
        "Termination": "This explains how and when either party can end the agreement.",
        "Confidentiality": "This requires protection of confidential information.",
        "Liability": "This sets legal responsibility or limits for losses and damages.",
        "Penalty": "This describes consequences if contractual obligations are breached.",
        "Scope": "This describes the services, deliverables, or work covered by the agreement.",
        "Definition": "This defines important terms or party references used in the contract.",
        "Other": "This is an important contractual statement extracted from the document.",
    }

    explanation = templates.get(clause_type, templates["Other"])
    if "may" in low and clause_type in {"Termination", "Right"}:
        explanation += " It explicitly grants an optional right to act."
    if "shall" in low and clause_type == "Obligation":
        explanation += " The word 'shall' indicates this is binding."
    return explanation[:320]


def _is_generated_explanation(text: str) -> bool:
    low = (text or "").strip().lower()
    return low == "" or "auto-generated from detected clause text" in low or "generated from available model output" in low


def _extract_sentences_for_clause_search(text: str) -> List[str]:
    normalized = _normalize_whitespace(text or "")
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", normalized) if len(s.strip()) >= 35]


def _ensure_key_clause_coverage(key_clauses: List[Dict[str, str]], source_text: str, max_items: int) -> List[Dict[str, str]]:
    output = list(key_clauses)
    existing_types = {str(item.get("type") or "") for item in output}
    sentences = _extract_sentences_for_clause_search(source_text)
    clause_index_by_text: Dict[str, int] = {
        _clean_clause_text(str(item.get("clause") or "")).lower(): idx
        for idx, item in enumerate(output)
        if _clean_clause_text(str(item.get("clause") or ""))
    }

    wanted = [
        ("Right", [" may ", " entitled ", " has the right", " can ", " option to"]),
        ("Obligation", [" shall ", " must ", " required to ", " is obligated "]),
    ]

    for clause_type, signals in wanted:
        if clause_type in existing_types:
            continue
        candidate = ""
        for sentence in sentences:
            low = f" {sentence.lower()} "
            if any(sig in low for sig in signals):
                candidate = _clean_clause_text(sentence)
                break
        if candidate:
            key = candidate.lower()
            existing_idx = clause_index_by_text.get(key)
            if existing_idx is not None:
                current_type = str(output[existing_idx].get("type") or "Other")
                if current_type in {"Other", "Scope", "Definition", "Condition"}:
                    output[existing_idx]["type"] = clause_type
                    output[existing_idx]["explanation"] = _build_clause_explanation(clause_type, candidate)
            else:
                output.append({
                    "type": clause_type,
                    "clause": candidate[:420],
                    "explanation": _build_clause_explanation(clause_type, candidate),
                })
                clause_index_by_text[key] = len(output) - 1

    return _prioritize_key_clauses(output, max_items)


def _prioritize_key_clauses(key_clauses: List[Dict[str, str]], max_items: int) -> List[Dict[str, str]]:
    cleaned: List[Dict[str, str]] = []
    seen: Set[str] = set()
    for item in key_clauses:
        clause_text = _clean_clause_text(str(item.get("clause") or ""))[:420]
        if len(clause_text) < 25:
            continue

        clause_type = _normalize_clause_type(str(item.get("type") or "Other"), clause_text)
        explanation = _clean_clause_text(str(item.get("explanation") or "Auto-generated from detected clause text."))[:320]
        if _is_generated_explanation(explanation):
            explanation = _build_clause_explanation(clause_type, clause_text)
        key = clause_text.lower()
        if key in seen:
            continue
        seen.add(key)

        cleaned.append({
            "type": clause_type,
            "clause": clause_text,
            "explanation": explanation or "Auto-generated from detected clause text.",
            "_score": str(_clause_priority_score(clause_text, clause_type)),
        })

    if not cleaned:
        return []

    cleaned.sort(key=lambda item: int(item.get("_score", "0")), reverse=True)

    output: List[Dict[str, str]] = []
    for item in cleaned[:max_items]:
        output.append({
            "type": item["type"],
            "clause": item["clause"],
            "explanation": item["explanation"],
        })
    return output


def _looks_like_clause_fallback(key_clauses: List[Dict[str, Any]]) -> bool:
    if not key_clauses:
        return True

    fallback_hits = 0
    noisy_hits = 0
    for item in key_clauses:
        explanation = str(item.get("explanation") or "").lower()
        clause = str(item.get("clause") or "").lower()
        ctype = str(item.get("type") or "").lower()
        if "generated from available model output" in explanation:
            fallback_hits += 1
        if "[page" in clause or ctype == "other":
            noisy_hits += 1

    if len(key_clauses) == 1 and fallback_hits == 1:
        return True

    if len(key_clauses) >= 3 and noisy_hits >= math.ceil(len(key_clauses) * 0.75):
        return True

    return fallback_hits >= max(1, math.ceil(len(key_clauses) * 0.6)) and noisy_hits >= 1


def _retry_key_clause_extraction(document_text: str) -> List[Dict[str, str]]:
    source = _normalize_whitespace(document_text or "")[:18000]
    if not source:
        return []

    retry_prompt = f"""Extract key legal clauses from the document below.

Return STRICT JSON in this exact shape only:
{{
  "keyClauses": [
                {{"type": "Obligation|Penalty|Date|Right|Condition|Payment|Termination|Confidentiality|Liability|Scope|Definition|Other", "clause": "...", "explanation": "..."}}
  ]
}}

Rules:
1) Return 4 to 8 key clauses.
2) Keep each clause under 320 characters.
3) Exclude page markers like [PAGE 1].
4) No markdown, no extra text, JSON only.

Document:
---
{source}
---
"""

    try:
        parsed = _run_structured_analysis(retry_prompt)
    except Exception as err:
        print(f"Key clause retry failed: {err}")
        return []

    candidate_items = parsed.get("keyClauses") if isinstance(parsed, dict) else []
    if not isinstance(candidate_items, list):
        return []

    repaired: List[Dict[str, str]] = []
    for item in candidate_items:
        if isinstance(item, dict):
            clause_text = _clean_clause_text(str(item.get("clause") or ""))
            if not clause_text:
                continue
            ctype = _normalize_clause_type(str(item.get("type") or "Other"), clause_text)
            explanation = _clean_clause_text(str(item.get("explanation") or "This clause may affect your legal obligations."))
            repaired.append({
                "type": ctype,
                "clause": clause_text[:420],
                "explanation": explanation[:320],
            })

    return _prioritize_key_clauses(repaired, ANALYZE_MAX_KEY_CLAUSES)


def _build_local_analysis(document_text: str, reason: str) -> Dict[str, Any]:
    normalized = _normalize_whitespace(document_text)
    sentences = [s.strip() for s in re.split(r"(?<=[\.!?])\s+", normalized) if s.strip()]

    key_clauses: List[Dict[str, str]] = []
    for sentence in sentences[:40]:
        if len(sentence) < 30:
            continue
        ctype = _local_clause_type(sentence)
        if ctype == "Other" and len(key_clauses) >= 2:
            continue
        key_clauses.append({
            "type": ctype,
            "clause": sentence[:320],
            "explanation": "Auto-extracted locally due to temporary AI service limits."
        })
        if len(key_clauses) >= 8:
            break

    risks: List[Dict[str, str]] = []
    lower_text = normalized.lower()
    if any(k in lower_text for k in ["penalty", "damages", "indemnity", "liability"]):
        risks.append({
            "risk": "Potential financial liability terms are present.",
            "mitigation": "Review penalty/indemnity limits and negotiate caps where possible.",
            "severity": "High",
            "applicableLaw": "Indian Contract Act, 1872",
            "punishment": "Breach may result in monetary damages or specific performance orders."
        })
    if "termination" in lower_text:
        risks.append({
            "risk": "Termination terms may be one-sided or restrictive.",
            "mitigation": "Ensure notice period and termination rights are balanced for all parties.",
            "severity": "Medium",
            "applicableLaw": "Indian Contract Act, 1872",
            "punishment": "Wrongful termination can lead to compensation claims."
        })
    if "jurisdiction" not in lower_text and "governing law" not in lower_text:
        risks.append({
            "risk": "No clear governing law or jurisdiction identified.",
            "mitigation": "Add explicit governing law and jurisdiction clauses.",
            "severity": "Medium",
            "applicableLaw": "Code of Civil Procedure, 1908",
            "punishment": "Dispute resolution may become slower and more expensive."
        })

    if not risks:
        risks.append({
            "risk": "Detailed AI risk assessment is temporarily unavailable.",
            "mitigation": "Retry once the AI service is available for a full legal-risk assessment.",
            "severity": "Medium",
            "applicableLaw": "Not specified",
            "punishment": "Not specified",
        })

    date_match = re.search(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})\b", normalized)
    duration_match = re.search(r"\b(\d+\s+(day|days|month|months|year|years))\b", normalized, flags=re.IGNORECASE)
    summary_seed = " ".join(sentences[:2]) if sentences else normalized[:400]

    return {
        "simplifiedText": normalized[:ANALYZE_MAX_SIMPLIFIED_CHARS],
        "summary": f"{summary_seed}\n\nNote: Local fallback analysis was used because AI service is unavailable ({reason}).",
        "keyClauses": key_clauses or [{
            "type": "Other",
            "clause": normalized[:320] if normalized else "Not available",
            "explanation": "No clear clause patterns detected by local fallback parser."
        }],
        "riskAnalysis": risks[:ANALYZE_MAX_RISKS],
        "documentDetails": {
            "documentType": _detect_document_type(normalized),
            "partiesOrEntities": _extract_parties(normalized),
            "date": date_match.group(1) if date_match else "Not specified",
            "duration": duration_match.group(1) if duration_match else "Not applicable",
            "jurisdiction": "Not specified",
            "purpose": summary_seed[:220] if summary_seed else "Not specified",
        },
    }


def _chunk_text_for_analysis(text: str, chunk_limit: int, overlap: int) -> List[str]:
    if len(text) <= chunk_limit:
        return [text]

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: List[str] = []
    buffer = ""

    for para in paragraphs:
        candidate = para if not buffer else f"{buffer}\n\n{para}"
        if len(candidate) <= chunk_limit:
            buffer = candidate
            continue

        if buffer:
            chunks.append(buffer.strip())
            overlap_seed = buffer[-overlap:] if overlap > 0 else ""
            buffer = (overlap_seed + "\n\n" + para).strip()
            if len(buffer) > chunk_limit:
                buffer = para
        else:
            step = max(500, chunk_limit - overlap)
            start = 0
            while start < len(para):
                part = para[start:start + chunk_limit].strip()
                if not part:
                    break
                chunks.append(part)
                start += step

    if buffer:
        chunks.append(buffer.strip())

    return chunks


def _chunk_text_for_translation(text: str, chunk_limit: int) -> List[str]:
    normalized = _normalize_whitespace(text or "")
    if not normalized:
        return []
    if len(normalized) <= chunk_limit:
        return [normalized]

    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", normalized) if s.strip()]
    chunks: List[str] = []
    buffer = ""

    for sentence in sentences:
        if len(sentence) > chunk_limit:
            if buffer:
                chunks.append(buffer.strip())
                buffer = ""
            start = 0
            step = max(300, chunk_limit - 80)
            while start < len(sentence):
                part = sentence[start:start + chunk_limit].strip()
                if part:
                    chunks.append(part)
                start += step
            continue

        candidate = sentence if not buffer else f"{buffer} {sentence}"
        if len(candidate) <= chunk_limit:
            buffer = candidate
        else:
            chunks.append(buffer.strip())
            buffer = sentence

    if buffer:
        chunks.append(buffer.strip())

    return chunks


def _translation_guidance(language: str) -> str:
    lang = (language or "").strip().lower()
    if lang == "tamil":
        return (
            "Use natural formal Tamil suitable for legal readers. "
            "Keep names, dates, amounts, and section numbering exact. "
            "Do not transliterate legal role labels awkwardly (avoid words like 'பாக்டி'); use 'தரப்பு A', 'தரப்பு B'. "
            "Translate legal concepts clearly: jurisdiction=நீதித்துறை வரம்பு, confidentiality=ரகசியத்தன்மை, risk severity as உயர்ந்த/மத்திய/குறைந்த."
        )
    return (
        "Use clear, professional language in the target language. "
        "Preserve names, numbers, legal obligations, and section meaning exactly."
    )


def _postprocess_translation(text: str, language: str) -> str:
    out = _strip_markdown_noise(text or "")
    if (language or "").strip().lower() == "tamil":
        replacements = {
            "பாக்டி": "தரப்பு",
            "பார்டி": "தரப்பு",
            "jurisdiction": "நீதித்துறை வரம்பு",
            "severity": "ஆபத்து நிலை",
        }
        for old, new in replacements.items():
            out = out.replace(old, new)
        out = re.sub(r"\bMr\.\s*", "திரு. ", out)
    return _normalize_whitespace(out)


def _is_default_like(value: str) -> bool:
    norm = (value or "").strip().lower()
    return norm in {"", "not specified", "not applicable", "unknown", "none"}


def _default_analysis_payload() -> Dict[str, Any]:
    return {
        "simplifiedText": "",
        "summary": "",
        "keyClauses": [],
        "riskAnalysis": [],
        "documentDetails": {
            "documentType": "Not specified",
            "partiesOrEntities": [],
            "date": "Not specified",
            "duration": "Not applicable",
            "jurisdiction": "Not specified",
            "purpose": "Not specified",
        },
    }


def _normalize_parties_or_entities(value: Any, source_text: str) -> List[str]:
    if not isinstance(value, list):
        return _extract_parties(source_text)

    parties: List[str] = []
    seen: Set[str] = set()
    for item in value:
        party_text = ""
        if isinstance(item, str):
            party_text = _strip_markdown_noise(item)
        elif isinstance(item, dict):
            # Some models return objects like {name, role}; convert to a display-safe string.
            name = _strip_markdown_noise(str(item.get("name") or item.get("entity") or item.get("party") or "")).strip()
            role = _strip_markdown_noise(str(item.get("role") or item.get("type") or "")).strip()
            if name and role:
                party_text = f"{name} ({role})"
            else:
                party_text = name or role
        else:
            party_text = _strip_markdown_noise(str(item or "")).strip()

        party_text = party_text.strip()
        if not party_text:
            continue
        key = party_text.lower()
        if key in seen:
            continue
        seen.add(key)
        parties.append(party_text)

    return parties or _extract_parties(source_text)


def _coerce_analysis_payload(payload: Dict[str, Any], source_text: str) -> Dict[str, Any]:
    normalized_source = _normalize_whitespace(source_text or "")
    result = _default_analysis_payload()

    # Some local models return only document details at top level.
    incoming = payload or {}
    if "documentDetails" not in incoming and any(k in incoming for k in ["documentType", "partiesOrEntities", "date", "duration", "jurisdiction", "purpose"]):
        incoming = {
            "documentDetails": {
                "documentType": incoming.get("documentType"),
                "partiesOrEntities": incoming.get("partiesOrEntities"),
                "date": incoming.get("date"),
                "duration": incoming.get("duration"),
                "jurisdiction": incoming.get("jurisdiction"),
                "purpose": incoming.get("purpose"),
            }
        }

    simplified = _strip_markdown_noise(str(incoming.get("simplifiedText") or "").strip())
    if not simplified:
        simplified = normalized_source[:ANALYZE_MAX_SIMPLIFIED_CHARS] if normalized_source else "Not available"
    result["simplifiedText"] = simplified

    summary = _strip_markdown_noise(str(incoming.get("summary") or "").strip())
    if not summary:
        sentences = [s.strip() for s in re.split(r"(?<=[\.!?])\s+", simplified) if s.strip()]
        summary = " ".join(sentences[:2]) if sentences else simplified[:280]
    result["summary"] = summary

    key_clauses = incoming.get("keyClauses") if isinstance(incoming.get("keyClauses"), list) else []
    normalized_key_clauses: List[Dict[str, str]] = []
    for item in key_clauses:
        if isinstance(item, dict):
            clause_type = str(item.get("type") or "Other")
            explanation = _clean_clause_text(str(item.get("explanation") or "Generated from available model output."))[:320]
            candidates = _split_clause_candidates(str(item.get("clause") or ""), max_items=6)
            for candidate in candidates:
                normalized_key_clauses.append({
                    "type": _normalize_clause_type(clause_type, candidate),
                    "clause": candidate[:420],
                    "explanation": explanation,
                })
        elif isinstance(item, str):
            for candidate in _split_clause_candidates(item, max_items=4):
                normalized_key_clauses.append({
                    "type": _normalize_clause_type("Other", candidate),
                    "clause": candidate[:420],
                    "explanation": "Generated from available model output.",
                })
    key_clauses = [k for k in normalized_key_clauses if k.get("clause")]

    if not key_clauses:
        fallback_source = normalized_source if normalized_source else simplified
        inferred = _split_clause_candidates(fallback_source, max_items=6)
        if inferred:
            key_clauses = [{
                "type": _normalize_clause_type("Other", c),
                "clause": c[:420],
                "explanation": "Auto-generated from detected clause text."
            } for c in inferred]
        else:
            key_clauses = [{
                "type": "Other",
                "clause": simplified[:320],
                "explanation": "Generated from available model output."
            }]
    result["keyClauses"] = _prioritize_key_clauses(key_clauses, ANALYZE_MAX_KEY_CLAUSES)
    result["keyClauses"] = _ensure_key_clause_coverage(result["keyClauses"], normalized_source, ANALYZE_MAX_KEY_CLAUSES)
    if not result["keyClauses"]:
        result["keyClauses"] = [{
            "type": "Other",
            "clause": simplified[:320] if simplified else "Not available",
            "explanation": "Generated from available model output."
        }]

    risk_analysis = incoming.get("riskAnalysis") if isinstance(incoming.get("riskAnalysis"), list) else []
    if not risk_analysis:
        risk_analysis = [{
            "risk": "Detailed risk extraction was limited in the model response.",
            "mitigation": "Review the document manually or retry with a larger local model.",
            "severity": "Medium",
            "applicableLaw": "Not specified",
            "punishment": "Not specified"
        }]
    result["riskAnalysis"] = _normalize_risk_entries(risk_analysis)

    details = incoming.get("documentDetails") if isinstance(incoming.get("documentDetails"), dict) else {}
    result["documentDetails"] = {
        "documentType": _strip_markdown_noise(str(details.get("documentType") or _detect_document_type(normalized_source))),
        "partiesOrEntities": _normalize_parties_or_entities(details.get("partiesOrEntities"), normalized_source),
        "date": _strip_markdown_noise(str(details.get("date") or "Not specified")),
        "duration": _strip_markdown_noise(str(details.get("duration") or "Not applicable")),
        "jurisdiction": _strip_markdown_noise(str(details.get("jurisdiction") or "Not specified")),
        "purpose": _strip_markdown_noise(str(details.get("purpose") or (result["summary"][:220] if result["summary"] else "Not specified"))),
    }

    if not result["documentDetails"]["partiesOrEntities"]:
        result["documentDetails"]["partiesOrEntities"] = ["Not specified"]

    return result


def _merge_analysis_payload(aggregated: Dict[str, Any], partial: Dict[str, Any]) -> None:
    partial_simplified = (partial.get("simplifiedText") or "").strip()
    if partial_simplified:
        if aggregated["simplifiedText"]:
            aggregated["simplifiedText"] += "\n\n" + partial_simplified
        else:
            aggregated["simplifiedText"] = partial_simplified

    partial_summary = (partial.get("summary") or "").strip()
    if partial_summary:
        if aggregated["summary"]:
            aggregated["summary"] += "\n" + partial_summary
        else:
            aggregated["summary"] = partial_summary

    existing_clause_keys = {str(item.get("clause", "")).strip().lower() for item in aggregated["keyClauses"]}
    for item in partial.get("keyClauses", []):
        clause_key = str(item.get("clause", "")).strip().lower()
        if clause_key and clause_key not in existing_clause_keys:
            aggregated["keyClauses"].append(item)
            existing_clause_keys.add(clause_key)
            if len(aggregated["keyClauses"]) >= ANALYZE_MAX_KEY_CLAUSES:
                break

    existing_risk_keys = {str(item.get("risk", "")).strip().lower() for item in aggregated["riskAnalysis"]}
    for item in partial.get("riskAnalysis", []):
        risk_key = str(item.get("risk", "")).strip().lower()
        if risk_key and risk_key not in existing_risk_keys:
            aggregated["riskAnalysis"].append(item)
            existing_risk_keys.add(risk_key)
            if len(aggregated["riskAnalysis"]) >= ANALYZE_MAX_RISKS:
                break

    partial_details = partial.get("documentDetails", {}) or {}
    target_details = aggregated["documentDetails"]
    for field in ["documentType", "date", "duration", "jurisdiction", "purpose"]:
        incoming = str(partial_details.get(field, "")).strip()
        if incoming and _is_default_like(target_details.get(field, "")) and not _is_default_like(incoming):
            target_details[field] = incoming

    incoming_parties = partial_details.get("partiesOrEntities", []) or []
    existing_parties = {str(p).strip().lower() for p in target_details.get("partiesOrEntities", [])}
    for party in incoming_parties:
        party_text = str(party).strip()
        if not party_text:
            continue
        if party_text.lower() not in existing_parties:
            target_details["partiesOrEntities"].append(party_text)
            existing_parties.add(party_text.lower())


def _analyze_large_document(prompt: str, document_text: str) -> Dict[str, Any]:
    original_len = len(document_text)
    text_for_analysis = document_text[:ANALYZE_HARD_CHAR_LIMIT]
    chunks = _chunk_text_for_analysis(text_for_analysis, ANALYZE_CHUNK_CHAR_LIMIT, ANALYZE_CHUNK_OVERLAP)
    chunks = chunks[:ANALYZE_MAX_CHUNKS]

    aggregated = _default_analysis_payload()
    total = len(chunks)
    success_count = 0

    for idx, chunk in enumerate(chunks, start=1):
        chunk_prompt = (
            f"{prompt}\n"
            f"NOTE: This is chunk {idx} of {total} from a large document. "
            f"Analyze this chunk accurately; do not assume content outside this chunk. "
            f"Keep chunk output concise: max 4 key clauses and max 3 risks for this chunk.\n\n"
            f"Document:\n---\n{chunk}\n---"
        )
        try:
            partial = _coerce_analysis_payload(_run_structured_analysis(chunk_prompt), chunk)
            _merge_analysis_payload(aggregated, partial)
            success_count += 1
        except Exception as err:
            print(f"Chunk analysis failed for chunk {idx}/{total}: {err}")
            continue

    if success_count == 0:
        raise ValueError("Unable to analyze document chunks. Please try a smaller file or retry.")

    if not aggregated["simplifiedText"]:
        aggregated["simplifiedText"] = "Unable to generate simplified text from the provided document."
    elif len(aggregated["simplifiedText"]) > ANALYZE_MAX_SIMPLIFIED_CHARS:
        aggregated["simplifiedText"] = aggregated["simplifiedText"][:ANALYZE_MAX_SIMPLIFIED_CHARS].rstrip() + "..."

    if aggregated["summary"]:
        summary_lines = [line.strip() for line in aggregated["summary"].splitlines() if line.strip()]
        aggregated["summary"] = " ".join(summary_lines[:8])
    else:
        aggregated["summary"] = "Summary could not be generated for this document."

    if len(aggregated["keyClauses"]) > ANALYZE_MAX_KEY_CLAUSES:
        aggregated["keyClauses"] = aggregated["keyClauses"][:ANALYZE_MAX_KEY_CLAUSES]

    if len(aggregated["riskAnalysis"]) > ANALYZE_MAX_RISKS:
        aggregated["riskAnalysis"] = aggregated["riskAnalysis"][:ANALYZE_MAX_RISKS]

    coverage_notes: List[str] = []
    if original_len > ANALYZE_HARD_CHAR_LIMIT:
        coverage_notes.append(
            f"Only the first {ANALYZE_HARD_CHAR_LIMIT} characters were analyzed due to file size limits."
        )
    analyzed_chunks_estimate = len(chunks)
    if analyzed_chunks_estimate >= ANALYZE_MAX_CHUNKS:
        coverage_notes.append(
            f"Analysis considered up to {ANALYZE_MAX_CHUNKS} chunks to keep response time stable."
        )
    if success_count < total:
        coverage_notes.append(
            f"{total - success_count} chunk(s) could not be processed and were skipped."
        )
    if coverage_notes:
        aggregated["summary"] = aggregated["summary"].strip() + "\n\n" + " ".join(coverage_notes)

    if not aggregated["documentDetails"]["partiesOrEntities"]:
        aggregated["documentDetails"]["partiesOrEntities"] = ["Not specified"]

    return aggregated


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


def _gemini_embed_texts(texts: List[str]) -> Optional[List[List[float]]]:
    if not texts:
        return []

    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{EMBED_MODEL}:embedContent"
    vectors: List[List[float]] = []
    for text in texts:
        response = _gemini_http_request(endpoint, {
            "content": {"parts": [{"text": text}]}
        })

        values = None
        embedding = response.get("embedding")
        if isinstance(embedding, dict):
            values = embedding.get("values") or embedding.get("embedding")

        if values is None:
            items = response.get("embeddings") or []
            if items and isinstance(items[0], dict):
                values = items[0].get("values") or items[0].get("embedding")

        if values is None:
            return None
        vectors.append(values)

    return vectors


def _embed_texts(texts: List[str]) -> Optional[List[List[float]]]:
    if not texts:
        return []

    try:
        if AI_PROVIDER == "openai":
            response = openai_client.embeddings.create(model=EMBED_MODEL, input=texts)
            vectors: List[List[float]] = [item["embedding"] for item in response["data"]]
            return vectors

        if AI_PROVIDER == "ollama":
            vectors: List[List[float]] = []
            for text in texts:
                response = _ollama_http_request("/api/embeddings", {
                    "model": EMBED_MODEL,
                    "prompt": text,
                })
                embedding = response.get("embedding")
                if not embedding:
                    return None
                vectors.append(embedding)
            return vectors

        return _gemini_embed_texts(texts)
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

        prompt_base = """Analyze the following document from the perspective of an Indian legal expert. Your task is to simplify it, summarize it, extract key clauses, perform a detailed risk analysis, and extract its document details. Provide the output in a structured JSON format.

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
"""

        if len(document_text) <= ANALYZE_DIRECT_CHAR_LIMIT:
            contents = f"{prompt_base}\n\nDocument:\n---\n{document_text}\n---"
            result = _coerce_analysis_payload(_run_structured_analysis(contents), document_text)
        else:
            result = _analyze_large_document(prompt_base, document_text)

        if _looks_like_clause_fallback(result.get("keyClauses", [])):
            repaired_clauses = _retry_key_clause_extraction(document_text)
            if repaired_clauses:
                result["keyClauses"] = _ensure_key_clause_coverage(
                    repaired_clauses[:ANALYZE_MAX_KEY_CLAUSES],
                    document_text,
                    ANALYZE_MAX_KEY_CLAUSES,
                )

        result["simplifiedText"] = _ensure_simplified_text_quality(
            str(result.get("simplifiedText") or ""),
            document_text,
        )
        result["summary"] = _ensure_summary_quality(
            str(result.get("summary") or ""),
            document_text,
        )
        result["riskAnalysis"] = _ensure_risk_analysis_quality(
            result.get("riskAnalysis") if isinstance(result.get("riskAnalysis"), list) else [],
            document_text,
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in analyze_document: {str(e)}")
        if ENABLE_LOCAL_ANALYSIS_FALLBACK and _is_provider_failure(e):
            reason = _sanitize_provider_error(e)
            return _build_local_analysis(document_text, reason)
        raise HTTPException(status_code=500, detail=f"Failed to analyze document: {_sanitize_provider_error(e)}")


@app.post("/api/translate")
async def translate_text(request: TranslateRequest):
    """Translate text to a specified language"""
    try:
        source_text = _normalize_whitespace(request.text or "")
        if len(source_text) > TRANSLATE_MAX_CHARS:
            source_text = source_text[:TRANSLATE_MAX_CHARS]

        chunks = _chunk_text_for_translation(source_text, max(300, TRANSLATE_CHUNK_CHARS))
        translated_chunks: List[str] = []
        guidance = _translation_guidance(request.language)
        for chunk in chunks:
            prompt = f"""Translate the following English text into {request.language}. Preserve meaning and legal terms accurately.

Style guidance:
{guidance}

Return only translated text.

Text:
---
{chunk}
---
"""

            response = _generate_content_with_retry(
                primary_model=TRANSLATE_MODEL,
                fallback_models=TRANSLATE_FALLBACK_MODELS,
                contents=prompt
            )
            translated_chunks.append(_postprocess_translation(response.strip(), request.language))

        return {"translation": "\n\n".join([c for c in translated_chunks if c])}

    except Exception as e:
        print(f"Error in translate_text: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to translate text: {_sanitize_provider_error(e)}")


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

        response = _generate_content_with_retry(
            primary_model=CHAT_MODEL,
            fallback_models=CHAT_FALLBACK_MODELS,
            contents=prompt,
        )
        answer = response.strip()

        session["history"].append({"role": "user", "content": question})
        session["history"].append({"role": "assistant", "content": answer})

        return ChatResponse(response=answer)

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in send_chat_message: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to send message: {_sanitize_provider_error(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
