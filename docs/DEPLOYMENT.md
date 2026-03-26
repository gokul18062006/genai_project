# Deployment Guide

## Render Deployment (Recommended)

### Services
Create two services:
- Web Service: backend (FastAPI)
- Static Site: frontend (Vite build output)

### Backend Service Settings
- Root Directory: backend
- Build Command: pip install -r requirements.txt
- Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT

Environment variables:
- GEMINI_API_KEY=your_real_key
- CORS_ORIGINS=https://your-frontend-url.onrender.com

### Frontend Static Site Settings
- Root Directory: .
- Build Command: npm install && npm run build
- Publish Directory: dist

Environment variables:
- VITE_API_BASE_URL=https://your-backend-url.onrender.com

## Verification Checklist
- Backend health: GET / returns running status
- Frontend loads without blank page
- Document analyze endpoint works
- Chat create and message endpoints work
- Translation endpoint works

## Common Issues
1. Backend build fails with dependency conflict:
- Re-check backend/requirements.txt pinned versions.

2. Frontend cannot call backend:
- Ensure VITE_API_BASE_URL is correct.
- Ensure backend CORS_ORIGINS includes frontend URL.

3. Static site build passes but publish fails:
- Ensure Root Directory and Publish Directory pair is correct.
- For repo-root build output, Publish Directory must be dist.
