"""Faxina Várzea - interface."""
import queue
import threading
import time
import webbrowser
from tkinter import messagebox

import customtkinter as ctk

import backend as bk
import cpu
import health
import overlay
import settings
import single
import thermal
import updater
from page_home import HomePage
from page_security import SecurityPage
from page_space import SpacePage
from page_system import ProcPage
from pages2 import HealthPage, PerfPage, StartupPage
from tray import Tray
from ui_common import *
from ui_table import CHECK_OFF, CHECK_ON, DataTable
from version import REPO

apply_theme()
ctk.set_appearance_mode("dark")


# ------------------------------------------------------------------ Bloatware
class BloatPage(Page):
    TITLES = {"lixo": "🗑 Lixo — recomendo remover", "opcional": "🤔 Opcionais — você decide",
              "outro": "⚠ Outros apps — só remova se souber o que é"}
    PARTIAL = "▣"        # grupo com só alguns apps marcados

    def __init__(self, app):
        super().__init__(app, "Bloatware", "Apps que vêm com o Windows e quase ninguém usa. "
                                           "Marcados em verde = lixo seguro. Dá pra reinstalar depois pela Microsoft Store.")
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=24)
        ctk.CTkButton(bar, text="Marcar recomendados", width=160, command=self.mark_rec).pack(side="left", padx=(0, 6))
        ctk.CTkButton(bar, text="Desmarcar tudo", width=130, fg_color="gray40", hover_color="gray30",
                      command=lambda: self.mark(lambda it: False)).pack(side="left")
        self.go = ctk.CTkButton(bar, text="🔥 Remover marcados", width=180, fg_color=RED, hover_color=RED_H,
                                command=self.remove)
        self.go.pack(side="right")
        self.count = ctk.CTkLabel(bar, text="", text_color=MUTED)
        self.count.pack(side="right", padx=12)
        self.out = make_log(self, 90)
        self.out.pack(side="bottom", fill="x", padx=24, pady=(0, 14))
        self.table = DataTable(self, [
            {"id": "on", "text": "Remover", "width": 84, "anchor": "center", "toggle": True},
            {"id": "app", "text": "App", "width": 330, "minwidth": 160},
            {"id": "desc", "text": "Descrição", "width": 300, "stretch": True},
        ], tree=True, selectmode="browse", on_toggle=self.toggle, on_open=self.open_row)
        self.table.pack(fill="both", expand=True, padx=24, pady=6)
        self.table.tag("lixo", foreground=GREEN)
        self.table.tag("outro", foreground=AMBER)
        self.table.tag("g_lixo", foreground=GREEN, bold=True)
        self.table.tag("g_opcional", bold=True)
        self.table.tag("g_outro", foreground=AMBER, bold=True)
        self.rows = {}      # iid do app -> (item, marcado)
        self.groups = {}    # nível -> iid do grupo ("g:lixo")

    def on_show(self):
        if self.loaded:
            return
        self.loaded = True
        self.fill_loading("Procurando apps instalados… (pode levar uns segundos)")
        self.app.bg(bk.list_appx, self.populate)

    def fill_loading(self, text):
        self.table.clear()
        self.rows, self.groups = {}, {}
        self.table.message(text)
        self.update_count()

    def populate(self, items):
        t = self.table
        t.clear()
        self.rows, self.groups = {}, {}
        for i, it in enumerate(items):
            gid = self.groups.get(it.level)
            if gid is None:
                gid = self.groups[it.level] = t.add(["", self.TITLES.get(it.level, it.level), ""],
                                                    iid="g:" + it.level, tags=("g_" + it.level,))
            on = it.level == "lixo"
            iid = t.add([CHECK_ON if on else CHECK_OFF, it.friendly, it.desc], iid=f"a:{i}", parent=gid, tags=(it.level,))
            self.rows[iid] = (it, on)
        for gid in self.groups.values():
            t.update(gid, desc=f"{len(t.rows(gid))} app(s)")
        t.restripe()
        if not items:
            t.message("Nenhum bloatware encontrado. 🎉")
        self._sync()

    def _put(self, iid, on):
        self.rows[iid] = (self.rows[iid][0], on)
        self.table.update(iid, on=CHECK_ON if on else CHECK_OFF)

    def _sync(self):
        """Atualiza a marca de cada grupo (todos / alguns / nenhum) e o contador."""
        for gid in self.groups.values():
            marks = [self.rows[k][1] for k in self.table.rows(gid)]
            self.table.update(gid, on=CHECK_ON if marks and all(marks) else self.PARTIAL if any(marks) else CHECK_OFF)
        self.update_count()

    def toggle(self, iid, col=None):
        if iid in self.rows:
            self._put(iid, not self.rows[iid][1])
        elif iid.startswith("g:"):                       # clicar na marca do grupo muda todos de uma vez
            kids = self.table.rows(iid)
            want = not all(self.rows[k][1] for k in kids)
            for k in kids:
                self._put(k, want)
        self._sync()

    def open_row(self, iid):
        if iid in self.rows:                             # duplo clique no app marca/desmarca; no grupo só abre/fecha
            self.toggle(iid)

    def update_count(self):
        n = sum(1 for _, on in self.rows.values() if on)
        self.count.configure(text=f"{n} marcado(s)")

    def mark(self, pred):
        for iid, (it, _) in self.rows.items():
            self._put(iid, bool(pred(it)))
        self._sync()

    def mark_rec(self):
        self.mark(lambda it: it.level == "lixo")

    def remove(self):
        chosen = [it for it, on in self.rows.values() if on]
        if not chosen:
            messagebox.showinfo(APP_NAME, "Nenhum app marcado.")
            return
        names = "\n".join("• " + c.friendly for c in chosen[:15]) + ("\n…" if len(chosen) > 15 else "")
        if not messagebox.askyesno(APP_NAME, f"Remover {len(chosen)} app(s)?\n\n{names}\n\n"
                                             "Dá pra reinstalar depois pela Microsoft Store."):
            return
        self.go.configure(state="disabled", text="Removendo…")

        def work():
            ok = 0
            if bk.is_admin():
                self.app.post(lambda: log(self.out, "🛟 Criando ponto de restauração antes…"))
                _, msg = bk.create_restore_point("Faxina Várzea - antes de remover apps")
                self.app.post(lambda: log(self.out, "   " + msg))
            else:
                self.app.post(lambda: log(self.out, "⚠ Sem admin: sem ponto de restauração (os apps voltam pela Store)."))
            for line in bk.remove_appx(chosen, bk.is_admin()):
                if line.startswith("OK|"):
                    ok += 1
                    self.app.post(lambda l=line: log(self.out, "✔ removido: " + l[3:]))
                elif line.startswith("FAIL|"):
                    self.app.post(lambda l=line: log(self.out, "✖ falhou: " + l[5:]))
            return ok

        def done(ok):
            log(self.out, f"\n✅ {ok} app(s) removidos.")
            self.go.configure(state="normal", text="🔥 Remover marcados")
            self.loaded = False
            self.on_show()

        self.app.bg(work, done)


# -------------------------------------------------------------------- Limpeza
class CleanPage(Page):
    def __init__(self, app):
        super().__init__(app, "Limpeza", "Escolha o que limpar. Nada aqui apaga seus documentos, fotos ou senhas.")
        self.cleaners = bk.make_cleaners()
        self.vars = {}
        self.size_lbls = {}
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=24)
        self.scan_btn = ctk.CTkButton(bar, text="🔍 Analisar", width=130, command=self.analyze)
        self.scan_btn.pack(side="left")
        self.total = ctk.CTkLabel(bar, text="", text_color=MUTED)
        self.total.pack(side="left", padx=12)
        self.go = ctk.CTkButton(bar, text="🧹 Limpar marcados", width=170, fg_color=ACCENT, hover_color=ACCENT_H, command=self.clean)
        self.go.pack(side="right")

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=14, pady=6)
        admin = bk.is_admin()
        for c in self.cleaners:
            row = ctk.CTkFrame(scroll, fg_color=CARD, corner_radius=8)
            row.pack(fill="x", pady=3, padx=4)
            var = ctk.BooleanVar(value=c.default and (admin or not c.admin))
            self.vars[c.key] = var
            ctk.CTkCheckBox(row, text="", variable=var, width=24, fg_color=ACCENT, hover_color=ACCENT_H,
                            state="normal" if (admin or not c.admin) else "disabled").pack(side="left", padx=(12, 0), pady=10)
            txt = ctk.CTkFrame(row, fg_color="transparent")
            txt.pack(side="left", fill="x", expand=True, padx=8)
            ctk.CTkLabel(txt, text=c.name, font=("Segoe UI", 13, "bold"), anchor="w").pack(anchor="w")
            ctk.CTkLabel(txt, text=c.desc, text_color=MUTED, anchor="w", wraplength=520, justify="left").pack(anchor="w")
            lbl = ctk.CTkLabel(row, text="—", width=90, font=("Segoe UI", 13, "bold"))
            lbl.pack(side="right", padx=12)
            self.size_lbls[c.key] = lbl

        ex = ctk.CTkFrame(scroll, fg_color=CARD, corner_radius=8)
        ex.pack(fill="x", pady=(14, 3), padx=4)
        ctk.CTkLabel(ex, text="🔧 Extras para liberar MUITO espaço (precisam de admin)",
                     font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=12, pady=(10, 4))
        self.hib_btn = ctk.CTkButton(ex, text="Desligar hibernação", width=200, command=self.hibernate)
        self.hib_btn.pack(anchor="w", padx=12, pady=3)
        self.hib_lbl = ctk.CTkLabel(ex, text="", text_color=MUTED, wraplength=640, justify="left")
        self.hib_lbl.pack(anchor="w", padx=12)
        ctk.CTkButton(ex, text="Limpar componentes antigos do Windows (DISM)", width=330,
                      command=self.dism).pack(anchor="w", padx=12, pady=(10, 0))
        ctk.CTkLabel(ex, text="Demora uns minutos e fica parado em 20%/40%… é normal. Não feche.",
                     text_color=MUTED).pack(anchor="w", padx=12)
        ctk.CTkButton(ex, text="Abrir Limpeza de Disco do Windows (apaga Windows.old)", width=380,
                      command=bk.open_windows_cleanmgr).pack(anchor="w", padx=12, pady=(10, 12))
        self.out = make_log(self, 80)
        self.out.pack(fill="x", padx=24, pady=(0, 14))

    def on_show(self):
        if not self.loaded:
            self.loaded = True
            self.analyze()
            hib = bk.hiberfil_size()
            self.hib_lbl.configure(text=(f"Arquivo de hibernação ocupa {bk.fmt_size(hib)}. Desligar também desativa a "
                                         "'inicialização rápida'." if hib else "Hibernação já está desligada."))

    def analyze(self):
        self.scan_btn.configure(state="disabled", text="Analisando…")

        def work():
            for c in self.cleaners:
                bk.measure(c)
                self.app.post(lambda c=c: self.size_lbls[c.key].configure(text=bk.fmt_size(c.size)))

        def done(_):
            tot = sum(c.size for c in self.cleaners if self.vars[c.key].get())
            self.total.configure(text=f"Marcados: {bk.fmt_size(tot)} para liberar")
            self.scan_btn.configure(state="normal", text="🔍 Analisar")

        self.app.bg(work, done)

    def clean(self):
        chosen = [c for c in self.cleaners if self.vars[c.key].get()]
        if not chosen:
            return
        warns = [c for c in chosen if c.warn]
        if warns:
            txt = "\n\n".join(f"⚠ {c.name}\n{c.warn}" for c in warns)
            if not messagebox.askyesno(APP_NAME, txt + "\n\nQuer mesmo limpar isso?", icon="warning", default="no"):
                return
        if not messagebox.askyesno(APP_NAME, f"Limpar {len(chosen)} item(ns)? Feche os navegadores antes."):
            return
        self.go.configure(state="disabled", text="Limpando…")

        def work():
            total = 0
            for c in chosen:
                f = bk.run_cleaner(c)
                total += f
                self.app.post(lambda c=c, f=f: (log(self.out, f"{c.name}: {bk.fmt_size(f)}"),
                                                self.size_lbls[c.key].configure(text=bk.fmt_size(c.size))))
            return total

        def done(total):
            bk.history_add("Limpeza", total)
            log(self.out, f"✅ {bk.fmt_size(total)} liberados.")
            self.go.configure(state="normal", text="🧹 Limpar marcados")
            self.total.configure(text=f"Liberado: {bk.fmt_size(total)}")

        self.app.bg(work, done)

    def need_admin(self):
        if bk.is_admin():
            return False
        messagebox.showinfo(APP_NAME, "Isso precisa de administrador. Volte no Início e clique em "
                                      "'Reabrir como administrador'.")
        return True

    def hibernate(self):
        if self.need_admin():
            return
        if not messagebox.askyesno(APP_NAME, "Desligar a hibernação libera o arquivo hiberfil.sys (vários GB), "
                                             "mas desativa hibernar e a inicialização rápida. Continuar?"):
            return
        ok = bk.hibernate_off()
        self.hib_lbl.configure(text="Hibernação desligada. ✅" if ok else "Não consegui desligar. 😕")

    def dism(self):
        if self.need_admin():
            return
        log(self.out, "Iniciando limpeza de componentes… pode levar 10+ minutos, não feche.")
        stream_to_log(self.app, self.out, health.dism_cleanup)


# ------------------------------------------------------------------ Programas
class ProgramsPage(Page):
    def __init__(self, app):
        super().__init__(app, "Programas instalados", "Os mais pesados primeiro. Programas suspeitos (testes de antivírus, "
                                                      "barras de ferramentas) aparecem no topo com ⚠.")
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=24)
        ctk.CTkButton(bar, text="🔄 Atualizar", width=110, fg_color="gray40", hover_color="gray30",
                      command=self.reload).pack(side="left")
        self.count = ctk.CTkLabel(bar, text="", text_color=MUTED)
        self.count.pack(side="left", padx=12)
        self.go = ctk.CTkButton(bar, text="Desinstalar", width=130, fg_color=RED, hover_color=RED_H, state="disabled",
                                command=self.uninstall_selected)
        self.go.pack(side="right")
        self.table = DataTable(self, [
            {"id": "name", "text": "Programa", "width": 420, "minwidth": 160, "stretch": True, "sort": "text"},
            {"id": "pub", "text": "Editora", "width": 230, "sort": "text"},
            {"id": "size", "text": "Tamanho", "width": 100, "anchor": "e", "sort": "num"},
        ], selectmode="browse", on_open=self.open_row, on_select=self.picked)
        self.table.pack(fill="both", expand=True, padx=24, pady=(6, 14))
        self.table.tag("suspect", foreground=AMBER)
        self.progs = {}     # iid -> Program

    def on_show(self):
        if self.loaded:
            return
        self.loaded = True
        self.progs = {}
        self.table.clear()
        self.table.message("Lendo programas…")
        self.count.configure(text="")
        self.picked([])
        self.app.bg(bk.list_programs, self.populate)

    def reload(self):
        self.loaded = False
        self.on_show()

    def populate(self, progs):
        t = self.table
        t.clear()
        self.progs = {}
        for i, p in enumerate(progs):          # na ordem que veio: suspeitos primeiro, depois os maiores
            iid = t.add([("⚠ " if p.suspect else "") + p.name, p.publisher or "—", bk.fmt_size(p.size) if p.size else "—"],
                        iid=f"p:{i}", tags=("suspect",) if p.suspect else (), raw={"size": p.size, "name": p.name})
            self.progs[iid] = p
        col, rev = getattr(t, "_sort", (None, False))
        if col:                                 # mantém a ordenação que a pessoa escolheu no cabeçalho
            t.sort_by(col, rev)
        else:
            t.restripe()
        if not progs:
            t.message("Nenhum programa encontrado.")
        self.count.configure(text=f"{len(progs)} programa(s)")
        self.picked(t.sel())

    def picked(self, sel):
        self.go.configure(state="normal" if sel else "disabled")

    def open_row(self, iid):
        if iid in self.progs:
            self.uninstall(self.progs[iid])

    def uninstall_selected(self):
        sel = self.table.sel()
        if sel and sel[0] in self.progs:
            self.uninstall(self.progs[sel[0]])

    def uninstall(self, p):
        if messagebox.askyesno(APP_NAME, f"Abrir o desinstalador de:\n\n{p.name}?"):
            bk.run_uninstaller(p.uninstall)
            self.loaded = False


# ------------------------------------------------------------------------ App
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.settings = settings.load()
        self._busy, self._busy_label, self._prog, self._status_mode = 0, "", None, None
        self._hidden = False
        self.tray = None
        self._quiet_after = None
        self.update_info = None
        self.geometry("1040x720")
        self.minsize(900, 600)
        self.after(250, self._icon)
        self.q = queue.Queue()
        self.after(80, self._pump)

        # vigia de temperatura: roda o tempo todo, mesmo com outra aba aberta
        self.cfg = thermal.load_config()
        self.sensor = thermal.Sensor()
        self.guard = thermal.Guard(self.sensor, self.cfg)
        self.overlay = overlay.Overlay(self)
        self._guard_busy = False
        self.guard.recover()
        self.current = "home"
        self.sensor_sync()           # o sensor só liga se a proteção estiver ativada (ou a aba Segurança aberta)
        self.after(2500, self._guard_tick)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        side = ctk.CTkFrame(self, width=210, corner_radius=0)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        try:
            from PIL import Image
            logo = ctk.CTkImage(Image.open(resource("icon.png")), size=(72, 72))
            ctk.CTkLabel(side, image=logo, text="").pack(pady=(20, 0))
        except Exception:
            pass
        try:
            ctk.CTkLabel(side, image=gradient_title("Faxina Várzea", 22), text="").pack(padx=10, pady=(6, 14))
        except Exception:
            ctk.CTkLabel(side, text="Faxina Várzea", font=("Segoe UI", 22, "bold"), text_color=CYAN).pack(padx=10, pady=(6, 14))

        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.pack(side="right", fill="both", expand=True)

        # barra de atividade: aparece sempre que algo está sendo verificado em segundo plano
        self.status = ctk.CTkFrame(self.content, fg_color="transparent", height=24)
        self.status.pack(side="bottom", fill="x", padx=24, pady=(0, 4))
        self.status_lbl = ctk.CTkLabel(self.status, text="", text_color=MUTED, font=("Segoe UI", 11))
        self.status_bar = ctk.CTkProgressBar(self.status, height=6, width=220, mode="indeterminate")

        self.pages = {}
        self.nav = {}
        for key, label, cls in [("home", "🏠  Início", HomePage), ("bloat", "🧨  Bloatware", BloatPage),
                                ("clean", "🧹  Limpeza", CleanPage), ("space", "📊  Espaço", SpacePage),
                                ("progs", "📦  Programas", ProgramsPage), ("start", "🚀  Inicialização", StartupPage),
                                ("health", "🩺  Saúde", HealthPage), ("perf", "⚡  Desempenho", PerfPage),
                                ("proc", "🧠  Processos", ProcPage),
                                ("security", "🛡  Segurança", SecurityPage)]:
            self.pages[key] = cls(self)
            b = ctk.CTkButton(side, text=label, anchor="w", height=36, font=("Segoe UI", 15), fg_color="transparent",
                              text_color=("gray10", "gray90"), hover_color=("gray75", "gray25"),
                              command=lambda k=key: self.show(k))
            b.pack(fill="x", padx=12, pady=1)
            self.nav[key] = b
        ctk.CTkLabel(side, text="feito na porra 💚💛", text_color=MUTED).pack(side="bottom", pady=14)
        self.show("home")
        self.after(1500, self._auto_profile)
        self.bind("<Map>", lambda e: setattr(self, "_hidden", False) if e.widget is self else None)
        if self.settings.get("background"):
            self.set_background(True)
        self.after(8000, self.check_update)

    def _icon(self):
        try:
            self.iconbitmap(resource("icon.ico"))
        except Exception:
            pass

    # --- vigia de temperatura
    def _auto_profile(self):
        """Primeira vez neste PC: detecta a CPU e monta a curva certa para ela (em vez de copiar a de outro PC)."""
        c = self.cfg
        if c.curve_set and c.cpu_name:
            return

        def done(info):
            c.cpu_name, c.tj = info[0], thermal.guess_tjmax(info[0])
            if not c.curve_set:
                curve, warn = thermal.make_curve(c.tj, "gamer")
                c.curve[:] = curve
                c.warn = warn
            thermal.save_config(c)
            self.pages["security"].refresh_all()

        self.bg(cpu.info, done, quiet=True)

    def _sensor_wanted(self):
        return self.cfg.enabled or self.current == "security"

    def sensor_sync(self):
        """Liga o sensor só quando precisa: proteção ativada ou aba Segurança aberta. Desligado, não roda nada."""
        if self._sensor_wanted():
            self.sensor.start()
            return
        if self.guard.throttled:
            self.guard.restore()
        self.sensor.stop()
        self.guard.reading = None
        self.guard.state = thermal.NOSENSOR
        self.overlay.hide()

    def _guard_tick(self):
        self.after(2000, self._guard_tick)
        if self._guard_busy or not self._sensor_wanted():
            return
        self._guard_busy = True

        def done(_):
            self._guard_busy = False
            self._guard_ui()

        self.bg(self.guard.tick, done, quiet=True)

    def _guard_ui(self):
        import winsound
        g, cfg = self.guard, self.cfg
        if not cfg.enabled:
            g.alert = None
            self.overlay.hide()
            return
        if g.alert:
            if cfg.sound:
                try:
                    winsound.MessageBeep(winsound.MB_ICONHAND if g.alert in (thermal.HOT, thermal.CRIT)
                                         else winsound.MB_ICONEXCLAMATION)
                except Exception:
                    pass
            g.alert = None
        hot = thermal.RANK[g.state] >= thermal.RANK[thermal.WARN] or g.throttled
        if cfg.overlay == "always" or (cfg.overlay == "hot" and hot):
            level = thermal.WARN if (g.state == thermal.OK and g.throttled) else g.state
            self.overlay.update_view(overlay.describe(g.reading, g.state, g.throttled, g.cur_max), level)
        else:
            self.overlay.hide()

    def on_close(self):
        if self.settings.get("background") and self.tray is not None:
            self.hide_to_tray()
            return
        g = self.guard
        temp = (g.reading or {}).get("cpu")
        if g.throttled and temp is not None and temp >= self.cfg.warn:
            if not messagebox.askyesno(APP_NAME, "O PC ainda está quente e estou limitando o clock.\n"
                                                 "Se fechar, o clock volta ao normal e ele pode esquentar de novo.\n\n"
                                                 "Fechar mesmo assim?"):
                return
        self.shutdown()

    def shutdown(self):
        """Devolve o clock original, para o sensor e fecha."""
        try:
            self.guard.restore()
            self.sensor.stop()
            if self.tray:
                self.tray.stop()
        finally:
            self.destroy()

    # --- modo segundo plano (bandeja)
    def save_settings(self):
        settings.save(self.settings)

    def set_background(self, on):
        """Liga/desliga o ícone da bandeja e a conferência silenciosa. -> False se não deu pra ligar."""
        if self._quiet_after is not None:
            self.after_cancel(self._quiet_after)
            self._quiet_after = None
        if on:
            try:
                self.tray = Tray(self, resource("icon.png"), APP_NAME, self.show_from_tray, self.scan_now, self.shutdown)
                self.tray.start()
            except Exception:
                self.tray = None
                return False
            self.settings["background"] = True
            self._quiet_after = self.after(60_000, self._quiet_loop)
        else:
            self.settings["background"] = False
            if self.tray:
                self.tray.stop()
                self.tray = None
        self.save_settings()
        return True

    def hide_to_tray(self):
        self.withdraw()
        self._hidden = True
        if self.tray and not self.settings.get("hide_tip"):
            self.settings["hide_tip"] = True
            self.save_settings()
            self.tray.notify(APP_NAME, "Continuo aqui na bandeja, conferindo o PC em silêncio.")

    def show_from_tray(self):
        self._hidden = False
        self.deiconify()
        self.lift()
        self.focus_force()

    def _quiet_loop(self):
        if not self.settings.get("background") or self.tray is None:
            return
        self._quiet_scan()
        minutes = max(5, int(self.settings.get("scan_minutes", 60)))
        self._quiet_after = self.after(minutes * 60_000, self._quiet_loop)

    def scan_now(self):
        self._quiet_scan(force=True)

    def _quiet_scan(self, force=False):
        def done(d):
            msgs = []
            if d["free"] / d["total"] < 0.15:
                msgs.append(f"Só {bk.fmt_size(d['free'])} livres no C:.")
            if d.get("junk", 0) > 2 * 1024 ** 3:
                msgs.append(f"Dá pra limpar {bk.fmt_size(d['junk'])} de lixo seguro.")
            now = time.time()
            if msgs and (force or now - self.settings.get("last_notice", 0) > 12 * 3600):
                self.settings["last_notice"] = now
                self.save_settings()
                if self.tray:
                    self.tray.notify(APP_NAME, " ".join(msgs) + " Abra o programa para limpar.")
            elif force and self.tray:
                self.tray.notify(APP_NAME, "Tudo certo por aqui. Nada importante para limpar.")

        self.bg(bk.quick_summary, done, quiet=True)

    # --- atualização pelo GitHub
    def check_update(self):
        def done(up):
            if up is None:
                return
            self.update_info = up
            self.pages["home"].show_update(up)
            if self._hidden and self.tray:
                self.tray.notify(APP_NAME, f"Versão {up.version} disponível. Abra o programa para atualizar.")

        self.bg(updater.check, done, quiet=True)
        if self.update_info is None:
            self.after(6 * 3600 * 1000, self.check_update)

    def start_update(self):
        up = self.update_info
        if up is None:
            return
        if not updater.can_self_update():
            webbrowser.open(f"https://github.com/{REPO}/releases/latest")
            return
        if not messagebox.askyesno(APP_NAME, f"Baixar a versão {up.version} ({bk.fmt_size(up.size)}) e reiniciar o programa?\n\n"
                                             "Se o vigia de temperatura estiver limitando o clock, ele devolve o clock "
                                             "ao normal ao fechar."):
            return

        def work():
            return updater.download(up, lambda f: self.post(lambda f=f: self.progress(f, "Baixando atualização…")))

        def done(path):
            self.progress(None)
            updater.apply(path)
            self.shutdown()

        self.bg(work, done, label="Baixando atualização…")

    # --- barra de atividade
    def progress(self, frac, text=None):
        """Barra com porcentagem (frac de 0 a 1). progress(None) volta ao normal."""
        self._prog = None if frac is None else (frac, text)
        self._status_refresh()

    def _status_refresh(self):
        if self._prog is not None:
            frac, text = self._prog
            if self._status_mode != "det":
                self.status_bar.stop()
                self.status_bar.configure(mode="determinate")
                self._status_mode = "det"
            self.status_bar.set(frac)
            self.status_lbl.configure(text=f"{text or 'Trabalhando…'}  {frac * 100:.0f}%")
        elif self._busy > 0:
            if self._status_mode != "ind":
                self.status_bar.configure(mode="indeterminate")
                self.status_bar.start()
                self._status_mode = "ind"
            self.status_lbl.configure(text=self._busy_label)
        else:
            if self._status_mode is not None:
                self.status_bar.stop()
                self.status_lbl.pack_forget()
                self.status_bar.pack_forget()
                self._status_mode = None
            return
        self.status_lbl.pack(side="left")
        self.status_bar.pack(side="right")

    def show(self, key):
        for k, p in self.pages.items():
            p.pack_forget()
            self.nav[k].configure(fg_color="transparent")
        self.nav[key].configure(fg_color=ACCENT)
        self.current = key
        self.sensor_sync()
        self.pages[key].pack(fill="both", expand=True)
        self.pages[key].on_show()

    # trabalho em segundo plano -> resultado volta para a thread da interface
    def post(self, fn):
        self.q.put(fn)

    def _pump(self):
        # reagenda primeiro: um aviso (messagebox) aberto dentro de um callback não pode parar a fila
        self.after(500 if self._hidden else 80, self._pump)    # escondido na bandeja: quase não faz nada
        try:
            while True:
                self.q.get_nowait()()
        except queue.Empty:
            pass
        except Exception as e:
            print("erro na interface:", e)

    def bg(self, work, done=None, label=None, quiet=False):
        """Roda `work` numa thread e entrega o resultado a `done` na thread da interface.

        Enquanto roda, a barra de atividade fica visível (a não ser com quiet=True, para tarefas de fundo).
        """
        if not quiet:
            self._busy += 1
            self._busy_label = label or "Trabalhando…"
            self._status_refresh()

        def finish():
            if not quiet:
                self._busy -= 1
                self._status_refresh()

        def run():
            try:
                res = work()
            except Exception as e:
                self.post(finish)
                self.post(lambda: self.progress(None))
                self.post(lambda: messagebox.showerror(APP_NAME, f"Deu ruim: {e}"))
                return
            self.post(finish)
            if done:
                self.post(lambda: done(res))

        threading.Thread(target=run, daemon=True).start()


def selftest(out_path):
    """Roda os comandos de conserto sem janela e grava o resultado (para depurar o .exe)."""
    import health
    import traceback
    res = []

    def run():
        try:
            res.append(("dns", list(health.flush_dns())))
            res.append(("ps", bk.ps("'ok'").strip()))
            res.append(("dism", list(bk.component_cleanup())[:3]))
            import pystray
            import system
            from PIL import Image
            pystray.Icon("teste", Image.new("RGB", (16, 16)))
            res.append(("psutil", len(system.process_groups()) > 10))
            res.append(("updater", updater.check()))
            res.append(("settings", sorted(settings.load())))
        except BaseException:
            res.append(("erro", traceback.format_exc()))

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(30)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(("TRAVOU\n" if t.is_alive() else "terminou\n") + repr(res))


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2 and sys.argv[1] == "--selftest":
        selftest(sys.argv[2])
    elif not single.acquire(wait=12 if "--elevated" in sys.argv else 0):
        single.focus_existing(APP_NAME)      # já tem uma janela aberta: traz ela pra frente
    else:
        App().mainloop()
