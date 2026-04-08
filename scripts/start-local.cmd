@echo off
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "REPO_ROOT=%%~fI"

set "BACKEND_HOST=127.0.0.1"
set "BACKEND_PORT=8000"
set "FRONTEND_HOST=127.0.0.1"
set "FRONTEND_PORT=3000"

echo.
echo === Tender Navigator local start ===
echo Repo: %REPO_ROOT%
echo.

where npm.cmd >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Node.js ^(with npm^) not found in PATH.
  echo Install Node.js 20+ and try again.
  exit /b 1
)

call :ensure_python
if errorlevel 1 exit /b 1

call :ensure_backend_dependencies
if errorlevel 1 exit /b 1

call :ensure_frontend_dependencies
if errorlevel 1 exit /b 1

set "DB_PATH=%REPO_ROOT:\=/%/backend/data/tender_navigator_backend.db"
set "API_PROXY_TARGET=http://%BACKEND_HOST%:%BACKEND_PORT%"

echo.
echo Starting backend window...
start "Tender Navigator Backend" cmd /k "cd /d ""%REPO_ROOT%"" && set ""TENDER_NAVIGATOR_DATABASE_URL=sqlite:///%DB_PATH%"" && set ""TENDER_NAVIGATOR_CELERY_EAGER=true"" && ""%PYTHON_EXE%"" -m uvicorn backend.app.main:app --reload --host %BACKEND_HOST% --port %BACKEND_PORT%"

echo Starting frontend window...
start "Tender Navigator Frontend" cmd /k "cd /d ""%REPO_ROOT%\frontend"" && set ""NEXT_PUBLIC_API_BASE_URL=/api/v1"" && set ""TENDER_NAVIGATOR_API_PROXY_TARGET=%API_PROXY_TARGET%"" && npm.cmd run dev -- --hostname %FRONTEND_HOST% --port %FRONTEND_PORT%"

echo.
echo Waiting a few seconds before opening the browser...
timeout /t 6 /nobreak >nul
start "" "http://%FRONTEND_HOST%:%FRONTEND_PORT%/login"

echo.
echo Backend:  http://%BACKEND_HOST%:%BACKEND_PORT%/docs
echo Frontend: http://%FRONTEND_HOST%:%FRONTEND_PORT%/login
echo.
echo If something fails, keep both opened terminal windows and copy their last lines.
exit /b 0

:ensure_python
if exist "%REPO_ROOT%\.venv\Scripts\python.exe" (
  set "PYTHON_EXE=%REPO_ROOT%\.venv\Scripts\python.exe"
  exit /b 0
)

echo Creating Python virtual environment in .venv ...

where py >nul 2>nul
if not errorlevel 1 (
  py -3 -m venv "%REPO_ROOT%\.venv"
) else (
  where python >nul 2>nul
  if errorlevel 1 (
    echo [ERROR] Python not found in PATH.
    echo Install Python 3.11+ and try again.
    exit /b 1
  )
  python -m venv "%REPO_ROOT%\.venv"
)

if not exist "%REPO_ROOT%\.venv\Scripts\python.exe" (
  echo [ERROR] Failed to create Python virtual environment.
  exit /b 1
)

set "PYTHON_EXE=%REPO_ROOT%\.venv\Scripts\python.exe"
exit /b 0

:ensure_backend_dependencies
if exist "%REPO_ROOT%\.venv\Scripts\uvicorn.exe" (
  echo Backend dependencies already available.
  exit /b 0
)

echo Installing backend dependencies...
"%PYTHON_EXE%" -m pip install --upgrade pip
if errorlevel 1 (
  echo [ERROR] Failed to upgrade pip.
  exit /b 1
)

"%PYTHON_EXE%" -m pip install -r "%REPO_ROOT%\backend\requirements.txt"
if errorlevel 1 (
  echo [ERROR] Failed to install backend dependencies.
  exit /b 1
)

exit /b 0

:ensure_frontend_dependencies
if exist "%REPO_ROOT%\frontend\node_modules\next" (
  echo Frontend dependencies already available.
  exit /b 0
)

echo Installing frontend dependencies...
pushd "%REPO_ROOT%\frontend"
call npm.cmd install
set "NPM_EXIT=%ERRORLEVEL%"
popd

if not "%NPM_EXIT%"=="0" (
  echo [ERROR] Failed to install frontend dependencies.
  exit /b 1
)

exit /b 0
