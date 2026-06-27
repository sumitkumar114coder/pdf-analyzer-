@echo off
echo Starting AI Research Assistant backend server...
start /b .venv\Scripts\python -m uvicorn backend.main:app --port 8000
timeout /t 2 >nul
echo Opening application in Brave Browser...
start "" "C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe" "http://localhost:8000"
exit
