@echo off
chcp 65001 > nul
REM AI Arena 배포 준비 배치 스크립트

echo ======================================================================
echo AI Arena Deployment Preparation
echo ======================================================================
echo.

REM CRITICAL: Change to project directory
cd /d "%~dp0\.."
set PYTHONPATH=%CD%

echo [INFO] Working directory: %CD%
echo [INFO] Deploy path: D:\arena_deployment
echo.

REM 환경 변수 설정
set ARENA_DEPLOY_PATH=D:\arena_deployment

echo [STEP 1] Validating project files...
python tools/arena_deployment_prep.py --skip-validation

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Validation failed. Fixing errors...
    python tools/arena_deployment_prep.py
    
    if %ERRORLEVEL% NEQ 0 (
        echo.
        echo [ERROR] Deployment preparation failed
        echo.
        echo [Troubleshooting]
        echo   1. Check syntax errors: python -m py_compile run.py
        echo   2. Check missing files in project root
        echo   3. Review error messages above
        echo.
        pause
        exit /b 1
    )
)

echo.
echo [STEP 2] Creating deployment package...
python tools/arena_deployment_prep.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Package creation failed
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo Deployment preparation complete!
echo ======================================================================
echo.
echo Package location: D:\arena_deployment
echo.
echo Next steps:
echo   1. Review the package in: D:\arena_deployment\temp_package
echo   2. Upload ZIP file to AI Arena: D:\arena_deployment\WickedZerg_AIArena_*.zip
echo   3. Test the package locally before uploading
echo.
pause
