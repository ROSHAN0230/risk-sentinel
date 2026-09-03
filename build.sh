#!/usr/bin/env bash
# exit on error
set -o errexit

echo "=== Risk Sentinel: Starting Render Build Process ==="

# Upgrade pip and install backend Python dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# If Node and npm are available, rebuild the React 18 frontend
if command -v npm &> /dev/null
then
    echo "=== Building React 18 + TypeScript Frontend ==="
    cd frontend
    npm install
    npm run build
    cd ..
else
    echo "=== Node/npm not detected; using pre-compiled frontend in frontend/dist/ ==="
fi

echo "=== Render Build Process Completed Successfully ==="
