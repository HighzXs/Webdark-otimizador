"""Ajustes de sistema com aviso, TRIM e a página de processos."""
from tkinter import messagebox

import customtkinter as ctk
import psutil

import backend as bk
import system
from ui_common import *
from ui_table import DataTable

_restore_done = False


def _ensure_restore():
    """Cria um ponto de restauração antes do primeiro ajuste de sistema da sessão."""
    global _restore_done
    if _restore_done:
        return ""
    ok, msg = bk.create_restore_point("Faxina Várzea - antes de ajustes de sistema")
    _restore_done = ok
    return msg


class SystemSection:
    """Bloco 'Ajustes de sistema' dentro da aba Desempenho."""

    def __init__(self, body, app):
        self.app = app
        self.kind = ""
        self.sw = {}
        self.loaded = False

        ctk.CTkLabel(body, text="🔧 Ajustes de sistema (mexem no Windows, com aviso)",
                     font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=8, pady=(16, 4))
        ctk.CTkLabel(body, text="Antes de aplicar, mostro o que muda, o que pode dar errado e como desfazer. "
                                "Precisa de administrador. Crio um ponto de restauração antes do primeiro ajuste.",
                     text_color=MUTED, wraplength=720, justify="left").pack(anchor="w", padx=8)
        for t in system.SYS_TWEAKS:
            row = ctk.CTkFrame(body, fg_color=CARD, corner_radius=8)
            row.pack(fill="x", pady=2, padx=4)
            sw = ctk.CTkSwitch(row, text="", width=46, progress_color=ACCENT, state="disabled",
                               command=lambda t=t: self.toggle(t))
            sw.pack(side="left", padx=(12, 4), pady=10)
            self.sw[t.key] = sw
            txt = ctk.CTkFrame(row, fg_color="transparent")
            txt.pack(side="left", fill="x", expand=True, padx=6, pady=5)
            head = ctk.CTkFrame(txt, fg_color="transparent")
            head.pack(anchor="w")
            ctk.CTkLabel(head, text=t.name, font=("Segoe UI", 13, "bold")).pack(side="left")
            badge(head, "CUIDADO", AMBER, 80).pack(side="left", padx=8)
            ctk.CTkLabel(txt, text=t.desc, text_color=MUTED, anchor="w", wraplength=600, justify="left").pack(anchor="w")

        trim = ctk.CTkFrame(body, fg_color=CARD, corner_radius=8)
        trim.pack(fill="x", pady=(8, 2), padx=4)
        ctk.CTkLabel(trim, text="💽 Otimizar unidades (TRIM)", font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=12, pady=(10, 0))
        self.trim_lbl = ctk.CTkLabel(trim, text="Verificando…", text_color=MUTED, anchor="w", wraplength=640, justify="left")
        self.trim_lbl.pack(anchor="w", padx=12)
        btns = ctk.CTkFrame(trim, fg_color="transparent")
        btns.pack(anchor="w", padx=12, pady=(6, 10))
        self.trim_btn = ctk.CTkButton(btns, text="Ativar TRIM", width=130, state="disabled", command=self.enable_trim)
        self.trim_btn.pack(side="left", padx=(0, 8))
        self.opt_btn = ctk.CTkButton(btns, text="Otimizar o C: agora", width=170, state="disabled", command=self.optimize)
        self.opt_btn.pack(side="left")
        self.out = make_log(body, 110)
        self.out.pack(fill="x", padx=4, pady=8)

    def load(self):
        if self.loaded:
            return
        self.loaded = True

        def fetch():
            return system.service_states(), system.system_disk_kind(), system.trim_status()

        self.app.bg(fetch, self.show)

    def show(self, res):
        states, self.kind, trim = res
        for t in system.SYS_TWEAKS:
            sw, on = self.sw[t.key], system.tweak_state(t, states)
            if on is None:
                sw.configure(state="disabled")
                continue
            sw.configure(state="normal")
            sw.select() if on else sw.deselect()
        kind = {"SSD": "SSD", "HDD": "HD"}.get(self.kind, "tipo de disco desconhecido")
        if trim is None:
            self.trim_lbl.configure(text=f"Disco do sistema: {kind}. Não consegui ler o estado do TRIM.")
        elif trim:
            self.trim_lbl.configure(text=f"Disco do sistema: {kind}. TRIM está ATIVO ✔")
        else:
            self.trim_lbl.configure(text=f"Disco do sistema: {kind}. TRIM está DESLIGADO. Em SSD isso deixa o disco mais lento com o tempo.",
                                    text_color=YELLOW)
        self.trim_btn.configure(state="normal" if trim is False else "disabled")
        self.opt_btn.configure(state="normal")

    def need_admin(self):
        if bk.is_admin():
            return False
        messagebox.showinfo(APP_NAME, "Isso precisa de administrador. Volte no Início e clique em "
                                      "'Reabrir como administrador'.")
        return True

    def toggle(self, t):
        sw = self.sw[t.key]
        want = sw.get() == 1

        def revert():
            sw.deselect() if want else sw.select()

        if self.need_admin():
            revert()
            return
        if want and not messagebox.askyesno(APP_NAME, system.warning_text(t, self.kind), icon="warning", default="no"):
            revert()
            return

        def work():
            note = _ensure_restore() if want else ""
            ok, msg = system.apply_tweak(t, want)
            return ok, msg, note

        def done(res):
            ok, msg, note = res
            if ok:
                log(self.out, f"✔ {t.name}: {'aplicado' if want else 'desfeito'}." + (f"  🛟 {note}" if note else ""))
            else:
                revert()
                messagebox.showerror(APP_NAME, f"Não consegui mudar: {msg}")

        self.app.bg(work, done)

    def enable_trim(self):
        if self.need_admin():
            return
        if not messagebox.askyesno(APP_NAME, "Ativar o TRIM do Windows?\n\nO TRIM avisa o SSD quais blocos não são mais "
                                             "usados. Só faz sentido em SSD e normalmente já vem ligado.\n"
                                             "⚠ Em HD ou disco virtual não adianta nada.\n"
                                             "↩ Dá pra desligar de novo com: fsutil behavior set DisableDeleteNotify 1"):
            return

        def done(ok):
            log(self.out, "✔ TRIM ativado." if ok else "✖ Não consegui ativar o TRIM.")
            self.loaded = False
            self.load()

        self.app.bg(system.enable_trim, done)

    def optimize(self):
        if self.need_admin():
            return
        if self.kind == "SSD":
            msg = "Vou rodar o TRIM no SSD (C:). É rápido e seguro."
        elif self.kind == "HDD":
            msg = ("Seu disco é um HD, então vou DESFRAGMENTAR o C:.\n\n⚠ Demora de minutos a horas, o PC fica lento "
                   "nesse tempo e você NÃO deve desligar nem fechar o programa até terminar.")
        else:
            msg = "Não sei se é SSD ou HD, então só vou ANALISAR o C: (não muda nada)."
        if not messagebox.askyesno(APP_NAME, msg + "\n\nContinuar?", default="no" if self.kind == "HDD" else "yes"):
            return
        self.opt_btn.configure(state="disabled")
        log(self.out, "▶ Otimizando o C:… não feche o programa.")
        stream_to_log(self.app, self.out, lambda: system.optimize_drive(self.kind),
                      lambda: self.opt_btn.configure(state="normal"))


# ---------------------------------------------------------------------- Processos
class ProcPage(Page):
    def __init__(self, app):
        super().__init__(app, "Processos", "Quem está pesando agora. Fechar um programa perde o que não foi salvo nele. "
                                           "Processos do Windows ficam trancados. Clique num programa e use Fechar.")
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=24)
        ctk.CTkLabel(bar, text="Ordenar por:").pack(side="left")
        self.sort = ctk.CTkSegmentedButton(bar, values=["RAM", "CPU"], command=lambda _=None: self.render())
        self.sort.set("RAM")
        self.sort.pack(side="left", padx=6)
        ctk.CTkButton(bar, text="🔄 Atualizar", width=100, command=self.refresh).pack(side="left", padx=6)
        self.auto = ctk.CTkSwitch(bar, text="Atualizar sozinho", progress_color=ACCENT)
        self.auto.select()
        self.auto.pack(side="left", padx=10)
        self.close_btn = ctk.CTkButton(bar, text="Fechar", width=96, state="disabled", fg_color=RED,
                                       hover_color=RED_H, command=self.close)
        self.close_btn.pack(side="right")
        self.summary = ctk.CTkLabel(self, text="", text_color=MUTED, anchor="w")
        self.summary.pack(fill="x", padx=26, pady=(4, 0))
        self.table = DataTable(self, [
            {"id": "name", "text": "Programa", "width": 380, "stretch": True},
            {"id": "ram", "text": "RAM", "width": 110, "anchor": "e"},
            {"id": "cpu", "text": "CPU", "width": 80, "anchor": "e"},
            {"id": "state", "text": "Estado", "width": 120},
        ], selectmode="browse", on_select=self._on_select)
        self.table.pack(fill="both", expand=True, padx=24, pady=(6, 14))
        self.table.message("Lendo processos…")
        self.groups = []
        self.rows = {}              # iid (nome em minúsculas) -> ProcGroup mostrado na linha
        self.busy = False
        self.ticking = False
        self.closing = False
        self.again = False          # pedido de nova leitura enquanto outra ainda estava rodando
        self.ready = False          # já chegou algum dado (some o "Lendo processos…")

    def on_show(self):
        if not self.ticking:
            self.ticking = True
            try:
                system.process_groups()       # 1ª leitura só prepara o cálculo de CPU
            except Exception as e:
                print("erro lendo processos:", e)
            self.after(1200, self.refresh)
            self.after(4000, self._tick)

    def _tick(self):
        self.after(4000, self._tick)
        if self.auto.get() == 1 and self.winfo_ismapped():
            self.refresh()

    def refresh(self, force=False):
        if self.busy:
            if force:
                self.again = True         # a leitura em andamento pode ser anterior ao que mudou: repete depois
            return
        self.busy = True
        self.app.bg(self._read, self._got, quiet=True)

    @staticmethod
    def _read():
        try:
            return system.process_groups()
        except Exception as e:           # falha pontual: tenta de novo no próximo ciclo, sem travar o busy
            print("erro ao ler processos:", e)
            return None

    def _got(self, groups):
        self.busy = False
        if groups is not None:
            self.groups = groups
            if not self.ready:
                self.ready = True
                self.table.message("")
            self.render()
        if self.again:
            self.again = False
            self.refresh()

    @staticmethod
    def _cells(g):
        return {"name": g.name + (f" ×{g.count}" if g.count > 1 else ""), "ram": bk.fmt_size(g.ram),
                "cpu": f"{g.cpu:.1f}%", "state": "🔒 Windows" if g.protected else ""}

    def render(self):
        vm = psutil.virtual_memory()
        self.summary.configure(text=f"RAM: {bk.fmt_size(vm.used)} de {bk.fmt_size(vm.total)} ({vm.percent:.0f}%)   •   "
                                    f"CPU: {psutil.cpu_percent(None):.0f}%   •   {sum(g.count for g in self.groups)} processos")
        key = (lambda g: g.cpu) if self.sort.get() == "CPU" else (lambda g: g.ram)
        top = sorted(self.groups, key=key, reverse=True)[:30]
        order = [g.name.lower() for g in top]
        keep = set(order)
        before = self.table.rows()
        # tudo no lugar: nada é apagado e refeito, então a lista não pisca e a seleção/rolagem ficam como estão
        self.table.remove(*[i for i in before if i not in keep])
        self.rows = {}
        for iid, g in zip(order, top):
            self.rows[iid] = g
            cells = self._cells(g)
            if self.table.has(iid):
                self.table.update(iid, **{c: v for c, v in cells.items() if str(self.table.cell(iid, c)) != v})
            else:
                self.table.add([cells["name"], cells["ram"], cells["cpu"], cells["state"]], iid=iid)
        self.table.set_order(order)
        if self.table.rows() != before:
            self.table.restripe()
        self._sync_btn()

    def _selected(self):
        sel = self.table.sel()
        return self.rows.get(sel[0]) if sel else None

    def _on_select(self, _sel=None):
        self._sync_btn()

    def _sync_btn(self):
        g = self._selected()
        ok = g is not None and not g.protected and not self.closing
        self.close_btn.configure(state="normal" if ok else "disabled")

    def close(self):
        g = self._selected()
        if g is None or g.protected or self.closing:
            return
        if not messagebox.askyesno(APP_NAME, f"Fechar {g.name} ({g.count} processo(s))?\n\n"
                                             "⚠ Tudo que não foi salvo nele será perdido.", icon="warning", default="no"):
            return
        self.closing = True
        self._sync_btn()

        def work():
            try:
                return system.close_group(g)
            except Exception as e:
                return 0, [str(e)]

        def done(res):
            closed, errors = res
            self.closing = False
            self._sync_btn()
            if errors:
                messagebox.showwarning(APP_NAME, "Não consegui fechar tudo:\n" + "\n".join(errors[:6]))
            self.refresh(force=True)

        self.app.bg(work, done)
