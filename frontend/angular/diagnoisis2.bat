@echo off
echo.
echo ======================================
echo Healthcare Companion - Diagnostics
echo ======================================
echo.

echo Checking Node.js...
node --version
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Node.js not found!
    pause
    exit /b 1
)
echo.

echo Checking npm...
npm --version
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: npm not found!
    pause
    exit /b 1
)
echo.

echo AFTER NPM CHECK
pause
