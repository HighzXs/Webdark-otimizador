@echo off
rem Gera dist\FaxinaVarzea.exe (precisa de: pip install customtkinter send2trash pillow pyinstaller)
python make_icon.py
python -m PyInstaller --noconfirm --onefile --windowed --name FaxinaVarzea --icon icon.ico ^
  --add-data "icon.ico;." --add-data "icon.png;." --collect-all customtkinter app.py
echo.
echo Pronto: dist\FaxinaVarzea.exe
pause
