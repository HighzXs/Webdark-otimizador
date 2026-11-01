@echo off
cd /d %~dp0
python demo_a_ctk.py
if errorlevel 1 pause
