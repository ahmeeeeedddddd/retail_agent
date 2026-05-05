@echo off
echo Starting RetailMind Agent Backend...
cd backend
start cmd /k "..\venv\Scripts\activate && uvicorn main_api:app --host 0.0.0.0 --port 8000"

echo Waiting for backend to start...
timeout /t 5 /nobreak >nul

echo Starting RetailMind Dashboard...
cd ../frontend
start index.html
echo Startup complete! Ensure your browser allows local file access, or run it via a local static server if needed.
pause
