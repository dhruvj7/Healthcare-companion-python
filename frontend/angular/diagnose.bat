@echo off
echo.
echo ======================================
echo Healthcare Companion - Diagnostics
echo ======================================
echo.

echo Checking Node.js...
node --version
if errorlevel 1 (
    echo ERROR: Node.js not found!
    echo Please install Node.js from https://nodejs.org
    pause
    exit /b 1
)
echo.

@REM echo Checking npm...
@REM npm --version
@REM if errorlevel 1 (
@REM     echo ERROR: npm not found!
@REM     pause
@REM     exit /b 1
@REM )
@REM echo.

@REM echo Checking Angular CLI...
@REM call ng version
@REM if errorlevel 1 (
@REM     echo WARNING: Angular CLI not found globally
@REM     echo Installing Angular CLI globally...
@REM     npm install -g @angular/cli
@REM )
@REM echo.

echo Checking project files...
echo.

if exist "package.json" (echo [OK] package.json) else (echo [MISSING] package.json & set ERROR=1)
if exist "angular.json" (echo [OK] angular.json) else (echo [MISSING] angular.json & set ERROR=1)
if exist "tsconfig.json" (echo [OK] tsconfig.json) else (echo [MISSING] tsconfig.json & set ERROR=1)
if exist "src\app\app.module.ts" (echo [OK] app.module.ts) else (echo [MISSING] app.module.ts & set ERROR=1)
if exist "src\app\components\chat\chat.component.ts" (echo [OK] chat.component.ts) else (echo [MISSING] chat.component.ts & set ERROR=1)
if exist "src\app\services\chat.service.ts" (echo [OK] chat.service.ts) else (echo [MISSING] chat.service.ts & set ERROR=1)
if exist "src\app\models\chat.models.ts" (echo [OK] chat.models.ts) else (echo [MISSING] chat.models.ts & set ERROR=1)
if exist "src\app\pipes\safe-html.pipe.ts" (echo [OK] safe-html.pipe.ts) else (echo [MISSING] safe-html.pipe.ts & set ERROR=1)
if exist "src\environments\environment.ts" (echo [OK] environment.ts) else (echo [MISSING] environment.ts & set ERROR=1)

if defined ERROR (
    echo.
    echo ERROR: Some critical files are missing!
    echo Please ensure all files are in place.
    pause
    exit /b 1
)

echo.
echo All files present!
echo.

echo Checking node_modules...
if exist "node_modules" (
    echo [OK] node_modules exists
) else (
    echo [MISSING] node_modules folder
    echo Running npm install...
    call npm install
)
echo.

echo ======================================
echo Diagnostics Complete!
echo ======================================
echo.
echo If you see errors above, please fix them first.
echo Otherwise, run: ng serve
echo.
pause
