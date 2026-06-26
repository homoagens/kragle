#!/bin/bash
cd "$(dirname "$0")"

echo ""
echo "========================================"
echo "  Kragle - LLM configuration"
echo "========================================"
echo ""
echo "This will write a .env file for Kragle."
echo "Point it at any OpenAI-compatible endpoint"
echo "(Ollama, LM Studio, vLLM, llama.cpp, OpenAI, Groq, OpenRouter...)."
echo ""

read -p "Base URL [http://localhost:11434/v1]: " BASE_URL
BASE_URL=${BASE_URL:-http://localhost:11434/v1}

read -p "Model name [llama3.2]: " MODEL
MODEL=${MODEL:-llama3.2}

read -p "API key (press Enter for none): " API_KEY

read -p "Web UI port [7861]: " WEB_PORT
WEB_PORT=${WEB_PORT:-7861}

if [ -f .env ]; then
    cp .env .env.backup
    echo ""
    echo "Existing .env backed up to .env.backup"
fi

cat > .env <<EOF
LLM_PROVIDER=openai
LLM_BASE_URL=${BASE_URL}
LLM_API_KEY=${API_KEY}
DEFAULT_MODEL=${MODEL}

WEB_HOST=0.0.0.0
WEB_PORT=${WEB_PORT}
EOF

echo ""
echo "Configuration saved to .env:"
echo "  provider:  openai-compatible"
echo "  base URL:  ${BASE_URL}"
echo "  model:     ${MODEL}"
echo "  port:      ${WEB_PORT}"
echo ""
echo "Run ./start.sh to launch Kragle."
echo ""
