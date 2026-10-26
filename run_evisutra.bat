@echo off
title EviSutra - Digital Evidence Forensics Platform
echo =====================================================================
echo           EVISUTRA FORENSICS PLATFORM - STARTUP LAUNCHER             
echo       Bihar Cyber Hackathon 2026 - Problem Statement PS-05           
echo =====================================================================
echo.
echo [1/2] Starting FastAPI Backend on http://localhost:8000...
start "EviSutra Backend (FastAPI)" cmd /k "python -m uvicorn backend.app.main:app --port 8000 --reload"

echo [2/2] Starting Frontend Vite Server on http://localhost:5173...
start "EviSutra Frontend (Vite)" cmd /k "npm run dev"

echo.
echo =====================================================================
echo Both servers are launching in separate windows!
echo - Web Dashboard:      http://localhost:5173
echo - API Docs (Swagger): http://localhost:8000/docs
echo =====================================================================
echo Opening browser in 3 seconds...
timeout /t 3 >nul
start http://localhost:5173
