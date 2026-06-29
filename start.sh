#!/bin/bash
cd "$(dirname "$0")"
export PYTHONPATH="$(pwd)/src"
(sleep 2 && xdg-open http://localhost:7861 2>/dev/null || open http://localhost:7861 2>/dev/null) &
./venv/bin/python -m app.run
