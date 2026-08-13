@echo off
setlocal

if not exist .venv (
    echo .venv not found. Creating environment...
    call scripts\setup_venv.bat
)

call .venv\Scripts\activate.bat
set DRY_RUN=true
python main.py
