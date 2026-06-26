@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo.
echo ========================================
echo   Kragle - LLM configuration
echo ========================================
echo.
echo This will write a .env file for Kragle.
echo Point it at any OpenAI-compatible endpoint
echo (Ollama, LM Studio, vLLM, llama.cpp, OpenAI, Groq, OpenRouter...).
echo.

set "DEFAULT_URL=http://localhost:11434/v1"
set "DEFAULT_MODEL=llama3.2"

set /p BASE_URL=Base URL [%DEFAULT_URL%]:
if "!BASE_URL!"=="" set "BASE_URL=%DEFAULT_URL%"

set /p MODEL=Model name [%DEFAULT_MODEL%]:
if "!MODEL!"=="" set "MODEL=%DEFAULT_MODEL%"

set /p API_KEY=API key (press Enter for none):

set /p WEB_PORT=Web UI port [7861]:
if "!WEB_PORT!"=="" set "WEB_PORT=7861"

if exist .env (
    copy /Y .env .env.backup >nul
    echo.
    echo Existing .env backed up to .env.backup
)

(
    echo LLM_PROVIDER=openai
    echo LLM_BASE_URL=!BASE_URL!
    echo LLM_API_KEY=!API_KEY!
    echo DEFAULT_MODEL=!MODEL!
    echo.
    echo WEB_HOST=0.0.0.0
    echo WEB_PORT=!WEB_PORT!
) > .env

echo.
echo Configuration saved to .env:
echo   provider:  openai-compatible
echo   base URL:  !BASE_URL!
echo   model:     !MODEL!
echo   port:      !WEB_PORT!
echo.
echo Run start.bat to launch Kragle.
echo.
endlocal
