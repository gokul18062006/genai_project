# LegalEase AI

LegalEase AI is a full-stack legal document assistant that analyzes legal text and PDFs, simplifies legal language, extracts key clauses, generates risk analysis, and supports follow-up chat grounded in the uploaded document.

## Overview

LegalEase AI provides:
- Legal document analysis for `.pdf` and `.txt` files
- Plain-language simplification
- Executive summary generation
- Key clause extraction with explanations
- Risk and mitigation analysis with legal context
- Document details extraction (type, parties, date, term, jurisdiction, purpose)
- Translation of simplified output into Indian languages
- Document-grounded legal Q&A chat

## Tech Stack

- Frontend: React 19, TypeScript, Vite
- Backend: FastAPI, Uvicorn, Pydantic
- AI providers supported:
  - Ollama (local)
  - Gemini
  - OpenAI
- PDF extraction: pypdf
- Optional scanned-PDF support: pypdfium2 + Pillow (VLM flow)

## Project Structure

```text
legalease-ai/
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   ├── README.md
│   └── services/
│       └── apiService.ts
├── frontend/
│   ├── App.tsx
│   ├── index.tsx
│   ├── constants.ts
│   └── components/
├── docs/
├── package.json
├── vite.config.ts
├── render.yaml
└── README.md
```

## Current Local Defaults

Current local config is tuned for Ollama-first usage:
- Backend URL: `http://127.0.0.1:8001`
- Frontend URL: `http://localhost:5173`
- Frontend API default: `http://localhost:8001`
- Analysis model: `llama3.1:8b`
- Translation model: `llama3.1:8b`
- VLM model: `llava:13b`
- Embedding model: `nomic-embed-text`

## Prerequisites

- Node.js 18+
- Python 3.11+
- npm
- (Recommended) Python virtual environment
- Ollama installed and running locally for local AI mode

## Setup

### 1. Install frontend dependencies

```powershell
npm install
```

### 2. Install backend dependencies

```powershell
cd backend
py -m pip install -r requirements.txt
```

### 3. Configure environment

Create or update `backend/.env`.

Example for local Ollama mode:

```dotenv
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434

OLLAMA_TEXT_MODEL=llama3.1:8b
OLLAMA_ANALYSIS_MODEL=llama3.1:8b
OLLAMA_CHAT_MODEL=llama3.1:8b
OLLAMA_TRANSLATE_MODEL=llama3.1:8b
OLLAMA_VLM_MODEL=llava:13b
OLLAMA_EMBED_MODEL=nomic-embed-text

OLLAMA_TIMEOUT_SECONDS=300
TRANSLATE_MAX_CHARS=3500
TRANSLATE_CHUNK_CHARS=1200

VLM_ENABLED=true
VLM_PDF_STRATEGY=fallback
OLLAMA_MAX_VLM_PAGES=2

ANALYZE_PERF_PROFILE=balanced
ENABLE_LOCAL_ANALYSIS_FALLBACK=true
ANALYSIS_FALLBACK_MODELS=llama3.1:8b,gemma3:1b
TRANSLATE_FALLBACK_MODELS=llama3.1:8b

SIMPLIFY_REWRITE_ENABLED=true
SUMMARY_REWRITE_ENABLED=true
RISK_REWRITE_ENABLED=true
```

Optional frontend env file (`.env.local` in project root):

```dotenv
VITE_API_BASE_URL=http://localhost:8001
```

## Run Locally

Open two terminals.

### Terminal 1: Backend

```powershell
py -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8001
```

### Terminal 2: Frontend

```powershell
npm run dev
```

Open:
- Frontend: `http://localhost:5173`
- Backend health: `http://127.0.0.1:8001/`
- Backend docs: `http://127.0.0.1:8001/docs`

## Ollama Models

Pull the models used by the project:

```powershell
ollama pull llama3.1:8b
ollama pull gemma3:1b
ollama pull llava:13b
ollama pull nomic-embed-text
```

## API Endpoints

- `GET /`
  - Health and runtime status

- `POST /api/analyze`
  - Input: document text or uploaded file payload
  - Output:
    - `simplifiedText`
    - `summary`
    - `keyClauses[]`
    - `riskAnalysis[]`
    - `documentDetails`

- `POST /api/translate`
  - Input: `{ text, language }`
  - Output: `{ translation }`

- `POST /api/chat/create`
  - Creates document-grounded chat session

- `POST /api/chat/message`
  - Sends message in existing chat session

## Output Quality Pipeline

The backend includes quality enforcement layers:
- Simplified text quality check and rewrite fallback
- Executive summary quality check and rewrite fallback
- Risk analysis quality check, rewrite fallback, enrichment, dedupe, prioritization
- Key clause fallback detection and extraction retry

## Build

```powershell
npm run build
npm run preview
```

## Deployment Notes

`render.yaml` is included for deploying backend and frontend services.

Important for deployment:
- Set `VITE_API_BASE_URL` to backend URL
- Set backend provider env vars based on chosen provider
- Configure `CORS_ORIGINS` for your frontend domain

## Troubleshooting

### Frontend shows `ERR_CONNECTION_REFUSED`
- Ensure frontend dev server is running on `localhost:5173`
- Ensure backend is running on `127.0.0.1:8001`

### Analyze error: invalid format specifier
- Caused by broken f-string JSON braces in backend prompt (already fixed in current code)
- Restart backend after pulling latest changes

### Translation timeout
- Translation now uses dedicated model + chunking
- Increase `OLLAMA_TIMEOUT_SECONDS` if needed
- Ensure translation model exists locally in Ollama

### Generic fallback results
- Increase model quality (`OLLAMA_ANALYSIS_MODEL`)
- Keep rewrite flags enabled
- Use `ANALYZE_PERF_PROFILE=balanced` for better accuracy

## Security

- Do not commit secrets in `.env`
- Keep API keys server-side only
- Rotate exposed keys immediately

## License

MIT

Primary provider: ollama
Analysis: llama3.1:8b
Chat: llama3.1:8b
Translation: llama3.1:8b
VLM (PDF image/scanned support): llava:13b
Embeddings: nomic-embed-text
Analysis fallback: gemma3:1b (after llama3.1:8b)