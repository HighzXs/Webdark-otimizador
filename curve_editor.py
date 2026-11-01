"""Gráfico editável: temperatura (eixo X) -> clock máximo permitido (eixo Y)."""
import tkinter as tk

import customtkinter as ctk

T_MIN, T_MAX = 50, 105
P_MIN, P_MAX = 20, 100
PAD_L, PAD_R, PAD_T, PAD_B = 50, 20, 22, 34
HIT = 13           # raio (px) para pegar um ponto
MAX_POINTS = 8

DARK = {"bg": "#262626", "grid": "#3b3b3b", "text": "#9ca3af", "ok": "#173324", "warn": "#3b3217", "hot": "#3f1d1d",
        "live": "#e5e7eb"}
LIGHT = {"bg": "#f3f4f6", "grid": "#d1d5db", "text": "#4b5563", "ok": "#d1fae5", "warn": "#fef3c7", "hot": "#fee2e2",
         "live": "#111827"}


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


class CurveEditor(tk.Canvas):
    """Arraste os pontos. Duplo clique cria um ponto. Botão direito apaga."""

    def __init__(self, master, cfg, on_change, height=300):
        super().__init__(master, height=height, highlightthickness=0, bd=0)
        self.cfg, self.on_change = cfg, on_change
        self.drag = None
        self.live = None            # (temperatura, clock atual)
        self.tip = ""
        self.bind("<Configure>", lambda e: self.redraw())
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<B1-Motion>", self._motion)
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<Double-Button-1>", self._double)
        self.bind("<Button-3>", self._right)
        self.bind("<Motion>", self._hover)

    # ------------------------------------------------------------ geometria
    def _width(self):
        return max(self.winfo_width(), 420)

    def _height(self):
        return int(self["height"])

    def x(self, t):
        return PAD_L + (t - T_MIN) / (T_MAX - T_MIN) * (self._width() - PAD_L - PAD_R)

    def y(self, p):
        return PAD_T + (P_MAX - p) / (P_MAX - P_MIN) * (self._height() - PAD_T - PAD_B)

    def to_t(self, x):
        return T_MIN + (x - PAD_L) / (self._width() - PAD_L - PAD_R) * (T_MAX - T_MIN)

    def to_p(self, y):
        return P_MAX - (y - PAD_T) / (self._height() - PAD_T - PAD_B) * (P_MAX - P_MIN)

    @property
    def pts(self):
        return self.cfg.curve

    def _hit(self, ex, ey):
        for i, (t, p) in enumerate(self.pts):
            if (ex - self.x(t)) ** 2 + (ey - self.y(p)) ** 2 <= HIT ** 2:
                return i
        return None

    # ------------------------------------------------------------ eventos
    def _hover(self, e):
        self.configure(cursor="hand2" if self._hit(e.x, e.y) is not None else "arrow")

    def _press(self, e):
        self.drag = self._hit(e.x, e.y)
        if self.drag is not None:
            self._motion(e)

    def _motion(self, e):
        i = self.drag
        if i is None:
            return
        pts = self.pts
        t, p = round(self.to_t(e.x)), round(self.to_p(e.y) / 5) * 5
        lo_t = pts[i - 1][0] + 1 if i > 0 else T_MIN
        hi_t = pts[i + 1][0] - 1 if i < len(pts) - 1 else T_MAX
        lo_p = max(P_MIN, pts[i + 1][1]) if i < len(pts) - 1 else P_MIN
        hi_p = min(P_MAX, pts[i - 1][1]) if i > 0 else P_MAX
        pts[i] = [_clamp(t, lo_t, hi_t), _clamp(p, lo_p, hi_p)]
        self.tip = f"{pts[i][0]}°C  →  clock máximo {pts[i][1]}%"
        self.redraw()

    def _release(self, _):
        if self.drag is not None:
            self.drag = None
            self.tip = ""
            self.redraw()
            self.on_change()

    def _double(self, e):
        if self._hit(e.x, e.y) is not None or len(self.pts) >= MAX_POINTS:
            return
        t = _clamp(round(self.to_t(e.x)), T_MIN + 1, T_MAX - 1)
        if any(pt[0] == t for pt in self.pts):
            return
        idx = sum(1 for pt in self.pts if pt[0] < t)
        hi = self.pts[idx - 1][1] if idx > 0 else P_MAX
        lo = self.pts[idx][1] if idx < len(self.pts) else P_MIN
        p = _clamp(round(self.to_p(e.y) / 5) * 5, lo, hi)
        self.pts.insert(idx, [t, p])
        self.redraw()
        self.on_change()

    def _right(self, e):
        i = self._hit(e.x, e.y)
        if i is not None and len(self.pts) > 2:
            del self.pts[i]
            self.redraw()
            self.on_change()

    # ------------------------------------------------------------ desenho
    def set_live(self, temp, cap):
        self.live = (temp, cap) if temp is not None else None
        self.redraw()

    def redraw(self):
        c = self
        c.delete("all")
        col = DARK if ctk.get_appearance_mode() == "Dark" else LIGHT
        c.configure(bg=col["bg"])
        top, bot = PAD_T, self._height() - PAD_B
        warn, limit = self.cfg.warn, self.cfg.limit

        # faixas de temperatura
        c.create_rectangle(self.x(T_MIN), top, self.x(warn), bot, fill=col["ok"], outline="")
        c.create_rectangle(self.x(warn), top, self.x(limit), bot, fill=col["warn"], outline="")
        c.create_rectangle(self.x(limit), top, self.x(T_MAX), bot, fill=col["hot"], outline="")
        for name, a, b in (("LIVRE", T_MIN, warn), ("AVISO", warn, limit), ("LIMITANDO", limit, T_MAX)):
            if self.x(b) - self.x(a) > 50:
                c.create_text((self.x(a) + self.x(b)) / 2, top - 9, text=name, fill=col["text"], font=("Segoe UI", 8, "bold"))

        # grade e eixos
        for t in range(60, T_MAX, 10):
            c.create_line(self.x(t), top, self.x(t), bot, fill=col["grid"])
            c.create_text(self.x(t), bot + 12, text=f"{t}°C", fill=col["text"], font=("Segoe UI", 8))
        for p in (20, 40, 60, 80, 100):
            c.create_line(self.x(T_MIN), self.y(p), self.x(T_MAX), self.y(p), fill=col["grid"])
            c.create_text(PAD_L - 6, self.y(p), text=f"{p}%", fill=col["text"], anchor="e", font=("Segoe UI", 8))
        c.create_text(10, (top + bot) / 2, text="clock", fill=col["text"], angle=90, font=("Segoe UI", 8))

        # curva
        pts = sorted(self.pts)
        line = [self.x(T_MIN), self.y(pts[0][1])]
        for t, p in pts:
            line += [self.x(t), self.y(p)]
        line += [self.x(T_MAX), self.y(pts[-1][1])]
        c.create_line(*line, fill="#38bdf8", width=3)

        # marcador do momento atual
        if self.live:
            t, cap = self.live
            xt = self.x(_clamp(t, T_MIN, T_MAX))
            c.create_line(xt, top, xt, bot, fill=col["live"], dash=(4, 3))
            c.create_oval(xt - 5, self.y(cap) - 5, xt + 5, self.y(cap) + 5, fill="#22c55e", outline="")
            c.create_text(self._width() - PAD_R, top + 10, anchor="e", fill=col["live"], font=("Segoe UI", 9, "bold"),
                          text=f"agora: {t:.0f}°C  •  clock {cap}%")

        # pontos
        for i, (t, p) in enumerate(self.pts):
            r = 7
            c.create_oval(self.x(t) - r, self.y(p) - r, self.x(t) + r, self.y(p) + r,
                          fill="#ffffff" if i == self.drag else "#facc15", outline="#1f2937", width=2)
        if self.tip:
            c.create_text(PAD_L + 8, bot - 10, text=self.tip, anchor="w", fill=col["live"], font=("Segoe UI", 10, "bold"))
