@echo off
rem Sets up this projects Python environment and installs its packages.
cd /d "%~dp0"
echo Creating the .venv environment...
python -m venv .venv
if errorlevel 1 goto failed
echo Installing packages (this takes a minute or two)...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo.
echo Done. In VS Code, open the notebook and choose the .venv kernel.
pause
exit /b 0
:failed
echo.
echo Something went wrong. Copy the message above and send it to Claude.
pause
exit /b 1
