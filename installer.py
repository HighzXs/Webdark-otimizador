"""Instala o WebDark como aplicativo do Windows: copia o .exe para %LOCALAPPDATA%\\Programs\\WebDark, cria atalho no
menu Iniciar (aparece na pesquisa) e na Área de Trabalho, e registra em "Aplicativos instalados" para desinstalar.
Tudo por usuário (HKCU), sem precisar de administrador."""
import ctypes
import os
import shutil
import subprocess
import sys
import tempfile
import time
import winreg

from version import VERSION

NAME = "WebDark"
DISPLAY = "WebDark Otimizador"
INSTALL_DIR = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "Programs", NAME)
EXE = os.path.join(INSTALL_DIR, NAME + ".exe")
START_LNK = os.path.join(os.environ.get("APPDATA") or "", r"Microsoft\Windows\Start Menu\Programs", DISPLAY + ".lnk")
UNINST_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall" + "\\" + NAME

_YES = 6


def _ask(text):
    return ctypes.windll.user32.MessageBoxW(None, text, DISPLAY, 0x04 | 0x20 | 0x40000) == _YES   # sim/não, ?, por cima


def _tell(text, error=False):
    ctypes.windll.user32.MessageBoxW(None, text, DISPLAY, (0x10 if error else 0x40) | 0x40000)


def _desktop_lnk():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders") as k:
            desk = winreg.QueryValueEx(k, "Desktop")[0]
    except OSError:
        desk = os.path.join(os.path.expanduser("~"), "Desktop")
    return os.path.join(desk, DISPLAY + ".lnk")


def _ver(text):
    import re
    return tuple(int(n) for n in re.findall(r"\d+", text or "")[:4]) or (0,)


def is_frozen():
    return bool(getattr(sys, "frozen", False))


def is_installed_copy():
    return os.path.normcase(os.path.abspath(sys.executable)) == os.path.normcase(EXE)


def installed_version():
    """Versão registrada em "Aplicativos instalados", ou None se não está instalado."""
    if not os.path.exists(EXE):
        return None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, UNINST_KEY) as k:
            return winreg.QueryValueEx(k, "DisplayVersion")[0]
    except OSError:
        return "0"


def _shortcut(lnk, target):
    import backend
    q = lambda s: "'" + s.replace("'", "''") + "'"
    backend.ps(f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut({q(lnk)});$s.TargetPath={q(target)};"
               f"$s.WorkingDirectory={q(os.path.dirname(target))};$s.IconLocation={q(target + ',0')};"
               f"$s.Description={q(DISPLAY)};$s.Save()", timeout=30)


def register(desktop=False):
    """Atalho no menu Iniciar e registro de desinstalação (roda a cada abertura da cópia instalada: mantém a versão em dia)."""
    os.makedirs(os.path.dirname(START_LNK), exist_ok=True)
    _shortcut(START_LNK, EXE)
    if desktop:
        _shortcut(_desktop_lnk(), EXE)
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, UNINST_KEY) as k:
        for name, val in (("DisplayName", DISPLAY), ("DisplayVersion", VERSION), ("Publisher", "WebDark"),
                          ("DisplayIcon", EXE + ",0"), ("InstallLocation", INSTALL_DIR),
                          ("UninstallString", f'"{EXE}" --uninstall')):
            winreg.SetValueEx(k, name, 0, winreg.REG_SZ, val)
        for name, val in (("NoModify", 1), ("NoRepair", 1), ("EstimatedSize", os.path.getsize(EXE) // 1024)):
            winreg.SetValueEx(k, name, 0, winreg.REG_DWORD, val)


def install():
    """Copia este .exe para a pasta de instalação e cria os atalhos. -> True se deu certo."""
    os.makedirs(INSTALL_DIR, exist_ok=True)
    try:
        shutil.copyfile(sys.executable, EXE)   # copyfile (sem copiar permissões): o arquivo herda as da pasta
    except PermissionError:
        _tell("O WebDark instalado está aberto. Feche ele (inclusive pelo ícone perto do relógio) e tente de novo.", True)
        return False
    register(desktop=True)
    return True


def launch_installed():
    import backend
    subprocess.Popen([EXE], env=backend.fresh_start_env(), cwd=INSTALL_DIR, stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def offer(prefs):
    """Chamado ao abrir um .exe solto (ex.: Downloads). -> True se abriu a cópia instalada e este processo deve sair."""
    have = installed_version()
    if have is not None and _ver(have) >= _ver(VERSION):
        launch_installed()                     # já instalado (igual ou mais novo): abre o do menu Iniciar
        return True
    if have is None and prefs.get("install_asked"):
        return False
    text = (f"Atualizar o WebDark instalado ({have} → {VERSION})?" if have is not None else
            "Instalar o WebDark neste PC?\n\nEle vai aparecer na pesquisa do menu Iniciar e na Área de Trabalho, "
            "e você pode desinstalar em Configurações > Aplicativos.\n\nNão precisa de administrador.")
    if have is None:
        import settings
        prefs["install_asked"] = True
        settings.save(prefs)
    if not _ask(text) or not install():
        return False
    launch_installed()
    return True


def uninstall():
    """Chamado por "Aplicativos instalados" (UninstallString). Apaga atalhos, registro e a pasta do programa.
    As configurações em %APPDATA%\\FaxinaVarzea ficam (se reinstalar, volta como estava)."""
    import single
    if not single.acquire(0):
        _tell("Feche o WebDark antes de desinstalar (inclusive pelo ícone perto do relógio).", True)
        return
    if not _ask("Desinstalar o WebDark Otimizador?"):
        return
    for lnk in (START_LNK, _desktop_lnk()):
        try:
            os.remove(lnk)
        except OSError:
            pass
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, UNINST_KEY)
    except OSError:
        pass
    # a pasta só pode ser apagada depois que este processo fechar: um .bat espera e apaga
    folder = os.path.join(tempfile.gettempdir(), f"WebDark-uninstall-{os.getpid()}-{int(time.time())}")
    os.makedirs(folder, exist_ok=True)
    bat = os.path.join(folder, "desinstalar.bat")
    script = (
        "@echo off\r\n"
        "set n=0\r\n"
        ":retry\r\n"
        "set /a n+=1\r\n"
        "ping 127.0.0.1 -n 2 >nul\r\n"
        f'rmdir /s /q "{INSTALL_DIR}" >nul 2>&1\r\n'
        f'if exist "{INSTALL_DIR}" if %n% lss 30 goto retry\r\n'
        '(goto) 2>nul & del "%~f0"\r\n'
    )
    with open(bat, "w", encoding="cp850", errors="replace") as f:
        f.write(script)
    _tell("WebDark desinstalado.")
    subprocess.Popen(["cmd", "/c", bat], cwd=folder, creationflags=0x08000000, stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
