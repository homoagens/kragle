@echo off
cd /d "%~dp0"
set "PYTHONPATH=%~dp0src"
start "" /b cmd /c "timeout /t 2 /nobreak > nul && start http://localhost:7861"
venv\Scripts\python.exe -m app.run
