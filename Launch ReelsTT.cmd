@echo off
cd /d "%~dp0"
if exist "%~dp0ReelsTT.exe" (
    start "" "%~dp0ReelsTT.exe" %*
) else (
    start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0main.py" %*
)
