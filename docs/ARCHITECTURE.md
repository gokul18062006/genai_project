# Architecture

## Overview
LegalEase AI has a frontend-backend architecture:
- Frontend: React + TypeScript + Vite
- Backend: FastAPI + Google Gemini integration

Frontend sends document and chat requests to backend. Backend performs AI operations and returns structured JSON.

## High-Level Flow
1. User uploads a PDF/TXT or pastes text in the frontend.
2. Frontend sends request to backend API.
3. Backend calls Gemini model and requests structured response.
4. Backend returns analysis payload to frontend.
5. Frontend renders tabs (risk, details, summary, clauses, translation).
6. Frontend can create and continue a document-grounded chat session.

## Core Modules
- frontend/App.tsx: app orchestration and page state
- frontend/components/*: UI for upload, analysis, and chat
- backend/main.py: API routes and Gemini integration
- backend/services/apiService.ts: frontend API client for backend calls
- types.ts: shared frontend TypeScript contracts

## API Endpoints
- GET /: health endpoint
- POST /api/analyze: structured legal analysis
- POST /api/translate: language translation
- POST /api/chat/create: create chat session with document context
- POST /api/chat/message: continue existing chat session

## Data Contracts
Primary response object from /api/analyze includes:
- simplifiedText
- summary
- keyClauses[]
- riskAnalysis[]
- documentDetails

## Security Notes
- Gemini API key is backend-only via environment variable.
- Do not expose secrets in frontend code or git history.
- Rotate keys immediately if exposed.
