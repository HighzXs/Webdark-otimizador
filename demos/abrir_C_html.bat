@echo off
cd /d %~dp0demo_c_web
python demo_c.py
if errorlevel 1 pause
