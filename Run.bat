@echo off
setlocal enabledelayedexpansion

echo ==========================================================================
echo    Fixltpro IT Support Ticketing System - All-in-One Launcher
echo ==========================================================================
echo.

REM Check command line arguments
set SETUP_MODE=0
set FORCE_SETUP=0
set REPAIR_MODE=0

if "%1"=="--setup" (
    set SETUP_MODE=1
)
if "%1"=="--force-setup" (
    set SETUP_MODE=1
    set FORCE_SETUP=1
)
if "%1"=="--repair" (
    set REPAIR_MODE=1
)

REM Check if virtual environment exists
if not exist venv\ (
    echo [!] Virtual environment not found.
    echo     Starting setup process automatically...
    echo.
    set SETUP_MODE=1
) else (
    if %SETUP_MODE%==0 (
        echo [+] Virtual environment found.
    )
)

REM Perform setup if needed
if %SETUP_MODE%==1 (
    call :SETUP_ENVIRONMENT
    if !ERRORLEVEL! NEQ 0 (
        pause
        exit /b 1
    )
)

REM Perform dependency repair if requested
if %REPAIR_MODE%==1 (
    call :REPAIR_DEPENDENCIES
    if !ERRORLEVEL! NEQ 0 (
        pause
        exit /b 1
    )
    exit /b 0
)

REM Check if setup has been skipped
if %SETUP_MODE%==0 (
    REM Verify dependencies before starting the application
    call :VERIFY_DEPENDENCIES
    if !ERRORLEVEL! NEQ 0 (
        echo [!] Dependency verification failed.
        set /p REPAIR="Would you like to repair dependencies now? (Y/N): "
        if /i "!REPAIR!"=="Y" (
            call :REPAIR_DEPENDENCIES
            if !ERRORLEVEL! NEQ 0 (
                pause
                exit /b 1
            )
        ) else (
            echo [!] Application may not function correctly without required dependencies.
            pause
            exit /b 1
        )
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
    echo [+] Local IP address: !LOCAL_IP!

    REM Check if database exists
    if not exist fixltpro.db (
        echo [i] Database file not found.
        echo     You may need to initialize the database when the application starts.
        echo     Navigate to: http://!LOCAL_IP!:5000/setup in your browser.
        echo.
    )

    REM Start Flask application with the local IP address
    echo [+] Starting Fixltpro application...
    start /B cmd /c "python app.py --host=!LOCAL_IP! > app_log.txt 2>&1"

    REM Wait for application to start
    echo [+] Waiting for application to initialize...
    timeout /t 3 /nobreak > nul

    REM Open browser with local IP address
    echo [+] Opening application in browser...
    start http://!LOCAL_IP!:5000

    echo.
    echo =============================================================
    echo [i] Application running at: http://!LOCAL_IP!:5000
    echo.
    echo [i] Default login credentials:
    echo     Username: admin
    echo     Password: admin123
    echo.
    echo [i] To stop the application, close this window or press Ctrl+C
    echo =============================================================
    echo.

    REM Keep the window open
    echo [i] Application is running... Press Ctrl+C to stop the server
    cmd /k
)

exit /b 0

REM ===========================
REM SETUP ENVIRONMENT FUNCTION
REM ===========================
:SETUP_ENVIRONMENT
echo ======================================================
echo    Fixltpro IT Support Ticketing System Setup
echo ======================================================
echo.

REM Check if Python is installed
python --version > NUL 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [!] Python not found. Please install Python 3.7 or newer.
    echo     Download from: https://www.python.org/downloads/
    exit /b 1
)

echo [+] Python found...

REM Check if force setup or venv doesn't exist
if %FORCE_SETUP%==1 (
    echo [!] Forcing new setup as requested...
    if exist venv\ (
        echo [!] Removing existing virtual environment...
        rmdir /s /q venv
    )
)

REM Create virtual environment if it doesn't exist
if not exist venv\ (
    echo [+] Creating virtual environment...
    python -m venv venv
    if %ERRORLEVEL% NEQ 0 (
        echo [!] Error creating virtual environment.
        exit /b 1
    )
)

REM Activate virtual environment
echo [+] Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip to latest version
echo [+] Upgrading package manager pip...
python -m pip install --upgrade pip

REM Create requirements.txt file with all required dependencies
echo [+] Creating required libraries list...
(
echo Flask==2.3.3
echo Flask-SQLAlchemy==3.1.1
echo Flask-WTF==1.2.1
echo Flask-Login==0.6.3
echo Flask-Babel==4.0.0
echo Flask-Mail==0.9.1
echo Werkzeug==2.3.7
echo WTForms==3.1.1
echo email_validator==2.1.0.post1
echo python-dotenv==1.0.0
echo gunicorn==21.2.0
echo Jinja2==3.1.2
echo click==8.1.7
echo itsdangerous==2.1.2
echo MarkupSafe==2.1.3
echo SQLAlchemy==2.0.23
echo psycopg2-binary==2.9.9
echo PyJWT==2.8.0
echo Babel==2.13.1
echo blinker==1.7.0
) > requirements.txt

REM Install required libraries
echo [+] Installing required libraries...
echo [i] This may take a few minutes...
pip install -r requirements.txt

if %ERRORLEVEL% NEQ 0 (
    echo [!] Error installing libraries.
    echo [!] Attempting to install core dependencies individually...
    
    pip install Flask==2.3.3
    pip install Flask-SQLAlchemy==3.1.1
    pip install Flask-WTF==1.2.1
    pip install Flask-Login==0.6.3
    pip install Flask-Babel==4.0.0
    pip install Flask-Mail==0.9.1
    pip install Werkzeug==2.3.7
    pip install python-dotenv==1.0.0
    
    if %ERRORLEVEL% NEQ 0 (
        echo [!] Error installing core dependencies.
        exit /b 1
    ) else {
        echo [+] Core dependencies installed successfully.
    }
)

REM Create .env file if it doesn't exist
if not exist .env (
    echo [+] Creating environment settings file...
    (
    echo SECRET_KEY=fixltpro_secret_key_2025
    echo FLASK_APP=app.py
    echo FLASK_ENV=development
    ) > .env
)

echo.
echo ============================================================
echo [+] Fixltpro IT Support Ticketing System environment setup completed
echo.

REM Ask if user wants to initialize the database now
set /p INIT_DB="Do you want to initialize the database now? (Y/N): "
if /i "%INIT_DB%"=="Y" (
    echo.
    echo [+] Starting application to initialize database...
    echo [+] Please wait...
    
    REM Get local IP address for database setup
    for /f "tokens=4 delims= " %%i in ('route print ^| find " 0.0.0.0"') do (
        set LOCAL_IP=%%i
        goto :found_ip_setup
    )
    
    :found_ip_setup
    start /B cmd /c "python app.py --host=!LOCAL_IP! > nul 2>&1"
    timeout /t 3 /nobreak > nul
    start http://!LOCAL_IP!:5000/setup
    echo [+] Browser opened to database setup page.
    echo [+] After database setup is complete, press any key to continue.
    pause > nul
    
    REM Kill the temporary server
    for /f "tokens=5" %%p in ('netstat -aon ^| find ":5000" ^| find "LISTENING"') do (
        taskkill /F /PID %%p > nul 2>&1
    )
    
    echo [+] Setup server stopped. System is now ready to run.
    echo [+] Press any key to launch the application...
    pause > nul
    
    REM Return to main script to start the app properly
    exit /b 0
) else (
    echo.
    echo [+] Database initialization skipped.
    echo [+] Press any key to launch the application...
    pause > nul
    exit /b 0
)

REM =========================
REM REPAIR DEPENDENCIES FUNCTION
REM =========================
:REPAIR_DEPENDENCIES
echo ======================================================
echo    Repairing Fixltpro Dependencies
echo ======================================================
echo.

REM Activate virtual environment
echo [+] Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip to latest version
echo [+] Upgrading package manager pip...
python -m pip install --upgrade pip

REM Uninstall problematic packages to ensure clean reinstall
echo [+] Removing any problematic packages...
pip uninstall -y flask_wtf
pip uninstall -y flask_sqlalchemy
pip uninstall -y flask_login

REM Install all required dependencies
echo [+] Reinstalling all required dependencies...
pip install -r requirements.txt --force-reinstall

if %ERRORLEVEL% NEQ 0 (
    echo [!] Failed to reinstall dependencies.
    echo [+] Attempting to install critical packages individually...
    
    pip install Flask==2.3.3
    pip install Flask-SQLAlchemy==3.1.1
    pip install Flask-WTF==1.2.1
    pip install Flask-Login==0.6.3
    pip install Werkzeug==2.3.7
    
    if %ERRORLEVEL% NEQ 0 (
        echo [!] Critical package installation failed.
        exit /b 1
    )
)

echo [+] Verifying installations...
python -c "import flask_wtf" 2>NUL
if %ERRORLEVEL% NEQ 0 (
    echo [!] Flask-WTF verification failed.
    exit /b 1
)

python -c "import flask_sqlalchemy" 2>NUL
if %ERRORLEVEL% NEQ 0 (
    echo [!] Flask-SQLAlchemy verification failed.
    exit /b 1
)

echo [+] Dependencies successfully repaired.
exit /b 0

REM ==========================
REM VERIFY DEPENDENCIES FUNCTION
REM ==========================
:VERIFY_DEPENDENCIES
echo [+] Verifying installed dependencies...

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Verify critical dependencies
python -c "import flask_wtf" 2>NUL
if %ERRORLEVEL% NEQ 0 (
    echo [!] Flask-WTF not properly installed.
    exit /b 1
)

python -c "import flask_sqlalchemy" 2>NUL
if %ERRORLEVEL% NEQ 0 (
    echo [!] Flask-SQLAlchemy not properly installed.
    exit /b 1
)

python -c "import flask_login" 2>NUL
if %ERRORLEVEL% NEQ 0 (
    echo [!] Flask-Login not properly installed.
    exit /b 1
)

echo [+] All dependencies verified successfully.
exit /b 0