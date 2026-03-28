@echo off
setlocal

echo =====================================
echo   Dictly - Offline Windows Installer
echo =====================================
echo.

if not exist "models" (
  echo No models folder was found.
  echo Download at least one model first, for example:
  echo   .\download-models.bat
  exit /b 1
)

dir /b /ad "models" >nul 2>nul
if errorlevel 1 (
  echo The models folder is empty.
  echo Download at least one model first, for example:
  echo   .\download-models.bat
  exit /b 1
)

echo Found local bundled models under:
for /d %%D in (models\*) do echo   %%~nxD
echo.

call "%CD%\build.bat"
if errorlevel 1 exit /b 1

call "%CD%\build-installer.bat"
if errorlevel 1 exit /b 1

echo.
echo Offline installer build complete.
echo The generated installer includes bundled models from the models folder.
echo Users should not need to download those bundled models on first run.

