@echo off

REM Change directory to where main.py is located
cd /d "C:\Users\admin\Documents\dbbackup"

REM Activate the virtual environment (Create one in dir if not already)
call venv\Scripts\activate.bat

REM Run the Python script
python main.py

REM Deactivate the venv
deactivate
