@echo off
echo Starting LegalEase AI Backend...
echo.

cd backend

echo Installing/updating dependencies...
py -m pip install -r requirements.txt
echo.

echo Starting FastAPI server...
py main.py
