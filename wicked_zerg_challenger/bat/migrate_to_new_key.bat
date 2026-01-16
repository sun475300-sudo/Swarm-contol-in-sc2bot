@echo off
chcp 65001 >nul
echo ========================================
echo ?꾨줈?앺듃 ?꾩껜瑜????ㅻ줈 援먯껜
echo Migrate Entire Project to New API Key
echo ========================================
echo.

cd /d "%~dp0\.."

set NEW_KEY=YOUR_API_KEY_HERE

echo ???? %NEW_KEY%
echo.

pause

powershell -ExecutionPolicy Bypass -File "%~dp0..\tools\migrate_to_new_key.ps1" -NewApiKey "%NEW_KEY%"

pause
