"""Garante que só exista uma janela do programa aberta."""
import ctypes
import time

_k32 = ctypes.WinDLL("kernel32", use_last_error=True)
_k32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
_k32.CreateMutexW.restype = ctypes.c_void_p
_k32.CloseHandle.argtypes = [ctypes.c_void_p]
_NAME = "Local\\FaxinaVarzea.SingleInstance"
_ALREADY_EXISTS = 183
_handle = None


def acquire(wait=0.0):
    """True se esta é a única instância. `wait` dá tempo da instância anterior terminar (ex.: reabrir como admin)."""
    global _handle
    deadline = time.time() + wait
    while True:
        h = _k32.CreateMutexW(None, 0, _NAME)
        if h and ctypes.get_last_error() != _ALREADY_EXISTS:
            _handle = h
            return True
        if h:
            _k32.CloseHandle(h)
        if time.time() >= deadline:
            return False
        time.sleep(0.3)


def focus_existing(title):
    """Traz a janela que já está aberta (mesmo escondida na bandeja) para a frente."""
    u = ctypes.windll.user32
    hwnd = u.FindWindowW(None, title)
    if not hwnd:
        return False
    u.ShowWindow(hwnd, 5)          # SW_SHOW (tira da bandeja)
    if u.IsIconic(hwnd):
        u.ShowWindow(hwnd, 9)      # SW_RESTORE (tira da barra de tarefas)
    u.keybd_event(0x12, 0, 0, 0)   # um Alt "aperta e solta" libera o SetForegroundWindow para quem acabou de ser aberto
    u.keybd_event(0x12, 0, 2, 0)
    u.BringWindowToTop(hwnd)
    u.SetForegroundWindow(hwnd)
    return True
