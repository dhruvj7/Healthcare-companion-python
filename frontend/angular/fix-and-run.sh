#!/bin/bash

# Frontend Fix and Run Script
# This script will fix all issues and start the Angular dev server

echo "🔧 Healthcare Companion - Frontend Fix & Run"
echo "============================================"
echo ""

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: package.json not found!"
    echo "Please run this script from the frontend/angular directory"
    exit 1
fi

echo "✅ In correct directory"
echo ""

# Step 1: Clean old installations
echo "📦 Step 1: Cleaning old installations..."
rm -rf node_modules package-lock.json
echo "✅ Cleaned"
echo ""

# Step 2: Install dependencies
echo "📦 Step 2: Installing dependencies..."
npm install
if [ $? -ne 0 ]; then
    echo "⚠️  Standard install failed, trying with --legacy-peer-deps..."
    npm install --legacy-peer-deps
fi
echo "✅ Dependencies installed"
echo ""

# Step 3: Verify critical files
echo "📁 Step 3: Verifying files..."

critical_files=(
    "src/app/app.module.ts"
    "src/app/components/chat/chat.component.ts"
    "src/app/services/chat.service.ts"
    "src/app/models/chat.models.ts"
    "src/app/pipes/safe-html.pipe.ts"
    "src/environments/environment.ts"
)

all_exist=true
for file in "${critical_files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file - MISSING!"
        all_exist=false
    fi
done

if [ "$all_exist" = false ]; then
    echo ""
    echo "❌ Some files are missing!"
    echo "Please check FIXES_APPLIED.md for details"
    exit 1
fi

echo "✅ All files present"
echo ""

# Step 4: Check backend
echo "🔍 Step 4: Checking backend..."
backend_status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null)

if [ "$backend_status" = "200" ]; then
    echo "✅ Backend is running (http://localhost:8000)"
else
    echo "⚠️  Backend not responding"
    echo "   Make sure backend is running with:"
    echo "   uvicorn app.main:app --reload"
fi
echo ""

# Step 5: Start the dev server
echo "🚀 Step 5: Starting Angular dev server..."
echo ""
echo "================================================"
echo "Frontend will be available at:"
echo "  http://localhost:4200"
echo ""
echo "Press Ctrl+C to stop the server"
echo "================================================"
echo ""

ng serve

# Alternative if ng is not found
if [ $? -ne 0 ]; then
    echo "⚠️  'ng' command not found, trying 'npm start'..."
    npm start
fi
