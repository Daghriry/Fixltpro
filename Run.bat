@echo off
echo ======================================================
echo    Fixltpro IT Support Ticketing System Launcher
echo ======================================================
echo.

REM Check if virtual environment exists
if not exist venv\ (
    echo [!] Virtual environment not found. Please run setup.bat first.
    pause
    exit /b 1
)

REM Activate virtual environment
echo [+] Activating virtual environment...
call venv\Scripts\activate.bat

REM Get local IP address
echo [+] Detecting local network IP address...
for /f "tokens=4 delims= " %%i in ('route print ^| find " 0.0.0.0"') do (
    set LOCAL_IP=%%i
    goto :found_ip
)

:found_ip
echo [+] Local IP address: %LOCAL_IP%

REM Check if database exists
if not exist fixltpro.db (
    echo [!] Warning: Database file not found.
    echo     You may need to initialize the database at http://%LOCAL_IP%:5000/setup
    echo     after the application starts.
    echo.
    set /p CONTINUE="Continue anyway? (Y/N): "
    if /i not "%CONTINUE%"=="Y" (
        echo [+] Operation cancelled. Please run setup.bat to initialize the database.
        pause
        exit /b 1
    )
)

REM Start Flask application in background
echo [+] Starting Fixltpro application...
start /B cmd /c "python app.py --host=%LOCAL_IP% > app_log.txt 2>&1"

REM Wait for application to start
echo [+] Waiting for application to initialize...
timeout /t 3 /nobreak > nul

REM Open browser with local IP address
echo [+] Opening application in browser...
start http://%LOCAL_IP%:5000

echo.
echo =============================================================
echo [i] Application running at http://%LOCAL_IP%:5000
echo.
echo [i] Default login credentials:
echo     Username: admin
echo     Password: admin123
echo.
echo [i] To stop the application, close this window or press Ctrl+C
echo =============================================================
echo.

REM Keep the window open
echo [i] Press Ctrl+C to stop the server...
cmd /k