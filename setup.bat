@echo on
setlocal enabledelayedexpansion

echo ======================================================
echo    Fixltpro IT Support Ticketing System Setup
echo ======================================================
echo.

:: Check if Python is installed
echo Checking Python installation...
python --version
if %errorlevel% neq 0 (
    echo ERROR: Python not found. Please install Python 3.8 or newer.
    pause
    exit /b 1
)

:: Create virtual environment
echo Creating virtual environment (venv)...
if exist venv (
    echo Virtual environment already exists.
) else (
    python -m venv venv
    if %errorlevel% neq 0 (
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo Virtual environment created successfully.
)

:: Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate
if %errorlevel% neq 0 (
    echo ERROR: Failed to activate virtual environment.
    pause
    exit /b 1
)

:: Install each required package individually to ensure success
echo Installing core packages...

echo Installing Flask...
pip install Flask==2.3.3
if %errorlevel% neq 0 echo WARNING: Flask installation may have issues

echo Installing Flask-SQLAlchemy...
pip install Flask-SQLAlchemy==3.1.1
if %errorlevel% neq 0 echo WARNING: Flask-SQLAlchemy installation may have issues

echo Installing Flask-WTF...
pip install Flask-WTF==1.2.1
if %errorlevel% neq 0 echo WARNING: Flask-WTF installation may have issues

echo Installing Werkzeug...
pip install Werkzeug==2.3.7
if %errorlevel% neq 0 echo WARNING: Werkzeug installation may have issues

echo Installing FPDF...
pip install fpdf==1.7.2
if %errorlevel% neq 0 echo WARNING: FPDF installation may have issues

echo Installing arabic-reshaper...
pip install arabic-reshaper==3.0.0
if %errorlevel% neq 0 echo WARNING: arabic-reshaper installation may have issues

echo Installing python-bidi...
pip install python-bidi==0.4.2
if %errorlevel% neq 0 echo WARNING: python-bidi installation may have issues

echo Installing openpyxl...
pip install openpyxl==3.1.2
if %errorlevel% neq 0 echo WARNING: openpyxl installation may have issues

:: Install remaining packages from requirements.txt
echo Installing remaining packages from requirements.txt...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo WARNING: Some packages in requirements.txt may not have installed correctly.
) else (
    echo Successfully installed all packages from requirements.txt
)

:: Create necessary directories
echo Creating necessary directories...
if not exist static\fonts (
    mkdir static\fonts
    echo Created fonts directory.
)

if not exist static\images (
    mkdir static\images
    echo Created images directory.
)

if not exist uploads (
    mkdir uploads
    echo Created uploads directory.
)

:: Check for font files
echo Checking font files...
if not exist static\fonts\arial.ttf (
    echo WARNING: Font file arial.ttf not found in static\fonts
    echo Please copy the required font files (arial.ttf and arialbd.ttf) for proper PDF generation.
)

if not exist static\fonts\arialbd.ttf (
    echo WARNING: Font file arialbd.ttf not found in static\fonts
    echo Please copy the required font files (arial.ttf and arialbd.ttf) for proper PDF generation.
)

:: Verify key installations
echo.
echo Verifying installations...
python -c "try: import flask; print(f'Flask version: {flask.__version__}'); except Exception as e: print(f'Flask error: {e}')"
python -c "try: import flask_sqlalchemy; print(f'Flask-SQLAlchemy OK'); except Exception as e: print(f'Flask-SQLAlchemy error: {e}')"
python -c "try: import fpdf; print(f'FPDF OK'); except Exception as e: print(f'FPDF error: {e}')"
python -c "try: import arabic_reshaper; print(f'arabic-reshaper OK'); except Exception as e: print(f'arabic-reshaper error: {e}')"
python -c "try: import bidi; print(f'python-bidi OK'); except Exception as e: print(f'python-bidi error: {e}')"
python -c "try: import openpyxl; print(f'openpyxl OK'); except Exception as e: print(f'openpyxl error: {e}')"

:: Set up the database
echo.
echo Setting up database...
python -c "from app import app, setup_api; app.app_context().push(); setup_api()"

:: Check if database file exists
if not exist fixltpro.db (
    echo WARNING: Database file not created. There might be an issue with database setup.
) else (
    echo Database setup completed successfully.
)

echo.
echo =================================================
echo    Application environment setup completed!
echo =================================================
echo.
echo Login information:
echo - Username: admin
echo - Password: admin123
echo.
echo Now starting the application...
echo.

:: Run the application
python app.py

endlocal