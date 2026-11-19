#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -d backend/.venv ]]; then echo 'Missing Python environment. See README.md.';exit 1;fi
if [[ ! -d frontend/node_modules ]]; then echo 'Missing npm packages. Run cd frontend && npm install';exit 1;fi
source backend/.venv/bin/activate
backend_pid=''; frontend_pid=''
cleanup() { [[ -z "$backend_pid" ]] || kill "$backend_pid" 2>/dev/null || true; [[ -z "$frontend_pid" ]] || kill "$frontend_pid" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
( cd backend && exec python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 ) & backend_pid=$!
( cd frontend && exec npm run dev ) & frontend_pid=$!
echo 'KKD Studio AI: http://localhost:5173 | API: http://localhost:8000/docs'
wait "$backend_pid" "$frontend_pid"
