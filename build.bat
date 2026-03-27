@echo off
setlocal
echo =====================================
echo   Dictly - Windows Build
echo =====================================
echo.

echo [1/4] Installing build dependencies...
python -m pip install -r requirements-build.txt --quiet
if errorlevel 1 exit /b 1

echo [2/4] Cleaning old build output...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo [3/4] Building executable...
python -m PyInstaller dictly.spec --clean --noconfirm
if errorlevel 1 exit /b 1

echo [4/4] Creating release zip...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path 'dist\Dictly\*' -DestinationPath 'dist\Dictly-windows.zip' -Force"
if errorlevel 1 exit /b 1

echo.
echo Build complete.
echo   Folder: dist\Dictly
echo   Zip:    dist\Dictly-windows.zip
pause
