@echo off
REM Mobile GCS Setup Script
REM Generates PWA icons and verifies setup

echo ================================
echo Mobile GCS Setup
echo ================================
echo.

cd /d "%~dp0.."

REM Check if Pillow is installed
python -c "import PIL" 2>nul
if errorlevel 1 (
    echo [STEP 1] Installing Pillow for icon generation...
    python -m pip install Pillow
    if errorlevel 1 (
        echo [ERROR] Failed to install Pillow
        echo.
        echo Alternative: Use online icon generator:
        echo   https://www.pwabuilder.com/imageGenerator
        pause
        exit /b 1
    )
)

echo [STEP 2] Generating PWA icons...
python tools\generate_pwa_icons.py
if errorlevel 1 (
    echo [WARNING] Icon generation failed. Using placeholder icons.
    echo You can generate icons manually using online tools.
)

echo.
echo [STEP 3] Verifying files...
if exist "monitoring\static\manifest.json" (
    echo   [OK] manifest.json exists
) else (
    echo   [ERROR] manifest.json not found!
)

if exist "monitoring\static\icon-192.png" (
    echo   [OK] icon-192.png exists
) else (
    echo   [WARNING] icon-192.png not found - PWA will work but icon may be missing
)

if exist "monitoring\static\icon-512.png" (
    echo   [OK] icon-512.png exists
) else (
    echo   [WARNING] icon-512.png not found - PWA will work but icon may be missing
)

echo.
echo ================================
echo Setup Complete!
echo ================================
echo.
echo Next steps:
echo 1. Start dashboard: python monitoring\dashboard.py
echo 2. Open http://localhost:8000 in mobile browser
echo 3. Add to Home Screen (Android/iOS)
echo.
pause
