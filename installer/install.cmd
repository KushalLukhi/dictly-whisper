@echo off
setlocal

set "APP_NAME=Dictly"
set "APP_DIR=%LOCALAPPDATA%\Programs\Dictly"
set "START_MENU_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Dictly"
set "DESKTOP_LINK=%USERPROFILE%\Desktop\Dictly.lnk"

if not exist "%APP_DIR%" mkdir "%APP_DIR%"
robocopy "%~dp0app" "%APP_DIR%" /E /R:1 /W:1 /NFL /NDL /NJH /NJS /NC /NS >nul
set "ROBOCOPY_EXIT=%ERRORLEVEL%"
if %ROBOCOPY_EXIT% GEQ 8 exit /b %ROBOCOPY_EXIT%

if not exist "%START_MENU_DIR%" mkdir "%START_MENU_DIR%"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ws = New-Object -ComObject WScript.Shell; " ^
  "$s1 = $ws.CreateShortcut('%START_MENU_DIR%\Dictly.lnk'); " ^
  "$s1.TargetPath = '%APP_DIR%\Dictly.exe'; " ^
  "$s1.WorkingDirectory = '%APP_DIR%'; " ^
  "$s1.Save(); " ^
  "$s2 = $ws.CreateShortcut('%DESKTOP_LINK%'); " ^
  "$s2.TargetPath = '%APP_DIR%\Dictly.exe'; " ^
  "$s2.WorkingDirectory = '%APP_DIR%'; " ^
  "$s2.Save();"

start "" "%APP_DIR%\Dictly.exe"
exit /b 0
