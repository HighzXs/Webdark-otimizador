"""Cantinho da tela com a temperatura (sempre por cima das outras janelas)."""
import tkinter as tk

import thermal

COLORS = {thermal.OK: "#16a34a", thermal.WARN: "#ca8a04", thermal.HOT: "#dc2626",
          thermal.CRIT: "#7f1d1d", thermal.NOSENSOR: "#4b5563"}
BLINK = "#ef4444"


class Overlay(tk.Toplevel):
    def __init__(self, root):
        super().__init__(root)
        self.withdraw()
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.93)
        self.lbl = tk.Label(self, text="", font=("Segoe UI", 12, "bold"), fg="white", padx=14, pady=7)
        self.lbl.pack()
        self.pos = None          # (x, y) depois que o usuário arrasta
        self._blink = False
        self._drag = (0, 0)
        for w in (self, self.lbl):
            w.bind("<ButtonPress-1>", self._press)
            w.bind("<B1-Motion>", self._move)

    def _press(self, e):
        self._drag = (e.x_root - self.winfo_x(), e.y_root - self.winfo_y())

    def _move(self, e):
        self.pos = (e.x_root - self._drag[0], e.y_root - self._drag[1])
        self.geometry(f"+{self.pos[0]}+{self.pos[1]}")

    def update_view(self, text, level):
        color = COLORS.get(level, COLORS[thermal.OK])
        if level == thermal.CRIT:
            self._blink = not self._blink
            color = BLINK if self._blink else color
        # só mexe na janela se algo mudou; update_idletasks() aqui processava a tela inteira do app e travava tudo
        key = (text, color, self.pos)
        if key == getattr(self, "_last", None) and self.winfo_viewable():
            return
        self._last = key
        self.lbl.configure(text=text, bg=color)
        self.configure(bg=color)
        if self.pos:
            x, y = self.pos
        else:
            width = self.lbl.winfo_reqwidth() + 4
            x, y = self.winfo_screenwidth() - width - 16, 16   # canto de cima, à direita
        self.geometry(f"+{x}+{y}")
        if not self.winfo_viewable():
            self.deiconify()
            self.attributes("-topmost", True)

    def hide(self):
        if self.winfo_viewable():
            self.withdraw()


def describe(reading, state, throttled, cur_max):
    """Texto curto do cantinho."""
    if not reading:
        return "🌡 sem leitura de temperatura"
    cpu_t, gpu_t = reading.get("cpu"), reading.get("gpu")
    parts = []
    if cpu_t is not None:
        parts.append(f"CPU {cpu_t:.0f}°C")
    if gpu_t is not None:
        parts.append(f"GPU {gpu_t:.0f}°C")
    base = "  •  ".join(parts) or "sem leitura"
    if state == thermal.CRIT:
        return f"🚨 {base} — PERIGO, clock em {cur_max or '…'}%"
    if state == thermal.HOT:
        return f"🔥 {base} — quente" + (f", clock em {cur_max}%" if throttled and cur_max else "")
    if state == thermal.WARN:
        return f"⚠ {base} — esquentando"
    if throttled and cur_max:
        return f"🌡 {base} — esfriando, clock em {cur_max}%"
    return f"🌡 {base}"
