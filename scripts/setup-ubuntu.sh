#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if ! command -v ffmpeg >/dev/null; then echo 'Install ffmpeg: sudo apt install ffmpeg';exit 1;fi
if ! command -v npm >/dev/null; then echo 'Install Node.js 20+ and npm first';exit 1;fi
python3 -m venv backend/.venv
source backend/.venv/bin/activate
python -m pip install --upgrade pip
# CPU-first installation avoids pulling multi-GB CUDA runtime dependencies.
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r backend/requirements-ai.txt
( cd frontend && npm install )
echo 'Setup finished. Run ./start.sh and open http://localhost:5173'
