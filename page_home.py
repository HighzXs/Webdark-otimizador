"""Página Início: resumo rápido, faxina rápida, modo segundo plano e aviso de atualização."""
import time
from tkinter import messagebox

import customtkinter as ctk
import psutil

import backend as bk
from ui_common import *
from version import VERSION

INTERVALS = {"30 min": 30, "1 hora": 60, "3 horas": 180}


class HomePage(Page):
    def __init__(self, app):
        super().__init__(app, "Início", "Resumo do seu PC e uma faxina segura com um clique.")
        self.last_summary = 0.0

        self.update_bar = ctk.CTkFrame(self, fg_color=("#e9defd", "#241a45"), corner_radius=10)
        self.update_lbl = ctk.CTkLabel(self.update_bar, text="", font=("Segoe UI", 13, "bold"), anchor="w")
        self.update_lbl.pack(side="left", padx=14, pady=10)
        ctk.CTkButton(self.update_bar, text="Depois", width=70, fg_color="gray40", hover_color="gray30",
                      command=self.update_bar.pack_forget).pack(side="right", padx=(4, 10))
        self.update_btn = ctk.CTkButton(self.update_bar, text="⬇ Atualizar agora", width=150, command=app.start_update)
        self.update_btn.pack(side="right")

        self.tiles = ctk.CTkFrame(self, fg_color="transparent")
        self.tiles.pack(fill="x", padx=20)
        self.tile = {}
        for i, (key, title) in enumerate([("free", "💽 Espaço livre (C:)"), ("junk", "🧹 Dá pra limpar"),
                                          ("start", "🚀 Abrem com o Windows"), ("ram", "🧠 Memória em uso")]):
            card = ctk.CTkFrame(self.tiles, fg_color=CARD, corner_radius=12)
            card.grid(row=0, column=i, padx=4, sticky="nsew")
            self.tiles.grid_columnconfigure(i, weight=1, uniform="t")
            ctk.CTkLabel(card, text=title, text_color=MUTED, font=("Segoe UI", 12)).pack(anchor="w", padx=14, pady=(10, 0))
            val = ctk.CTkLabel(card, text="…", font=("Segoe UI", 24, "bold"))
            val.pack(anchor="w", padx=14)
            sub = ctk.CTkLabel(card, text=" ", text_color=MUTED, font=("Segoe UI", 11))
            sub.pack(anchor="w", padx=14, pady=(0, 10))
            self.tile[key] = (val, sub)

        self.cards = ctk.CTkFrame(self, fg_color="transparent", height=1)   # sem filhos o CTkFrame teria 200px
        self.cards.pack(fill="x", padx=24, pady=(6, 0))

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=24, pady=12)
        self.btn = ctk.CTkButton(row, text="⚡  Faxina rápida", height=52, width=240, font=("Segoe UI", 18, "bold"),
                                 command=self.quick)
        self.btn.pack(side="left")
        ctk.CTkLabel(row, text="Limpa só o que é seguro: temporários, cache, lixeira e restos do Windows.",
                     text_color=MUTED, wraplength=300, justify="left").pack(side="left", padx=14)
        ctk.CTkButton(row, text="🛟 Criar ponto de restauração", width=210, fg_color="gray40", hover_color="gray30",
                      command=self.restore).pack(side="right")

        self.total_lbl = ctk.CTkLabel(self, text="", text_color=MUTED, anchor="w", justify="left")
        self.total_lbl.pack(fill="x", padx=26, pady=(0, 6))

        self.out = make_log(self, 110)
        self.out.pack(fill="both", expand=True, padx=24, pady=(0, 8))

        bgrow = ctk.CTkFrame(self, fg_color=CARD, corner_radius=10)
        bgrow.pack(fill="x", padx=24, pady=(0, 8))
        self.bg_sw = ctk.CTkSwitch(bgrow, text="🌙 Modo segundo plano", font=("Segoe UI", 13, "bold"),
                                   command=self.toggle_bg)
        if app.settings.get("background"):
            self.bg_sw.select()
        self.bg_sw.pack(side="left", padx=14, pady=10)
        ctk.CTkLabel(bgrow, text="Fecha na bandeja e confere o PC em silêncio, sem atrapalhar. Só avisa se achar algo.",
                     text_color=MUTED, wraplength=300, justify="left").pack(side="left", padx=4)
        self.interval = ctk.CTkOptionMenu(bgrow, values=list(INTERVALS), width=90, command=self.set_interval)
        cur = app.settings.get("scan_minutes", 60)
        self.interval.set(next((k for k, v in INTERVALS.items() if v == cur), "1 hora"))
        self.interval.pack(side="right", padx=14)
        ctk.CTkLabel(bgrow, text="Conferir a cada").pack(side="right")

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=24, pady=(0, 14))
        ctk.CTkLabel(bottom, text="Tema:").pack(side="left")
        sw = ctk.CTkSegmentedButton(bottom, values=["Escuro", "Claro"], command=self.theme)
        sw.set("Escuro")
        sw.pack(side="left", padx=8)
        ctk.CTkLabel(bottom, text=f"v{VERSION}", text_color=MUTED).pack(side="left", padx=8)
        if bk.is_admin():
            ctk.CTkLabel(bottom, text="🛡 Modo administrador ativo", text_color=GREEN).pack(side="right")
        else:
            ctk.CTkButton(bottom, text="🛡 Reabrir como administrador", fg_color="transparent", border_width=1,
                          text_color=("gray10", "gray90"), command=self.admin).pack(side="right")
            ctk.CTkLabel(bottom, text="Sem admin, algumas limpezas ficam de fora.  ", text_color=MUTED).pack(side="right")

    # ----------------------------------------------------------------- atualização
    def show_update(self, up):
        self.update_lbl.configure(text=f"🆕 Versão {up.version} disponível (você está na {VERSION})")
        self.update_bar.pack(fill="x", padx=24, pady=(0, 8), before=self.tiles)

    # ---------------------------------------------------------------------- resumo
    def theme(self, v):
        ctk.set_appearance_mode("dark" if v == "Escuro" else "light")
        from ui_table import restyle_all
        restyle_all()          # as tabelas abertas acompanham o tema escuro/claro

    def admin(self):
        if bk.relaunch_as_admin():
            self.app.shutdown()

    def on_show(self):
        for w in self.cards.winfo_children():
            w.destroy()
        for root in bk.fixed_drives():
            if root.upper().startswith("C"):
                continue
            try:
                total, used, free = bk.disk_usage(root)
            except OSError:
                continue
            card = ctk.CTkFrame(self.cards, fg_color=CARD, corner_radius=12)
            card.pack(fill="x", pady=3)
            low = free / total < 0.10
            ctk.CTkLabel(card, text=f"💽  Disco {root[:2]}", font=("Segoe UI", 14, "bold")).pack(side="left", padx=14, pady=10)
            ctk.CTkLabel(card, text=f"{bk.fmt_size(free)} livres de {bk.fmt_size(total)}"
                                    + ("   ⚠ quase cheio!" if low else ""),
                         text_color=RED if low else MUTED).pack(side="right", padx=14)
            bar = ctk.CTkProgressBar(card, width=260)
            if low:
                bar.configure(progress_color=RED)
            bar.set(used / total)
            bar.pack(side="right", padx=8)
        self.refresh_total()
        if time.time() - self.last_summary > 60:
            self.refresh_summary()

    def refresh_summary(self):
        self.last_summary = time.time()
        for val, sub in self.tile.values():
            val.configure(text="…")
            sub.configure(text=" ")
        self.app.bg(lambda: bk.quick_summary(lambda d: self.app.post(lambda d=d: self.show_summary(d))),
                    self.show_summary, label="Conferindo o PC…")

    def show_summary(self, d):
        if "free" in d:
            low = d["free"] / d["total"] < 0.10
            val, sub = self.tile["free"]
            val.configure(text=bk.fmt_size(d["free"]), text_color=RED if low else ("gray10", "#DCE4EE"))
            sub.configure(text=f"de {bk.fmt_size(d['total'])}" + ("  ⚠ quase cheio" if low else ""))
        if "startup" in d:
            val, sub = self.tile["start"]
            val.configure(text=str(d["startup"]))
            sub.configure(text="programas ligados" + ("  (muitos!)" if d["startup"] > 12 else ""))
        if "junk" in d:
            val, sub = self.tile["junk"]
            val.configure(text=bk.fmt_size(d["junk"]))
            sub.configure(text="lixo seguro, sem admin")
        val, sub = self.tile["ram"]
        pct = psutil.virtual_memory().percent
        val.configure(text=f"{pct:.0f}%", text_color=RED if pct >= 90 else ("gray10", "#DCE4EE"))
        sub.configure(text=f"{bk.fmt_size(psutil.virtual_memory().used)} de {bk.fmt_size(psutil.virtual_memory().total)}")

    def refresh_total(self):
        hist = bk.history_load()
        if not hist:
            self.total_lbl.configure(text="📈 Ainda não liberei nada por aqui. Bora fazer a primeira faxina!")
            return
        last = "\n".join(f"      {h['t']} — {h['what']}: {bk.fmt_size(h['bytes'])}" for h in hist[-3:][::-1])
        self.total_lbl.configure(text=f"📈 Total liberado até hoje: {bk.fmt_size(bk.history_total())}\n{last}")

    # -------------------------------------------------------------- modo segundo plano
    def toggle_bg(self):
        want = self.bg_sw.get() == 1
        if want and not self.app.settings.get("tray_tip_shown"):
            if not messagebox.askyesno(APP_NAME, "Modo segundo plano:\n\n"
                                                 "• Ao fechar a janela, o programa vai pra bandeja (perto do relógio) "
                                                 "em vez de fechar.\n"
                                                 "• De tempos em tempos ele confere o PC em silêncio, com prioridade "
                                                 "mínima, e só avisa se achar algo importante.\n"
                                                 "• O vigia de temperatura continua funcionando.\n"
                                                 "• Para fechar de vez: clique com o botão direito no ícone da bandeja > "
                                                 "'Sair de vez'.\n\nLigar?"):
                self.bg_sw.deselect()
                return
            self.app.settings["tray_tip_shown"] = True
        if not self.app.set_background(want):
            self.bg_sw.deselect() if want else self.bg_sw.select()
            messagebox.showerror(APP_NAME, "Não consegui criar o ícone da bandeja.")

    def set_interval(self, v):
        self.app.settings["scan_minutes"] = INTERVALS[v]
        self.app.save_settings()

    # -------------------------------------------------------------------- faxina
    def restore(self):
        if not bk.is_admin():
            messagebox.showinfo(APP_NAME, "Criar ponto de restauração precisa de administrador. "
                                          "Clique em 'Reabrir como administrador' aqui embaixo.")
            return
        self.app.bg(bk.create_restore_point,
                    lambda r: messagebox.showinfo(APP_NAME, ("🛟 " if r[0] else "😕 ") + r[1]),
                    label="Criando ponto de restauração…")

    def quick(self):
        if not messagebox.askyesno(APP_NAME, "Vou limpar arquivos temporários, cache dos navegadores, "
                                             "lixeira e restos de atualização.\n\n"
                                             "Feche os navegadores antes para limpar mais. Continuar?"):
            return
        self.btn.configure(state="disabled", text="Limpando…")
        cleaners = [c for c in bk.make_cleaners() if c.default and (bk.is_admin() or not c.admin)]
        self.out.configure(state="normal")
        self.out.delete("1.0", "end")
        self.out.configure(state="disabled")
        self.app.progress(0, "Começando…")

        def work():
            total = 0
            for i, c in enumerate(cleaners):
                self.app.post(lambda c=c: log(self.out, f"→ {c.name}…"))
                freed = bk.run_cleaner(c)
                total += freed
                self.app.post(lambda c=c, f=freed, p=(i + 1) / len(cleaners): (
                    log(self.out, f"   liberou {bk.fmt_size(f)}"), self.app.progress(p, c.name)))
            return total

        before = bk.disk_usage("C:\\")[2]

        def done(total):
            bk.history_add("Faxina rápida", total)
            after = bk.disk_usage("C:\\")[2]
            log(self.out, f"\n✅ Pronto! {bk.fmt_size(total)} liberados.")
            log(self.out, f"   Espaço livre no C: {bk.fmt_size(before)} → {bk.fmt_size(after)}")
            self.btn.configure(state="normal", text="⚡  Faxina rápida")
            self.app.progress(None)
            self.last_summary = 0
            self.on_show()

        self.app.bg(work, done, label="Limpando…")
