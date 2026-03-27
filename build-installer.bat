@echo off
setlocal

set "APP_VERSION=0.1.0"
set "APP_SOURCE="

if exist "dist-fixed2\Dictly\Dictly.exe" set "APP_SOURCE=%CD%\dist-fixed2\Dictly"
if not defined APP_SOURCE if exist "dist\Dictly\Dictly.exe" set "APP_SOURCE=%CD%\dist\Dictly"
if not defined APP_SOURCE if exist "dist-fixed\Dictly\Dictly.exe" set "APP_SOURCE=%CD%\dist-fixed\Dictly"

if not defined APP_SOURCE (
  echo No packaged Dictly build was found.
  echo Build the app first, then rerun this script.
  exit /b 1
)

set "ISCC_EXE="
if exist "%CD%\tools\Inno Setup 6\ISCC.exe" set "ISCC_EXE=%CD%\tools\Inno Setup 6\ISCC.exe"
if not defined ISCC_EXE if exist "%CD%\tools\innosetup\ISCC.exe" set "ISCC_EXE=%CD%\tools\innosetup\ISCC.exe"
if not defined ISCC_EXE if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC_EXE=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC_EXE if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC_EXE=%ProgramFiles%\Inno Setup 6\ISCC.exe"

echo =====================================
echo   Dictly - Windows Installer Build
echo =====================================
echo.
echo Source: %APP_SOURCE%
echo.

if defined ISCC_EXE (
  "%ISCC_EXE%" /DAppSource="%APP_SOURCE%" /DAppVersion="%APP_VERSION%" "dictly-installer.iss"
  if errorlevel 1 exit /b 1
  echo.
  echo Installer build complete.
  echo   Output: installer-dist\Dictly-Setup.exe
  exit /b 0
)

call "%CD%\build-iexpress-installer.bat"
