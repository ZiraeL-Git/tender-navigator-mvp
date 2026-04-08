@echo off
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "REPO_ROOT=%%~fI"

echo.
echo === Reset Tender Navigator local data ===
echo This will remove local SQLite data used by the app.
echo.

if exist "%REPO_ROOT%\backend\data\tender_navigator_backend.db" (
  del /f /q "%REPO_ROOT%\backend\data\tender_navigator_backend.db"
  if errorlevel 1 (
    echo [ERROR] Could not delete backend\data\tender_navigator_backend.db
    echo Make sure backend is stopped, then run this script again.
    exit /b 1
  )
)

if exist "%REPO_ROOT%\backend\data\tender_inputs" (
  rmdir /s /q "%REPO_ROOT%\backend\data\tender_inputs"
)

mkdir "%REPO_ROOT%\backend\data\tender_inputs" >nul 2>nul

echo Local data reset completed.
echo You can start the project again with start-local.cmd
exit /b 0
