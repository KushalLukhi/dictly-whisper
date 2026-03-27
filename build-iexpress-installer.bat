@echo off
setlocal

set "APP_SOURCE="
if exist "%CD%\dist-fixed2\Dictly\Dictly.exe" set "APP_SOURCE=%CD%\dist-fixed2\Dictly"
if not defined APP_SOURCE if exist "%CD%\dist\Dictly\Dictly.exe" set "APP_SOURCE=%CD%\dist\Dictly"
if not defined APP_SOURCE if exist "%CD%\dist-fixed\Dictly\Dictly.exe" set "APP_SOURCE=%CD%\dist-fixed\Dictly"

if not defined APP_SOURCE (
  echo No packaged Dictly build was found.
  echo Build the app first, then rerun this script.
  exit /b 1
)

set "STAGE_DIR=%CD%\installer-dist\iexpress-stage"
set "OUT_DIR=%CD%\installer-dist"
set "OUT_EXE=%OUT_DIR%\Dictly-Setup.exe"
set "SED_FILE=%STAGE_DIR%\dictly-installer.sed"

if exist "%STAGE_DIR%" rmdir /s /q "%STAGE_DIR%"
if not exist "%OUT_DIR%" mkdir "%OUT_DIR%"
mkdir "%STAGE_DIR%\app"

robocopy "%APP_SOURCE%" "%STAGE_DIR%\app" /E /R:1 /W:1 /NFL /NDL /NJH /NJS /NC /NS >nul
set "ROBOCOPY_EXIT=%ERRORLEVEL%"
if %ROBOCOPY_EXIT% GEQ 8 exit /b %ROBOCOPY_EXIT%

copy /Y "%CD%\installer\install.cmd" "%STAGE_DIR%\install.cmd" >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%CD%\installer\write_iexpress_sed.ps1" -StageDir "%STAGE_DIR%" -OutExe "%OUT_EXE%" -SedFile "%SED_FILE%"
if errorlevel 1 exit /b 1

iexpress /N "%SED_FILE%"
if errorlevel 1 exit /b 1

echo.
echo IExpress installer build complete.
echo   Output: installer-dist\Dictly-Setup.exe
