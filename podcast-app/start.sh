#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$SCRIPT_DIR/backend"

echo "=== 每日新聞播報 ==="
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
  echo "ERROR: Python 3 is required. Please install Python 3.8+."
  exit 1
fi

cd "$BACKEND"

# Create .env if missing
if [ ! -f "$SCRIPT_DIR/.env" ]; then
  cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
  echo "Created .env from .env.example — edit it to customise research topics."
fi

# Virtual environment
if [ ! -d "$BACKEND/.venv" ]; then
  echo "Creating virtual environment…"
  python3 -m venv .venv
fi

source .venv/bin/activate
echo "Installing dependencies…"
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo ""
echo "Starting server at http://localhost:8000"
echo "Press Ctrl+C to stop."
echo ""

# Copy .env to backend dir so python-dotenv finds it
cp "$SCRIPT_DIR/.env" "$BACKEND/.env" 2>/dev/null || true

python main.py
