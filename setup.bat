@echo off
echo ======================================================
echo    Fixltpro IT Support Ticketing System Setup
echo ======================================================
echo.

REM Check if Python is installed
python --version > NUL 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [!] Python not found. Please install Python 3.7 or newer.
    echo     Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [+] Python found...

REM Create virtual environment
echo [+] Creating virtual environment...
python -m venv venv
if %ERRORLEVEL% NEQ 0 (
    echo [!] Error creating virtual environment.
    pause
    exit /b 1
)

REM Activate virtual environment
echo [+] Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip to latest version
echo [+] Upgrading package manager pip...
python -m pip install --upgrade pip

REM Create requirements.txt file
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
) > requirements.txt

REM Install required libraries
echo [+] Installing required libraries...
pip install -r requirements.txt

if %ERRORLEVEL% NEQ 0 (
    echo [!] Error installing libraries.
    pause
    exit /b 1
)

REM Create .env file
echo [+] Creating environment settings file...
(
echo SECRET_KEY=fixltpro_secret_key_2025
echo FLASK_APP=app.py
echo FLASK_ENV=development
) > .env

echo.
echo ============================================================
echo [+] Fixltpro IT Support Ticketing System environment setup completed
echo.
echo    Next steps:
echo.
echo    1. To initialize the database (first time only):
echo       Run the application and navigate to: /setup
echo.
echo    2. To run the application:
echo       Execute run.bat
echo.
echo    3. Default login credentials:
echo       Username: admin
echo       Password: admin123
echo ============================================================
echo.

REM Ask if user wants to initialize the database now
set /p INIT_DB="Do you want to initialize the database now? (Y/N): "
if /i "%INIT_DB%"=="Y" (
    echo.
    echo [+] Starting application to initialize database...
    echo [+] Please wait...
    start /B cmd /c "python app.py > nul 2>&1"
    timeout /t 3 /nobreak > nul
    start http://localhost:5000/setup
    echo [+] Browser opened to database setup page.
    echo [+] You can close this window after database setup is complete.
    echo [+] Then use run.bat to start the application normally.
)

pause