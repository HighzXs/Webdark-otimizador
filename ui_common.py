"""Pedaços de interface compartilhados entre as páginas."""
import os
import re
import sys
import threading
import time

import customtkinter as ctk

APP_NAME = "Faxina Várzea"

# paleta WebDark: fundo preto e degradê ciano -> azul -> violeta -> magenta
ACCENT, ACCENT_H = "#8b5cf6", "#7c3aed"       # botões e interruptores
CYAN, BLUE_G, VIOLET, MAGENTA = "#4fd1e6", "#5aa3e0", "#8f71d0", "#b043d1"
# cores com significado (não mudam com o tema)
GREEN, GREEN_H = "#16a34a", "#15803d"
RED, RED_H = "#dc2626", "#b91c1c"
AMBER = "#ca8a04"
BLUE = "#2563eb"
YELLOW = "#facc15"
MUTED = ("gray35", "gray65")
CARD = ("gray88", "#14141f")
LEVEL_COLOR = {"ok": GREEN, "care": AMBER, "danger": RED, "bad": RED}


def apply_theme():
    """Troca o tema verde padrão do customtkinter pela paleta WebDark. Chamar antes de criar a janela."""
    ctk.set_default_color_theme("green")
    t = ctk.ThemeManager.theme
    pair = lambda light, dark: [light, dark]  # noqa: E731
    t["CTk"]["fg_color"] = pair("gray92", "#05050a")
    t["CTkFrame"].update(fg_color=pair("gray86", "#0e0e16"), top_fg_color=pair("gray81", "#14141e"),
                         border_color=pair("gray65", "#2a2a3a"))
    t["CTkButton"].update(fg_color=pair(ACCENT_H, ACCENT), hover_color=pair("#6d28d9", ACCENT_H),
                          text_color=pair("white", "white"))
    t["CTkSwitch"].update(progress_color=pair(ACCENT_H, ACCENT), fg_color=pair("#939BA2", "#2a2a3a"))
    t["CTkProgressBar"].update(progress_color=pair(BLUE_G, CYAN), fg_color=pair("#c9c9d6", "#1f1f2e"))
    t["CTkOptionMenu"].update(fg_color=pair(ACCENT_H, "#5b3fc0"), button_color=pair("#6d28d9", "#4c2fa8"),
                              button_hover_color=pair("#5b21b6", "#3f2590"), text_color=pair("white", "white"))
    t["CTkSegmentedButton"].update(selected_color=pair(ACCENT_H, ACCENT), selected_hover_color=pair("#6d28d9", ACCENT_H),
                                   fg_color=pair("#979DA2", "#1b1b28"), unselected_color=pair("#979DA2", "#1b1b28"),
                                   unselected_hover_color=pair("gray70", "#2a2a3a"), text_color=pair("white", "white"))
    t["CTkCheckBox"].update(fg_color=pair(ACCENT_H, ACCENT), hover_color=pair("#6d28d9", ACCENT_H),
                            border_color=pair("#3E454A", "#5a5a75"))
    t["CTkTextbox"].update(fg_color=pair("#F9F9FA", "#0a0a12"))
    t["CTkSlider"].update(progress_color=pair(ACCENT_H, ACCENT), button_color=pair(ACCENT_H, ACCENT),
                          button_hover_color=pair("#6d28d9", ACCENT_H))


def gradient_title(text, size=24):
    """Texto com o degradê do WebDark, como imagem (o customtkinter não pinta texto em degradê)."""
    from PIL import Image, ImageDraw, ImageFont
    scale = 3
    font = None
    for path in (r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\arialbd.ttf"):
        try:
            font = ImageFont.truetype(path, size * scale)
            break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default()
    l, t, r, b = font.getbbox(text)
    w, h = r - l + 4 * scale, b - t + 4 * scale
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).text((2 * scale - l, 2 * scale - t), text, font=font, fill=255)
    stops = [(0.0, (0x4f, 0xd1, 0xe6)), (0.4, (0x5a, 0xa3, 0xe0)), (0.7, (0x8f, 0x71, 0xd0)), (1.0, (0xb0, 0x43, 0xd1))]
    grad = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(grad)
    for x in range(w):
        p = x / max(w - 1, 1)
        for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
            if p0 <= p <= p1:
                k = (p - p0) / (p1 - p0)
                d.line([(x, 0), (x, h)], fill=tuple(int(a + (b2 - a) * k) for a, b2 in zip(c0, c1)))
                break
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.paste(grad, (0, 0), mask)
    return ctk.CTkImage(out, size=(w // scale, h // scale))


def resource(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def shorten(text, n=70):
    return text if len(text) <= n else text[: n // 2 - 1] + "…" + text[-(n // 2):]


def log(box, text):
    box.configure(state="normal")
    box.insert("end", text + "\n")
    box.see("end")
    box.configure(state="disabled")


def make_log(parent, height=110):
    return ctk.CTkTextbox(parent, height=height, font=("Consolas", 12), state="disabled")


def stream_to_log(app, box, make_gen, on_done=None):
    """Roda um comando longo em segundo plano e joga a saída no log.

    Mostra o progresso de 10 em 10% e avisa a cada 30s que ainda está trabalhando.
    `on_done` roda no fim, mesmo se der erro.
    """
    stop = threading.Event()
    t0 = time.time()

    def beat():
        while not stop.wait(30):
            secs = int(time.time() - t0)
            app.post(lambda s=secs: log(box, f"⏳ ainda trabalhando… {s // 60}min{s % 60:02d}s"))

    def work():
        threading.Thread(target=beat, daemon=True).start()
        last = -1
        try:
            for line in make_gen():
                m = re.search(r"(\d+(?:[.,]\d+)?)\s*%", line)
                if m:
                    bucket = int(float(m.group(1).replace(",", "."))) // 10
                    if bucket == last:
                        continue
                    last = bucket
                    app.post(lambda f=min(float(m.group(1).replace(",", ".")) / 100, 1.0): app.progress(f, "Trabalhando…"))
                app.post(lambda l=line: log(box, l))
        except Exception as e:
            app.post(lambda e=e: log(box, f"✖ erro: {e}"))
        finally:
            stop.set()

    def done(_):
        log(box, "✅ Terminou.\n")
        app.progress(None)
        if on_done:
            on_done()

    app.bg(work, done, label="Executando…")


def chunked(widget, items, build, size=5, then=None):
    """Cria as linhas de uma lista aos poucos, para a janela não congelar com listas grandes."""
    token = object()
    widget._chunk_token = token
    it = iter(items)

    def step():
        if getattr(widget, "_chunk_token", None) is not token:
            return
        try:
            for _ in range(size):
                build(next(it))
        except StopIteration:
            if then:
                then()
            return
        except Exception:
            return
        widget.after(10, step)

    step()


def clear(frame, text=None):
    frame._chunk_token = None
    for w in frame.winfo_children():
        w.destroy()
    if text:
        ctk.CTkLabel(frame, text=text, text_color=MUTED).pack(pady=30)


def badge(parent, text, color, width=92):
    return ctk.CTkLabel(parent, text=text, width=width, height=22, corner_radius=6, fg_color=color,
                        text_color="white", font=("Segoe UI", 11, "bold"))


class Page(ctk.CTkFrame):
    def __init__(self, app, title, subtitle):
        super().__init__(app.content, fg_color="transparent")
        self.app = app
        self.loaded = False
        ctk.CTkLabel(self, text=title, font=("Segoe UI", 26, "bold")).pack(anchor="w", padx=24, pady=(20, 0))
        ctk.CTkLabel(self, text=subtitle, font=("Segoe UI", 13), text_color=MUTED,
                     wraplength=720, justify="left").pack(anchor="w", padx=24, pady=(0, 10))

    def on_show(self):
        pass
