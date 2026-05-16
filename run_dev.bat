@echo off
echo Starting ProdSeller Bot [DEV - auto reload]...
echo Admin panel: http://127.0.0.1:8000/admin
echo.
set RUN_MAIN=true
venv\Scripts\uvicorn.exe main:app --host 127.0.0.1 --port 8000 --reload
