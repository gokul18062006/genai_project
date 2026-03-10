@echo off
echo Starting LegalEase AI Frontend...
echo.

echo Installing/updating dependencies...
call npm install
echo.

echo Starting Vite development server...
call npm run dev
