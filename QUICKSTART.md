# Quick Start Guide - LegalEase AI

## First Time Setup

### 1. Configure API Key

1. Get your Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create/Edit `backend/.env` and add:
   ```
   GEMINI_API_KEY=your-api-key-here
   ```

### 2. Install Dependencies

#### Backend (Python)
```powershell
cd backend
py -m pip install -r requirements.txt
```

#### Frontend (Node.js)
```powershell
npm install
```

## Running the Application

### Option 1: Using Quick Start Scripts (Windows)

1. **Start Backend** - Double-click `start-backend.bat` or run:
   ```powershell
   .\start-backend.bat
   ```

2. **Start Frontend** - In a new terminal, double-click `start-frontend.bat` or run:
   ```powershell
   .\start-frontend.bat
   ```

### Option 2: Manual Start

1. **Start Backend**:
   ```powershell
   cd backend
   py main.py
   ```
   Backend will run on: http://localhost:8000

2. **Start Frontend** (in a new terminal):
   ```powershell
   npm run dev
   ```
   Frontend will run on: http://localhost:5173

## Accessing the Application

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## Troubleshooting

### Backend Issues

**Error: "GEMINI_API_KEY not set"**
- Make sure `backend/.env` exists with your API key

**Error: "Module not found"**
```powershell
cd backend
venv\Scripts\activate
py -m ```

### Frontend Issues

**Error: "Cannot connect to backend"**
- Make sure backend is running on port 8000
- Check `frontend/.env.local` has: `VITE_API_BASE_URL=http://localhost:8000`

**Error: Dependencies missing**
```powershell
npm install
```

### Port Already in Use

**Backend (port 8000)**
```powershell
# Find and kill process using port 8000
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

**Frontend (port 5173)**
```powershell
# Find and kill process using port 5173
netstat -ano | findstr :5173
taskkill /PID <PID> /F
```

## Development Tips

- Keep both terminal windows open while developing
- Backend auto-reloads on code changes
- Frontend hot-reloads automatically
- Check backend logs in the backend terminal
- Check frontend logs in browser console (F12)
