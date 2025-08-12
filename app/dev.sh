#!/bin/bash

# Development script for hot reload functionality
echo "🚀 Starting Klyne development environment..."
echo "📦 This will start both Tailwind CSS watching and the FastAPI server"
echo ""

# Check if npm dependencies are installed
if [ ! -d "node_modules" ]; then
    echo "📋 Installing npm dependencies..."
    npm install
fi

# Start Tailwind CSS watcher and FastAPI server concurrently
echo "🎨 Starting Tailwind CSS watcher..."
echo "🖥️  Starting FastAPI server..."
echo ""
echo "💡 Hot reload is now active:"
echo "   - CSS changes will rebuild automatically"
echo "   - Python changes will restart the server"
echo "   - Visit http://localhost:8000 to see your app"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

npm run dev:server