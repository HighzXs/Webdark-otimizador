"""WebDark Otimizador: janela com interface HTML (pywebview + WebView2).

Uso:  python webapp.py            abre normal
      python webapp.py second     abre na segunda tela (testes)
"""
import ctypes
import os
import sys
import threading

import webview

import installer
import single
from webapi import TITLE, Api


def resource(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def dark_titlebar():
    hwnd = ctypes.windll.user32.FindWindowW(None, TITLE)
    if hwnd:
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(ctypes.c_int(1)), 4)


def selftest(out_path):
    """Sem janela: confere que tudo foi empacotado e que as chamadas de leitura funcionam (para depurar o .exe)."""
    res = {}
    try:
        res["web"] = os.path.exists(resource(os.path.join("web", "index.html")))
        res["icon"] = os.path.exists(resource("icon.png"))
        api = Api()
        res["info"] = sorted(api.info())
        res["plans"] = len(api.power_info()["plans"])
        res["tweaks"] = len(api.tweaks_list())
        res["sec"] = sorted(api.sec_state())[:3]
        res["procs"] = len(api.proc_list()["rows"]) > 5
        import netopt
        res["dns"] = len(netopt.DNS_SERVERS)
        res["help"] = api.help_state()
        import updater
        res["updater"] = updater.check()
        import pystray, psutil  # noqa: F401
        res["ok"] = True
        api._shutdown()
    except Exception:
        import traceback
        res["erro"] = traceback.format_exc()
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(repr(res))


def relaunch_test(out_path, reset):
    """Abre o próprio .exe de novo e sai na hora (como o 'Reabrir como administrador' e a atualização fazem)."""
    import subprocess
    import backend
    env = backend.fresh_start_env() if reset else dict(os.environ)
    subprocess.Popen([sys.executable, "--selftest", out_path], env=env, stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=backend.CREATE_NO_WINDOW)


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--selftest":
        selftest(sys.argv[2])
        os._exit(0)
    if len(sys.argv) > 2 and sys.argv[1] == "--relaunch-test":
        relaunch_test(sys.argv[2], "--no-reset" not in sys.argv)
        os._exit(0)
    if "--uninstall" in sys.argv:
        installer.uninstall()
        os._exit(0)
    if installer.is_frozen() and not installer.is_installed_copy() and "--elevated" not in sys.argv:
        import settings
        if installer.offer(settings.load()):   # .exe solto: oferece instalar (menu Iniciar) e abre a cópia instalada
            os._exit(0)
    if not single.acquire(wait=12 if "--elevated" in sys.argv else 0):
        single.focus_existing(TITLE)
        return
    api = Api()
    second = "second" in sys.argv
    window = webview.create_window(TITLE, url=resource(os.path.join("web", "index.html")), js_api=api,
                                   width=1200, height=820, min_size=(980, 640), background_color="#05050a",
                                   x=1960 if second else None, y=30 if second else None)
    api.attach(window)

    def on_start():
        dark_titlebar()
        api.make_overlay()                     # janelinha da temperatura (fica escondida até precisar)
        if api._prefs.get("background"):
            api._tray_start()                  # modo segundo plano ligado: volta pra bandeja
        threading.Timer(8.0, api.update_check).start()
        if installer.is_frozen() and installer.is_installed_copy():
            threading.Thread(target=installer.register, daemon=True).start()   # atalho e versão em dia após atualizar

    webview.start(on_start, gui="edgechromium")
    api._shutdown()
    os._exit(0)


if __name__ == "__main__":
    main()
