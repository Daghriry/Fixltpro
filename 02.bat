@echo on
setlocal enabledelayedexpansion

echo ======================================================
echo    Fixltpro IT Support Ticketing System Launcher
echo ======================================================
echo.

:: Check if virtual environment exists
if not exist venv (
    echo ERROR: Virtual environment not found. Please run setup.bat first.
    pause
    exit /b 1
)

:: Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo ERROR: Failed to activate virtual environment.
    pause
    exit /b 1
)

:: Get local IP address for display purposes
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4 Address"') do (
    set IP=%%a
    set IP=!IP:~1!
    goto :got_ip
)

:got_ip
if not defined IP (
    set IP=127.0.0.1
)

echo.
echo Application will start at: http://%IP%:5000
echo To stop the application, press CTRL+C
echo.
echo Login information:
echo - Username: admin
echo - Password: admin123
echo.

:: Start the application in the background
start /B python app.py

:: Wait for the application to start
echo Waiting for the application to start...
timeout /t 3 > nul

:: Open the browser with the application URL
echo Opening browser to http://%IP%:5000
start http://%IP%:5000

echo.
echo Application is running in the background.
echo Press any key to stop the application...
pause > nul

:: Find and kill python processes
echo Stopping the application...
taskkill /F /IM python.exe /T
echo Application stopped.

endlocal