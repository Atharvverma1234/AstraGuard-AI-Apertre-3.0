#!/bin/bash
# Vercel build script
# Installs dependencies and prepares the application

set -e

echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

echo "🏗️ Building Next.js frontend..."
cd frontend/astraguard-ai.site
npm install
npm run build
cd ../..

echo "✅ Build complete!"
