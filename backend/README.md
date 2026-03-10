# FastAPI Backend for LegalEase AI

This is the Python FastAPI backend that provides API endpoints for document analysis, translation, and chat functionality using Google's Gemini AI.

## Setup Instructions

### 1. Install Python Dependencies

Make sure you have Python 3.8+ installed, then install the required packages:

**Windows:**
```powershell
cd backend
py -m pip install -r requirements.txt
```

**macOS/Linux:**
```bash
cd backend
pip install -r requirements.txt
```

Or using a virtual environment (optional):

**Windows:**
```powershell
cd backend
py -m venv venv
venv\Scripts\activate
py -m pip install -r requirements.txt
```

**macOS/Linux:**
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Set Up Environment Variables

Create a `.env` file in the `backend` directory:

```bash
cp .env.example .env
```

Then edit `.env` and add your Gemini API key:

```
GEMINI_API_KEY=your_actual_gemini_api_key_here
```

You can get a Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey).

### 3. Run the Backend Server

Start the FastAPI server:

**Windows:**
```powershell
# From the backend directory
py main.py
```

**macOS/Linux:**
```bash
python main.py
```

Or using uvicorn directly:

**Windows:**
```powershell
py -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**macOS/Linux:**
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### 4. API Documentation

Once the server is running, you can access:
- Interactive API docs: `http://localhost:8000/docs`
- Alternative API docs: `http://localhost:8000/redoc`

## API Endpoints

- `POST /api/analyze` - Analyze a legal document
- `POST /api/translate` - Translate text to another language
- `POST /api/chat/create` - Create a new chat session
- `POST /api/chat/message` - Send a message in a chat session

## Frontend Configuration

Make sure your frontend is configured to connect to this backend. Create or update `frontend/.env.local`:

```
VITE_API_BASE_URL=http://localhost:8000
```

## Production Deployment

For production deployment:

1. Set `GEMINI_API_KEY` as an environment variable
2. Use a production ASGI server like Gunicorn with Uvicorn workers
3. Configure CORS origins in `main.py` to match your frontend domain
4. Use HTTPS for secure communication
