@echo off
REM Run Sparky ingestion with system Python (bypassing venv)
echo Starting Sparky ingestion...
echo This will take 8-12 hours. You can close this window and it will continue.
echo Progress is saved automatically - you can resume anytime.
echo.
C:\Python313\python.exe ingest_sparky_export.py ..\chat-history
pause

