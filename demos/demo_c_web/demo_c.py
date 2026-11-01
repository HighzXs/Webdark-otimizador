"""Demo C: interface em HTML/CSS/JS dentro de uma janela do Windows (pywebview + WebView2).

O Python só abre a janela e responde ao que o JavaScript pedir (aqui: ligar/desligar o acrílico do Windows 11).
"""
import ctypes
import os
import sys
import threading
import time

import webview

TITLE = "Demo C — HTML"
HERE = os.path.dirname(os.path.abspath(__file__))


def backdrop(on):
    hwnd = ctypes.windll.user32.FindWindowW(None, TITLE)
    if not hwnd:
        return
    dwm = ctypes.windll.dwmapi
    dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(ctypes.c_int(1)), 4)                 # barra de título escura
    dwm.DwmSetWindowAttribute(hwnd, 38, ctypes.byref(ctypes.c_int(2 if on else 1)), 4)   # 2 = Mica, 1 = nenhum


class Api:
    def set_blur(self, on):
        backdrop(bool(on))


def capture(window, prefix):
    from PIL import ImageGrab
    time.sleep(2.5)
    u = ctypes.windll.user32
    hwnd = u.FindWindowW(None, TITLE)
    u.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002)      # HWND_TOPMOST só pra tirar o print

    class R(ctypes.Structure):
        _fields_ = [("l", ctypes.c_long), ("t", ctypes.c_long), ("r", ctypes.c_long), ("b", ctypes.c_long)]
    steps = [("", 0), ("window.__demo.go(1)", 1.2), ("window.__demo.scrollList(2400)", 1.0), ("window.__demo.go(2)", 1.2),
             ("window.__demo.go(0); window.__demo.fake()", 2.6)]
    for i, (js, wait) in enumerate(steps):
        if js:
            window.evaluate_js(js)
        time.sleep(wait)
        r = R()
        u.GetWindowRect(hwnd, ctypes.byref(r))
        ImageGrab.grab(bbox=(r.l, r.t, r.r, r.b), all_screens=True).save(f"{prefix}_{i}.png")
    window.destroy()


if __name__ == "__main__":
    second = len(sys.argv) > 1 and sys.argv[1] == "second"
    x, y = (1960, 30) if second else None, None
    w = webview.create_window(TITLE, url=os.path.join(HERE, "index.html"), js_api=Api(), width=1180, height=800,
                              min_size=(900, 600), background_color="#05050a", x=1960 if second else None,
                              y=30 if second else None)
    if len(sys.argv) > 2:
        webview.start(capture, (w, sys.argv[2]), gui="edgechromium")
    else:
        webview.start(lambda: backdrop(False), gui="edgechromium")
