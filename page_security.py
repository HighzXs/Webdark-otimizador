"""Página Segurança: temperatura ao vivo, proteção térmica e histórico."""
import json
import os
import subprocess
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

import backend as bk
import cpu
import thermal
from curve_editor import CurveEditor
from ui_common import *

STATE_TEXT = {
    thermal.OK: ("Tudo tranquilo", GREEN),
    thermal.WARN: ("Esquentando — fique de olho", AMBER),
    thermal.HOT: ("QUENTE! Reduzindo o clock pra esfriar", RED),
    thermal.CRIT: ("PERIGO! Clock no mínimo de segurança", "#f87171"),
    thermal.NOSENSOR: ("Sem leitura de temperatura", "gray50"),
}
PRESETS = {"🎮 Gamer": "gamer", "🛡 Cuidadoso": "careful", "🧯 Bem cuidadoso": "very"}
OVERLAY_MODES = {"Só quando esquentar": "hot", "Sempre": "always", "Nunca": "never"}
KIND_ICON = {"ok": "✔", "warn": "⚠", "hot": "🔥", "crit": "🚨", "clock": "⏬", "info": "•"}


def temp_color(t, cfg):
    if t is None:
        return "gray50"
    return RED if t >= cfg.limit else AMBER if t >= cfg.warn else GREEN


class SecurityPage(Page):
    def __init__(self, app):
        super().__init__(app, "Segurança", "Vigia a temperatura do PC. Se chegar perto do perigo, avisa num cantinho da tela "
                                           "e baixa o clock sozinho até esfriar.")
        self.guard, self.cfg = app.guard, app.cfg
        self.body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        self._procs_at = 0.0
        self._procs_busy = False
        self._build_now()
        self._build_protection()
        self._build_log()
        self._build_procs()
        self._build_tips()

    # --------------------------------------------------------------- agora
    def _build_now(self):
        ctk.CTkLabel(self.body, text="🌡 Temperatura agora", font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=8, pady=(10, 4))
        card = ctk.CTkFrame(self.body, fg_color=CARD, corner_radius=10)
        card.pack(fill="x", padx=4)
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(10, 0))
        self.cpu_big = ctk.CTkLabel(row, text="CPU —", font=("Segoe UI", 34, "bold"))
        self.cpu_big.pack(side="left")
        self.gpu_big = ctk.CTkLabel(row, text="GPU —", font=("Segoe UI", 34, "bold"))
        self.gpu_big.pack(side="left", padx=28)
        self.clock_lbl = ctk.CTkLabel(row, text="", text_color=MUTED, justify="right")
        self.clock_lbl.pack(side="right")
        self.state_lbl = ctk.CTkLabel(card, text="", font=("Segoe UI", 14, "bold"), anchor="w")
        self.state_lbl.pack(fill="x", padx=14, pady=(0, 4))
        self.canvas = tk.Canvas(card, height=150, highlightthickness=0, bd=0)
        self.canvas.pack(fill="x", padx=14, pady=(0, 12))

    # ------------------------------------------------------------- proteção
    def _build_protection(self):
        ctk.CTkLabel(self.body, text="🛡 Proteção térmica", font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=8, pady=(16, 4))
        card = ctk.CTkFrame(self.body, fg_color=CARD, corner_radius=10)
        card.pack(fill="x", padx=4)

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=14, pady=(10, 2))
        self.on_sw = ctk.CTkSwitch(top, text="Ligada: segue a curva abaixo e baixa o clock sozinha", progress_color=ACCENT,
                                   command=self.save)
        if self.cfg.enabled:
            self.on_sw.select()
        self.on_sw.pack(side="left")
        self.pc_lbl = ctk.CTkLabel(card, text="", text_color=MUTED, anchor="w")
        self.pc_lbl.pack(fill="x", padx=14)

        pre = ctk.CTkFrame(card, fg_color="transparent")
        pre.pack(fill="x", padx=14, pady=6)
        for name, mode in PRESETS.items():
            ctk.CTkButton(pre, text=name, width=150, command=lambda m=mode: self.preset(m)).pack(side="left", padx=(0, 6))
        ctk.CTkButton(pre, text="✨ Sugerir pro meu PC", width=170, fg_color="gray40", hover_color="gray30",
                      command=self.suggest).pack(side="left", padx=(6, 0))

        self.editor = CurveEditor(card, self.cfg, on_change=self.on_curve, height=300)
        self.editor.pack(fill="x", padx=14, pady=(2, 4))
        self.curve_lbl = ctk.CTkLabel(card, text="", text_color=MUTED, wraplength=700, justify="left", anchor="w")
        self.curve_lbl.pack(fill="x", padx=14)
        ctk.CTkLabel(card, text="Como usar: arraste os pontos amarelos. Duplo clique cria um ponto, botão direito apaga. "
                                "Cada ponto diz: \"se a CPU chegar nessa temperatura, o clock máximo vai para essa %\". "
                                "Abaixo do primeiro ponto o clock fica livre; esfriou, ele volta sozinho.",
                     text_color=MUTED, wraplength=700, justify="left", anchor="w").pack(fill="x", padx=14, pady=(2, 6))

        self.warn_var = ctk.IntVar(value=self.cfg.warn)
        r = ctk.CTkFrame(card, fg_color="transparent")
        r.pack(fill="x", padx=14, pady=3)
        self.warn_lbl = ctk.CTkLabel(r, text="", width=330, anchor="w")
        self.warn_lbl.pack(side="left")
        ctk.CTkSlider(r, from_=50, to=95, number_of_steps=45, variable=self.warn_var, progress_color=ACCENT, width=300,
                      command=lambda _=None: self.on_warn()).pack(side="left", padx=8)

        r = ctk.CTkFrame(card, fg_color="transparent")
        r.pack(fill="x", padx=14, pady=(6, 4))
        ctk.CTkLabel(r, text="Cantinho de aviso:").pack(side="left")
        self.ov_menu = ctk.CTkOptionMenu(r, values=list(OVERLAY_MODES), width=170, command=lambda _=None: self.save())
        self.ov_menu.set(next(k for k, v in OVERLAY_MODES.items() if v == self.cfg.overlay))
        self.ov_menu.pack(side="left", padx=8)
        self.snd_sw = ctk.CTkSwitch(r, text="Apitar ao esquentar", progress_color=ACCENT, command=self.save)
        if self.cfg.sound:
            self.snd_sw.select()
        self.snd_sw.pack(side="left", padx=18)

        r = ctk.CTkFrame(card, fg_color="transparent")
        r.pack(fill="x", padx=14, pady=(2, 6))
        ctk.CTkButton(r, text="📋 Copiar meu perfil", width=170, fg_color="gray40", hover_color="gray30",
                      command=self.export_profile).pack(side="left")
        ctk.CTkButton(r, text="📥 Colar perfil de um amigo", width=210, fg_color="gray40", hover_color="gray30",
                      command=self.import_profile).pack(side="left", padx=8)
        ctk.CTkLabel(card, text="O cantinho aparece por cima de jogos em janela ou tela cheia sem bordas. Em tela cheia "
                                "exclusiva (alguns jogos) o Windows esconde — nesse caso o PC apita.",
                     text_color=MUTED, wraplength=700, justify="left").pack(anchor="w", padx=14, pady=(0, 10))
        self.refresh_curve_info()

    def refresh_all(self):
        """Recarrega a tela depois que a curva/PC mudou por fora (detecção automática)."""
        self.warn_var.set(self.cfg.warn)
        self.editor.redraw()
        self.refresh_curve_info()

    def refresh_curve_info(self):
        c = self.cfg
        self.warn_lbl.configure(text=f"Avisar (amarelo e apito) a partir de {int(self.warn_var.get())}°C")
        pts = "   •   ".join(f"{t}°C → {p}%" for t, p in sorted(c.curve))
        self.curve_lbl.configure(text=f"Clock livre até {c.limit}°C.   {pts}.   Perigo a partir de {c.crit}°C.")
        who = c.cpu_name or "seu PC"
        self.pc_lbl.configure(text=f"Seu PC: {who}  •  limite estimado do chip: {c.tj}°C "
                                   f"(a curva inicial é calculada pra cada PC)")

    def on_warn(self):
        limit = self.cfg.limit
        if self.warn_var.get() >= limit:
            self.warn_var.set(limit - 1)
        self.refresh_curve_info()
        self.save()
        self.editor.redraw()

    def on_curve(self):
        """Chamado quando o usuário termina de mexer no gráfico."""
        self.cfg.curve_set = True
        if self.cfg.warn >= self.cfg.limit:
            self.cfg.warn = self.cfg.limit - 1
            self.warn_var.set(self.cfg.warn)
        self.refresh_curve_info()
        self.save()

    def preset(self, mode):
        curve, warn = thermal.make_curve(self.cfg.tj, mode)
        self.apply_profile(curve, warn)

    def suggest(self):
        """Detecta a CPU deste PC e monta a curva do perfil Gamer para ela."""
        def done(info):
            name = info[0]
            self.cfg.cpu_name, self.cfg.tj = name, thermal.guess_tjmax(name)
            self.preset("gamer")

        self.app.bg(cpu.info, done)

    def apply_profile(self, curve, warn):
        c = self.cfg
        c.curve[:] = [list(p) for p in curve]
        c.warn = warn
        c.curve_set = True
        self.warn_var.set(warn)
        self.editor.redraw()
        self.refresh_curve_info()
        self.save()

    def export_profile(self):
        data = json.dumps({"v": 1, "warn": self.cfg.warn, "curve": self.cfg.curve}, separators=(",", ":"))
        self.clipboard_clear()
        self.clipboard_append(data)
        messagebox.showinfo(APP_NAME, "Perfil copiado! Cole numa mensagem para o seu amigo.\n\n"
                                      "Dica: cada PC esquenta de um jeito. Peça para ele usar como ponto de partida "
                                      "e ajustar a curva no PC dele.")

    def import_profile(self):
        text = ctk.CTkInputDialog(text="Cole aqui o perfil que seu amigo mandou:", title=APP_NAME).get_input()
        if not text:
            return
        try:
            data = json.loads(text.strip())
            curve = thermal.valid_curve(data["curve"])
            warn = int(data.get("warn", 80))
        except (ValueError, KeyError, TypeError):
            curve = None
        if not curve:
            messagebox.showerror(APP_NAME, "Esse perfil não parece válido.")
            return
        self.apply_profile(curve, min(warn, curve[0][0] - 1))

    def save(self):
        c = self.cfg
        c.enabled = self.on_sw.get() == 1
        c.warn = int(self.warn_var.get())
        c.overlay = OVERLAY_MODES[self.ov_menu.get()]
        c.sound = self.snd_sw.get() == 1
        thermal.save_config(c)
        self.app.sensor_sync()

    # ------------------------------------------------------------- histórico
    def _build_log(self):
        ctk.CTkLabel(self.body, text="📜 O que aconteceu", font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=8, pady=(16, 4))
        self.tip_lbl = ctk.CTkLabel(self.body, text="", text_color=YELLOW, wraplength=720, justify="left")
        self.tip_lbl.pack(anchor="w", padx=8)
        self.log_box = make_log(self.body, 130)
        self.log_box.pack(fill="x", padx=4, pady=4)

    def refresh_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        evs = thermal.recent_events(30)
        if not evs:
            self.log_box.insert("end", "Nada ainda. Quando o PC esquentar, aparece aqui.\n")
        for stamp, kind, text in evs:
            self.log_box.insert("end", f"{stamp[5:16]}  {KIND_ICON.get(kind, '•')} {text}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")
        n = thermal.hot_events_last_days(7)
        self.tip_lbl.configure(text=(f"⚠ O PC passou do limite {n} vezes nos últimos 7 dias. Limpe a poeira dos coolers, "
                                     "use o notebook em superfície dura e, se for antigo, troque a pasta térmica.")
                               if n >= 3 else "")

    # ------------------------------------------------------- quem está pesando
    def _build_procs(self):
        ctk.CTkLabel(self.body, text="🔎 Quem está pesando agora", font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=8, pady=(16, 4))
        self.proc_box = ctk.CTkFrame(self.body, fg_color=CARD, corner_radius=10)
        self.proc_box.pack(fill="x", padx=4)
        self.proc_lbl = ctk.CTkLabel(self.proc_box, text="Lendo…", justify="left", anchor="w", font=("Consolas", 13))
        self.proc_lbl.pack(fill="x", padx=14, pady=(10, 4))
        ctk.CTkButton(self.proc_box, text="Abrir o Gerenciador de Tarefas", width=240, fg_color="gray40",
                      hover_color="gray30", command=lambda: subprocess.Popen(["taskmgr"])).pack(anchor="w", padx=14, pady=(0, 10))

    def refresh_procs(self):
        import time
        if self._procs_busy or time.time() - self._procs_at < 6:
            return
        self._procs_busy = True
        threads = os.cpu_count() or 1

        def work():
            try:
                raw = bk.ps("Get-CimInstance Win32_PerfFormattedData_PerfProc_Process | "
                            "Where-Object { $_.Name -ne '_Total' -and $_.Name -ne 'Idle' } | "
                            "Sort-Object PercentProcessorTime -Descending | Select-Object -First 5 Name,PercentProcessorTime | "
                            "ConvertTo-Json -Compress", timeout=30).strip()
                data = json.loads(raw) if raw else []
                return [data] if isinstance(data, dict) else data
            except Exception:
                return []

        def done(rows):
            import time as _t
            self._procs_busy = False
            self._procs_at = _t.time()
            lines = []
            for r in rows:
                name = str(r.get("Name", "?")).split("#")[0]
                pct = min(100.0, float(r.get("PercentProcessorTime", 0)) / threads)
                lines.append(f"{name[:34]:<36}{pct:5.1f}% da CPU")
            self.proc_lbl.configure(text="\n".join(lines) or "Nada pesado agora. 👍")

        self.app.bg(work, done, quiet=True)

    # ------------------------------------------------------------------ dicas
    def _build_tips(self):
        ctk.CTkLabel(self.body, text="💡 Como esfriar o PC", font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=8, pady=(16, 4))
        tips = ("• Notebook: use em superfície dura e plana, nunca em cama ou sofá.\n"
                "• Limpe a poeira das saídas de ar a cada 6 meses.\n"
                "• Limite o FPS do jogo (ex.: 60). Menos FPS = menos calor.\n"
                "• Plano de energia Equilibrado + clock máximo em 90% já tira vários graus (aba Desempenho).\n"
                "• Fechar navegador e apps pesados enquanto joga ajuda bastante.")
        ctk.CTkLabel(self.body, text=tips, justify="left", anchor="w", text_color=MUTED).pack(anchor="w", padx=12, pady=(0, 14))

    # --------------------------------------------------------------- vida
    def on_show(self):
        if not self.loaded:
            self.loaded = True
            self.tick()

    def tick(self):
        if self.winfo_ismapped():
            self.render()
        self.after(2000, self.tick)

    def render(self):
        g, cfg = self.guard, self.cfg
        d = g.reading or {}
        cpu_t, gpu_t = d.get("cpu"), d.get("gpu")
        self.cpu_big.configure(text=f"CPU {cpu_t:.0f}°C" if cpu_t is not None else "CPU —", text_color=temp_color(cpu_t, cfg))
        self.gpu_big.configure(text=f"GPU {gpu_t:.0f}°C" if gpu_t is not None else "GPU —", text_color=temp_color(gpu_t, cfg))
        mhz, util = d.get("mhz"), d.get("util")
        self.clock_lbl.configure(text=(f"Clock {mhz / 1000:.2f} GHz\nUso {util:.0f}%" if mhz is not None and util is not None else ""))
        text, color = STATE_TEXT[g.state]
        if g.throttled and g.cur_max:
            text += f"  (clock em {g.cur_max}%)"
        if not cfg.enabled:
            text += "  — proteção DESLIGADA"
        self.state_lbl.configure(text=text, text_color=color)
        self.editor.set_live(cpu_t, g.cur_max or 100)
        self.draw_graph()
        self.refresh_log()
        self.refresh_procs()

    def draw_graph(self):
        c = self.canvas
        c.delete("all")
        dark = ctk.get_appearance_mode() == "Dark"
        c.configure(bg="#262626" if dark else "#e5e5e5")
        w, h = max(c.winfo_width(), 300), int(c["height"])
        lo, hi = 30, 105
        y = lambda t: h - 14 - (min(max(t, lo), hi) - lo) / (hi - lo) * (h - 24)
        fg = "#9ca3af"
        for t, col in ((self.cfg.warn, AMBER), (self.cfg.limit, RED)):
            c.create_line(0, y(t), w, y(t), fill=col, dash=(4, 3))
            c.create_text(w - 4, y(t) - 7, text=f"{t}°C", fill=col, anchor="e", font=("Segoe UI", 8))
        hist = list(self.guard.history)
        if len(hist) < 2:
            c.create_text(w // 2, h // 2, text="Coletando dados…", fill=fg)
            return
        n = len(hist)
        step = (w - 10) / max(self.guard.history.maxlen - 1, 1)
        x0 = w - 5 - (n - 1) * step
        for idx, color, width in ((1, "#38bdf8", 2), (2, "#a78bfa", 1)):   # CPU azul, GPU roxo
            pts = []
            for i, sample in enumerate(hist):
                if sample[idx] is not None:
                    pts += [x0 + i * step, y(sample[idx])]
            if len(pts) >= 4:
                c.create_line(*pts, fill=color, width=width, smooth=True)
        c.create_text(6, 8, text="CPU (azul)   GPU (roxo)   últimos ~5 min", fill=fg, anchor="w", font=("Segoe UI", 8))
