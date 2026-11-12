@echo off
cd /d "%~dp0"
python configurator.py
if errorlevel 1 pause
