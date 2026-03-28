@echo off
setlocal
echo =====================================
echo   Dictly - Download Local Models
echo =====================================
echo.

python download_models.py --insecure %*
if errorlevel 1 exit /b 1

echo.
echo Local models downloaded to .\models
pause
