@echo off
cd /d %~dp0
python demo_b_qt.py
if errorlevel 1 pause
