@echo off
rem Gera dist\webdark\WebDark.exe (precisa de: pip install pywebview pystray psutil send2trash pillow pyinstaller)
cd /d %~dp0
python -m PyInstaller --noconfirm --onefile --windowed --name WebDark --icon icon.ico ^
  --add-data "web;web" --add-data "icon.png;." --add-data "icon.ico;." ^
  --collect-all webview --collect-all pythonnet --collect-all clr_loader --distpath dist\webdark webapp.py
echo.
echo Pronto: dist\webdark\WebDark.exe
pause
