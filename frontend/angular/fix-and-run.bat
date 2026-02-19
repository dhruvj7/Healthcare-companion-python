@echo off
REM Frontend Fix and Run Script for Windows
REM This script will fix all issues and start the Angular dev server

echo.
echo 🔧 Healthcare Companion - Frontend Fix ^& Run
echo ============================================
echo.

REM Check if we're in the right directory
if not exist "package.json" (
    echo ❌ Error: package.json not found!
    echo Please run this script from the frontend\angular directory
    pause
    exit /b 1
)

echo ✅ In correct directory
echo.

REM Step 1: Clean old installations
echo 📦 Step 1: Cleaning old installations...
if exist "node_modules" rmdir /s /q node_modules
if exist "package-lock.json" del /f /q package-lock.json
echo ✅ Cleaned
echo.

REM Step 2: Install dependencies
echo 📦 Step 2: Installing dependencies...
call npm install
if errorlevel 1 (
    echo ⚠️  Standard install failed, trying with --legacy-peer-deps...
    call npm install --legacy-peer-deps
)
echo ✅ Dependencies installed
echo.

REM Step 3: Verify critical files
echo 📁 Step 3: Verifying files...
set "all_exist=true"

if exist "src\app\app.module.ts" (echo   ✅ src\app\app.module.ts) else (echo   ❌ src\app\app.module.ts - MISSING! & set "all_exist=false")
if exist "src\app\components\chat\chat.component.ts" (echo   ✅ src\app\components\chat\chat.component.ts) else (echo   ❌ src\app\components\chat\chat.component.ts - MISSING! & set "all_exist=false")
if exist "src\app\services\chat.service.ts" (echo   ✅ src\app\services\chat.service.ts) else (echo   ❌ src\app\services\chat.service.ts - MISSING! & set "all_exist=false")
if exist "src\app\models\chat.models.ts" (echo   ✅ src\app\models\chat.models.ts) else (echo   ❌ src\app\models\chat.models.ts - MISSING! & set "all_exist=false")
if exist "src\app\pipes\safe-html.pipe.ts" (echo   ✅ src\app\pipes\safe-html.pipe.ts) else (echo   ❌ src\app\pipes\safe-html.pipe.ts - MISSING! & set "all_exist=false")
if exist "src\environments\environment.ts" (echo   ✅ src\environments\environment.ts) else (echo   ❌ src\environments\environment.ts - MISSING! & set "all_exist=false")

if "%all_exist%"=="false" (
    echo.
    echo ❌ Some files are missing!
    echo Please check FIXES_APPLIED.md for details
    pause
    exit /b 1
)

echo ✅ All files present
echo.

REM Step 4: Check backend
echo 🔍 Step 4: Checking backend...
curl -s -o nul -w "%%{http_code}" http://localhost:8000/health > nul 2>&1
if errorlevel 1 (
    echo ⚠️  Backend not responding
    echo    Make sure backend is running with:
    echo    uvicorn app.main:app --reload
) else (
    echo ✅ Backend is running (http://localhost:8000^)
)
echo.

REM Step 5: Start the dev server
echo 🚀 Step 5: Starting Angular dev server...
echo.
echo ================================================
echo Frontend will be available at:
echo   http://localhost:4200
echo.
echo Press Ctrl+C to stop the server
echo ================================================
echo.

call ng serve

REM Alternative if ng is not found
if errorlevel 1 (
    echo ⚠️  'ng' command not found, trying 'npm start'...
    call npm start
)

pause
