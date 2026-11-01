"""Páginas: Inicialização, Saúde e Desempenho."""
from tkinter import messagebox

import customtkinter as ctk

import backend as bk
import cpu
import health
import startup
import system
import tweaks
from page_system import SystemSection
from ui_common import *
from ui_table import SWITCH_OFF, SWITCH_ON, DataTable

ADVICE_BADGE = {"off": ("PODE DESLIGAR", GREEN), "keep": ("MANTENHA", BLUE), "?": ("DEPENDE", AMBER)}
SECTIONS = {
    "run": "📋 Programas que abrem com o Windows (o Gerenciador de Tarefas também mostra)",
    "task": "🕵 Tarefas agendadas — o Gerenciador de Tarefas NÃO mostra",
    "service": "⚙ Serviços — o Gerenciador de Tarefas NÃO mostra (só na aba Serviços)",
}


def section(parent, text):
    ctk.CTkLabel(parent, text=text, font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=8, pady=(16, 4))


ADVICE_RANK = {"off": 0, "?": 1, "keep": 2}
ADVICE_KEY = {"off": "off", "keep": "keep", "?": "ask"}
# cor da linha por dica: (ligado, desligado — mais apagado)
ADVICE_COLOR = {"off": (GREEN, "#7fa18c"), "keep": ("#3b82f6", "#8196b8"), "ask": (AMBER, "#a99c6e")}
START_HINT = "Clique num item para ver os detalhes. Clique em “● ligado” ou “○ desligado” para ligar ou desligar."


def _group_of(it):
    return "run" if it.kind in ("run", "folder") else it.kind


def _split_title(title):
    """'📋 Programas (explicação)' -> ('📋 Programas', 'explicação'), pra caber nas colunas da tabela."""
    main, sep, hint = title.partition(" — ")
    if not sep:
        main, sep, hint = title.partition(" (")
        hint = hint.rstrip(")")
    return main, hint


def _one_line(text):
    return " ".join(str(text).split())


class _StartupTable(DataTable):
    def _col_at(self, x):
        # com tree=True o DataTable._col_at erra uma coluna: '#0' é a árvore e '#1' já é a 1ª coluna de dados
        try:
            n = int(self.tree.identify_column(x).lstrip("#")) - 1
        except ValueError:
            return None
        return self._ids[n] if 0 <= n < len(self._ids) else None


# ----------------------------------------------------------------- Inicialização
class StartupPage(Page):
    def __init__(self, app):
        super().__init__(app, "Inicialização",
                         "Tudo que liga junto com o Windows, inclusive o que o Gerenciador de Tarefas esconde: "
                         "tarefas agendadas e serviços. Menos coisa ligando = PC liga mais rápido.")
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=24)
        ctk.CTkButton(bar, text="🔄 Atualizar", width=110, command=self.reload).pack(side="left")
        self.count = ctk.CTkLabel(bar, text="", text_color=MUTED)
        self.count.pack(side="left", padx=12)
        ctk.CTkButton(bar, text="Desligar os recomendados", width=210, fg_color=ACCENT, hover_color=ACCENT_H,
                      command=self.disable_recommended).pack(side="right")
        if not bk.is_admin():
            ctk.CTkLabel(self, text="⚠ Sem administrador, só dá pra mexer nos itens do seu usuário. "
                                    "Tarefas e serviços precisam de admin.", text_color=YELLOW).pack(anchor="w", padx=24)
        # detalhes da linha escolhida (embaixo, altura fixa pra tabela não pular quando o texto muda)
        box = ctk.CTkFrame(self, fg_color=CARD, corner_radius=8, height=118)
        box.pack(side="bottom", fill="x", padx=24, pady=(0, 12))
        box.pack_propagate(False)
        self.detail = ctk.CTkLabel(box, text=START_HINT, anchor="nw", justify="left", wraplength=720,
                                   text_color=MUTED, font=("Segoe UI", 12))
        self.detail.pack(fill="both", expand=True, padx=12, pady=8)
        self.table = _StartupTable(self, [
            {"id": "state", "text": "Estado", "width": 110, "toggle": True},
            {"id": "name", "text": "Nome", "width": 300, "stretch": True},
            {"id": "advice", "text": "Dica", "width": 125},
            {"id": "where", "text": "Onde", "width": 320, "minwidth": 160, "stretch": True},
        ], tree=True, selectmode="browse", on_toggle=self._on_toggle, on_select=self._on_select)
        self.table.pack(fill="both", expand=True, padx=24, pady=(8, 8))
        for key, (on, dim) in ADVICE_COLOR.items():
            self.table.tag(f"adv_{key}", foreground=on)
            self.table.tag(f"adv_{key}_dim", foreground=dim)
        self.table.tag("group", foreground=ACCENT, bold=True)
        self.items = []
        self.byid = {}          # iid da linha -> item
        self.iid_of = {}        # id(item) -> iid da linha
        self.groups = {}        # iid da seção -> chave em SECTIONS
        self.busy = set()       # id(item) com mudança em andamento (ignora clique repetido)

    def on_show(self):
        if not self.loaded:
            self.loaded = True
            self.reload()

    def reload(self):
        self.table.clear()
        self.items, self.byid, self.iid_of, self.groups = [], {}, {}, {}
        self.count.configure(text="")
        self.detail.configure(text=START_HINT)
        self.table.message("Procurando… (leva alguns segundos)")
        self.app.bg(startup.list_startup, self.populate)

    def populate(self, items):
        t = self.table
        t.clear()
        self.items, self.byid, self.iid_of, self.groups = items, {}, {}, {}
        self.detail.configure(text=START_HINT)
        bygroup = {}
        for it in items:
            bygroup.setdefault(_group_of(it), []).append(it)
        order = list(SECTIONS)
        n = 0
        for grp in sorted(bygroup, key=lambda g: order.index(g) if g in order else len(order)):
            members = bygroup[grp]
            main, hint = _split_title(SECTIONS.get(grp, grp))
            gid = t.add(["", main, f"{len(members)} item" if len(members) == 1 else f"{len(members)} itens", hint],
                        iid=f"grp_{grp}", tags=("group",))
            self.groups[gid] = grp
            for it in members:
                label = ADVICE_BADGE.get(it.advice, ADVICE_BADGE["?"])[0]
                where = _one_line(it.where) + (f"  •  {shorten(_one_line(it.command), 70)}" if it.command else "")
                iid = t.add([SWITCH_ON if it.enabled else SWITCH_OFF, _one_line(it.name), label, where],
                            iid=f"it{n}", parent=gid, tags=(self._adv_tag(it, it.enabled),),
                            raw={"advice": ADVICE_RANK.get(it.advice, 1)})
                self.byid[iid] = it
                self.iid_of[id(it)] = iid
                n += 1
        t.restripe()
        if not items:
            t.message("Nada encontrado.")
        self.update_count()

    def update_count(self):
        on = sum(1 for i in self.items if i.enabled)
        self.count.configure(text=f"{on} ligados de {len(self.items)}")

    # ---------------------------------------------------------------- linhas
    @staticmethod
    def _adv_tag(it, enabled):
        return "adv_" + ADVICE_KEY.get(it.advice, "ask") + ("" if enabled else "_dim")

    def _paint(self, it, enabled):
        """Põe a linha do item no estado `enabled` (só essa linha muda, nada é recriado)."""
        iid = self.iid_of.get(id(it))
        if iid is None or not self.table.has(iid):
            return
        zebra = [x for x in self.table.tree.item(iid, "tags") if x in ("odd", "even")]
        self.table.update(iid, state=SWITCH_ON if enabled else SWITCH_OFF, tags=(*zebra, self._adv_tag(it, enabled)))

    def _on_select(self, sel):
        iid = sel[0] if sel else None
        it = self.byid.get(iid)
        if it is not None:
            cmd = shorten(_one_line(it.command), 200) if it.command else "—"
            self.detail.configure(text=f"{it.name}\n{it.note}\nOnde: {it.where}\nComando: {cmd}")
        elif iid in self.groups:
            n = len(self.table.rows(iid))
            self.detail.configure(text=f"{SECTIONS.get(self.groups[iid], '')}\n{n} " + ("item" if n == 1 else "itens"))
        else:
            self.detail.configure(text=START_HINT)

    def _on_toggle(self, iid, col):
        it = self.byid.get(iid)
        if it is None:          # clique numa linha de seção
            return
        self.table.set_sel([iid])
        self.toggle(it)

    def toggle(self, it):
        if id(it) in self.busy:
            return
        want = not it.enabled
        if it.admin and not bk.is_admin():
            messagebox.showinfo(APP_NAME, "Esse item precisa de administrador. Volte no Início e clique em "
                                          "'Reabrir como administrador'.")
            return
        if not want and it.advice == "keep" and not messagebox.askyesno(
                APP_NAME, f"'{it.name}' parece importante.\n\n{it.note}\n\nDesligar mesmo assim?"):
            return
        self.busy.add(id(it))
        self._paint(it, want)           # já mostra o novo estado; volta se falhar

        def done(res):
            self.busy.discard(id(it))
            ok, msg = res
            if ok:
                it.enabled = want
                self.update_count()
            else:
                self._paint(it, it.enabled)
                messagebox.showerror(APP_NAME, f"Não consegui mudar: {msg}")

        def work():
            try:
                return startup.set_enabled(it, want)
            except Exception as e:        # qualquer erro vira "não consegui", senão o item ficaria travado
                return False, str(e)

        self.app.bg(work, done)

    def disable_recommended(self):
        targets = [i for i in self.items if i.advice == "off" and i.enabled and (bk.is_admin() or not i.admin)]
        if not targets:
            messagebox.showinfo(APP_NAME, "Nada recomendado para desligar agora.")
            return
        names = "\n".join("• " + shorten(t.name, 50) for t in targets[:12]) + ("\n…" if len(targets) > 12 else "")
        if not messagebox.askyesno(APP_NAME, f"Desligar {len(targets)} item(ns)?\n\n{names}\n\n"
                                             "Dá pra religar depois pelo interruptor."):
            return

        def work():
            return [(t, startup.set_enabled(t, False)) for t in targets]

        def done(results):
            bad = [t.name for t, (ok, _) in results if not ok]
            if bad:
                messagebox.showwarning(APP_NAME, "Não consegui desligar:\n" + "\n".join(bad[:10]))
            self.reload()

        self.app.bg(work, done)


# ------------------------------------------------------------------------ Saúde
LEVEL_TEXT = {"ok": "SAUDÁVEL", "care": "ATENÇÃO", "bad": "RUIM"}
DIAG_STYLE = {"ok": ("✔", GREEN), "care": ("⚠", YELLOW), "bad": ("✖", "#f87171")}

REPAIRS = [
    ("🛠 Verificar arquivos do sistema (SFC)", health.sfc, True,
     "Procura arquivos do Windows corrompidos e conserta. Leva de 5 a 15 minutos."),
    ("🧰 Reparar a imagem do Windows (DISM)", health.dism_restore, True,
     "Baixa peças boas do Windows Update. Precisa de internet. Rode antes do SFC se ele falhar."),
    ("💽 Verificar o disco (CHKDSK)", health.chkdsk_scan, True,
     "Procura erros no sistema de arquivos sem precisar reiniciar."),
    ("🌐 Limpar cache de DNS", health.flush_dns, False,
     "Ajuda quando sites não abrem mesmo com a internet funcionando."),
]


class HealthPage(Page):
    def __init__(self, app):
        super().__init__(app, "Saúde", "Veja se o disco está bom, ache problemas no Windows e conserte.")
        self.body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=14, pady=(0, 10))

        section(self.body, "💽 Saúde do disco")
        self.disk_box = ctk.CTkFrame(self.body, fg_color="transparent")
        self.disk_box.pack(fill="x")

        section(self.body, "🩺 Diagnóstico geral")
        ctk.CTkButton(self.body, text="Rodar de novo", width=130, command=self.run_diag).pack(anchor="w", padx=8)
        self.diag_box = ctk.CTkFrame(self.body, fg_color="transparent")
        self.diag_box.pack(fill="x", pady=4)

        section(self.body, "🔄 Atualizações e drivers (só avisa, não instala nada)")
        self.upd_btn = ctk.CTkButton(self.body, text="Verificar agora", width=150, command=self.check_updates)
        self.upd_btn.pack(anchor="w", padx=8)
        self.upd_box = ctk.CTkFrame(self.body, fg_color="transparent")
        self.upd_box.pack(fill="x", pady=4)

        section(self.body, "🔧 Consertar o Windows (precisa de administrador)")
        self.rep_btns = []
        for title, fn, need_admin, desc in REPAIRS:
            row = ctk.CTkFrame(self.body, fg_color=CARD, corner_radius=8)
            row.pack(fill="x", pady=3, padx=4)
            b = ctk.CTkButton(row, text=title, width=300, anchor="w",
                              command=lambda fn=fn, a=need_admin, t=title: self.repair(fn, a, t))
            b.pack(side="left", padx=10, pady=10)
            self.rep_btns.append(b)
            ctk.CTkLabel(row, text=desc, text_color=MUTED, wraplength=380, justify="left").pack(side="left", padx=8)
        self.out = make_log(self.body, 170)
        self.out.pack(fill="x", padx=4, pady=8)

    def on_show(self):
        if not self.loaded:
            self.loaded = True
            clear(self.disk_box, "Lendo o disco…")
            self.app.bg(health.disk_health, self.show_disks)
            self.run_diag()

    def show_disks(self, disks):
        clear(self.disk_box)
        if not disks:
            ctk.CTkLabel(self.disk_box, text="Não consegui ler os discos. Tente reabrir como administrador.",
                         text_color=MUTED).pack(pady=10)
        for d in disks:
            card = ctk.CTkFrame(self.disk_box, fg_color=CARD, corner_radius=10)
            card.pack(fill="x", pady=3, padx=4)
            badge(card, LEVEL_TEXT[d.level], LEVEL_COLOR[d.level]).pack(side="left", padx=12, pady=12)
            txt = ctk.CTkFrame(card, fg_color="transparent")
            txt.pack(side="left", fill="x", expand=True, pady=8)
            ctk.CTkLabel(txt, text=d.name, font=("Segoe UI", 14, "bold"), anchor="w").pack(anchor="w")
            ctk.CTkLabel(txt, text=d.headline, anchor="w").pack(anchor="w")
            ctk.CTkLabel(txt, text="  •  ".join(d.details), anchor="w", text_color=MUTED,
                         font=("Segoe UI", 11), wraplength=620, justify="left").pack(anchor="w")

    def run_diag(self):
        clear(self.diag_box, "Verificando… (uns segundos)")
        self.app.bg(health.diagnose, self.show_diag)

    def show_diag(self, rows):
        clear(self.diag_box)
        for level, text in rows:
            icon, color = DIAG_STYLE[level]
            ctk.CTkLabel(self.diag_box, text=f"{icon}  {text}", anchor="w", text_color=color,
                         wraplength=720, justify="left").pack(anchor="w", padx=12, pady=1)

    def check_updates(self):
        self.upd_btn.configure(state="disabled", text="Verificando… (até 1 min)")
        clear(self.upd_box, "Procurando atualizações e drivers…")
        self.app.bg(system.check_updates_and_drivers, self.show_updates)

    def show_updates(self, res):
        self.upd_btn.configure(state="normal", text="Verificar de novo")
        clear(self.upd_box)

        def line(level, text):
            icon, color = DIAG_STYLE[level]
            ctk.CTkLabel(self.upd_box, text=f"{icon}  {text}", anchor="w", text_color=color, wraplength=720,
                         justify="left").pack(anchor="w", padx=12, pady=1)

        if res["error"]:
            line("care", "Não consegui consultar o Windows Update: " + res["error"])
        elif not res["updates"]:
            line("ok", "Nenhuma atualização pendente.")
        else:
            line("care", f"{len(res['updates'])} atualização(ões) pendente(s). Instale pelo Windows Update:")
            for u in res["updates"]:
                kind = "driver" if u.get("Driver") else "Windows"
                extra = " • pede reinicialização" if u.get("Reboot") else ""
                line("care", f"   {u['Title']}  ({kind}, {bk.fmt_size(u.get('Size') or 0)}{extra})")
        if res["drivers"]:
            line("care", f"{len(res['drivers'])} driver(s) com mais de 3 anos (estimativa pela data; "
                         "procure no site do fabricante):")
            for d in res["drivers"]:
                line("care", f"   {d['DeviceName']}  —  {d['Manufacturer']}, versão {d['DriverVersion']}, de {d['Date']}")
        else:
            line("ok", "Nenhum driver de vídeo, rede, áudio ou bluetooth com mais de 3 anos.")

    def repair(self, fn, need_admin, title):
        if need_admin and not bk.is_admin():
            messagebox.showinfo(APP_NAME, "Isso precisa de administrador. Volte no Início e clique em "
                                          "'Reabrir como administrador'.")
            return
        for b in self.rep_btns:
            b.configure(state="disabled")
        log(self.out, f"▶ {title}… não feche o programa.")

        def enable():
            for b in self.rep_btns:
                b.configure(state="normal")

        stream_to_log(self.app, self.out, fn, enable)


# ------------------------------------------------------------------ Desempenho
MINUTES = {"5 min": 5, "10 min": 10, "15 min": 15, "30 min": 30, "1 hora": 60, "Nunca": 0}
QUICK_PLANS = [("🚀 Desempenho máximo", "ultimate"), ("⚡ Alto desempenho", "high"),
               ("⚖ Equilibrado", "balanced"), ("🔋 Economia", "saver")]


class PerfPage(Page):
    def __init__(self, app):
        super().__init__(app, "Desempenho", "Plano de energia e ajustes do Windows. Tudo dá pra desfazer.")
        self.body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=14, pady=(0, 10))

        section(self.body, "🔋 Plano de energia")
        self.hint = ctk.CTkLabel(self.body, text="", text_color=MUTED, wraplength=720, justify="left")
        self.hint.pack(anchor="w", padx=8)
        quick = ctk.CTkFrame(self.body, fg_color="transparent")
        quick.pack(fill="x", padx=8, pady=6)
        for label, kind in QUICK_PLANS:
            ctk.CTkButton(quick, text=label, width=160, command=lambda k=kind: self.use_plan(k)).pack(side="left", padx=(0, 6))
        self.plan_box = ctk.CTkFrame(self.body, fg_color="transparent")
        self.plan_box.pack(fill="x")

        tm = ctk.CTkFrame(self.body, fg_color=CARD, corner_radius=8)
        tm.pack(fill="x", padx=4, pady=6)
        ctk.CTkLabel(tm, text="Tela desliga após").pack(side="left", padx=(12, 6), pady=10)
        self.mon = ctk.CTkOptionMenu(tm, values=list(MINUTES), width=90)
        self.mon.set("10 min")
        self.mon.pack(side="left")
        ctk.CTkLabel(tm, text="PC dorme após").pack(side="left", padx=(16, 6))
        self.slp = ctk.CTkOptionMenu(tm, values=list(MINUTES), width=90)
        self.slp.set("30 min")
        self.slp.pack(side="left")
        ctk.CTkButton(tm, text="Aplicar", width=90, fg_color=ACCENT, hover_color=ACCENT_H,
                      command=self.apply_timeouts).pack(side="right", padx=12)

        self.build_clock()

        section(self.body, "🛠 Ajustes do Windows")
        ctk.CTkLabel(self.body, text="Ligado = ajuste aplicado. Desligue o interruptor para voltar ao padrão do Windows.",
                     text_color=MUTED).pack(anchor="w", padx=8)
        self.tweak_box = ctk.CTkFrame(self.body, fg_color="transparent")
        self.tweak_box.pack(fill="x")

        self.sysec = SystemSection(self.body, app)

    def on_show(self):
        if self.loaded:
            return
        self.loaded = True
        self.hint.configure(text=("Notebook: use Equilibrado na bateria. Alto desempenho gasta bateria rápido."
                                  if health.has_battery() else
                                  "PC de mesa: Alto desempenho não gasta bateria e deixa o PC mais ágil."))
        self.load_plans()
        self.build_tweaks()
        self.sysec.load()
        self.load_clock()
        self.tick()

    # --- controle de clock
    def build_clock(self):
        section(self.body, "🧠 Controle de clock da CPU")
        self.cpu_lbl = ctk.CTkLabel(self.body, text="Lendo a CPU…", text_color=MUTED)
        self.cpu_lbl.pack(anchor="w", padx=8)
        self.live_lbl = ctk.CTkLabel(self.body, text="⏱ —", font=("Segoe UI", 22, "bold"), text_color=GREEN)
        self.live_lbl.pack(anchor="w", padx=8, pady=(2, 6))

        pre = ctk.CTkFrame(self.body, fg_color="transparent")
        pre.pack(fill="x", padx=8)
        for name in cpu.PRESETS:
            ctk.CTkButton(pre, text=name, width=170, command=lambda n=name: self.clock_preset(n)).pack(side="left", padx=(0, 6))

        card = ctk.CTkFrame(self.body, fg_color=CARD, corner_radius=8)
        card.pack(fill="x", padx=4, pady=8)
        self.max_val = ctk.IntVar(value=100)
        self.min_val = ctk.IntVar(value=5)
        for attr, var, lo, cmd in (("max_lbl", self.max_val, 20, self.on_max), ("min_lbl", self.min_val, 0, self.on_min)):
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=6)
            lbl = ctk.CTkLabel(row, text="", width=230, anchor="w")
            lbl.pack(side="left")
            setattr(self, attr, lbl)
            ctk.CTkSlider(row, from_=lo, to=100, number_of_steps=100 - lo, variable=var, command=cmd,
                          progress_color=ACCENT, width=360).pack(side="left", padx=8)
        self.on_max()
        self.on_min()

        self.boost_menu = self.freq_menu = None
        self.extra_row = ctk.CTkFrame(card, fg_color="transparent")
        self.extra_row.pack(fill="x", padx=12, pady=(0, 6))
        self.extra_lbl = ctk.CTkLabel(self.extra_row, text="", text_color=MUTED, justify="left")
        self.extra_lbl.pack(anchor="w")

        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.pack(fill="x", padx=12, pady=(2, 10))
        ctk.CTkButton(btns, text="Aplicar no plano ativo", width=190, fg_color=ACCENT, hover_color=ACCENT_H,
                      command=self.clock_apply).pack(side="left")
        ctk.CTkButton(btns, text="Voltar ao padrão", width=140, fg_color="gray40", hover_color="gray30",
                      command=lambda: self.clock_preset("⚖ Normal")).pack(side="left", padx=8)
        ctk.CTkLabel(self.body, text="Máximo abaixo de 100% desliga o turbo: a CPU fica mais fria e silenciosa, "
                                     "mas mais lenta. Vale pro plano ativo. Alguns notebooks ignoram.",
                     text_color=MUTED, wraplength=720, justify="left").pack(anchor="w", padx=8)
        self._live_busy = False
        self._boost_ok = self._freq_ok = False

    def on_max(self, _=None):
        v = int(self.max_val.get())
        if v < int(self.min_val.get()):
            self.min_val.set(v)
            self.on_min()
        self.max_lbl.configure(text=f"Clock máximo: {v}%")

    def on_min(self, _=None):
        v = int(self.min_val.get())
        if v > int(self.max_val.get()):
            self.max_val.set(v)
            self.max_lbl.configure(text=f"Clock máximo: {v}%")
        self.min_lbl.configure(text=f"Clock mínimo: {v}%")

    def load_clock(self):
        def work():
            return cpu.info(), cpu.snapshot_unlocked()

        def done(res):
            (name, base, threads), snap = res
            self.cpu_lbl.configure(text=f"{name}  •  clock base {base} MHz  •  {threads} threads")
            if snap["max"] is not None:
                self.max_val.set(max(20, snap["max"]))
                self.min_val.set(snap["min"] if snap["min"] is not None else 5)
                self.on_max()
                self.on_min()
            self._boost_ok, self._freq_ok = snap["boost"] is not None, snap["freq"] is not None
            row = ctk.CTkFrame(self.extra_row, fg_color="transparent", height=0)
            if self._boost_ok or self._freq_ok:
                row.pack(anchor="w", pady=(4, 0))
            if self._boost_ok:
                ctk.CTkLabel(row, text="Turbo:").pack(side="left")
                inv = {v: k for k, v in cpu.BOOST_MODES.items()}
                self.boost_menu = ctk.CTkOptionMenu(row, values=list(cpu.BOOST_MODES), width=190)
                self.boost_menu.set(inv.get(snap["boost"], "Normal"))
                self.boost_menu.pack(side="left", padx=(6, 14))
            if self._freq_ok:
                ctk.CTkLabel(row, text="Limite:").pack(side="left")
                self.freq_menu = ctk.CTkOptionMenu(row, width=130, values=[
                    "Sem limite", "1500 MHz", "2000 MHz", "2500 MHz", "3000 MHz", "3500 MHz", "4000 MHz"])
                self.freq_menu.set("Sem limite" if not snap["freq"] else f"{snap['freq']} MHz")
                self.freq_menu.pack(side="left", padx=6)
            if not (self._boost_ok and self._freq_ok):
                self.extra_lbl.configure(text="Turbo e limite em MHz estão escondidos neste PC. "
                                              + ("Não deu pra liberar." if bk.is_admin()
                                                 else "Reabra como administrador para liberar."))

        self.app.bg(work, done)

    def tick(self):
        if self.winfo_ismapped() and not self._live_busy:
            self._live_busy = True

            def safe():
                try:
                    return cpu.live()
                except Exception:
                    return None

            def done(r):
                self._live_busy = False
                if r:
                    self.live_lbl.configure(text=f"⏱ {r[0] / 1000:.2f} GHz   •   CPU em uso {r[1]:.0f}%")

            self.app.bg(safe, done)
        self.after(3000, self.tick)

    def clock_preset(self, name):
        mn, mx, boost, mhz = cpu.PRESETS[name]
        self.min_val.set(mn)
        self.max_val.set(mx)
        self.on_max()
        self.on_min()
        if self._boost_ok:
            inv = {v: k for k, v in cpu.BOOST_MODES.items()}
            self.boost_menu.set(inv[boost])
        if self._freq_ok:
            self.freq_menu.set("Sem limite")
        self.clock_apply()

    def clock_apply(self):
        mn, mx = int(self.min_val.get()), int(self.max_val.get())
        boost = cpu.BOOST_MODES[self.boost_menu.get()] if self._boost_ok else None
        mhz = None
        if self._freq_ok:
            f = self.freq_menu.get()
            mhz = 0 if f == "Sem limite" else int(f.split()[0])
        self.app.bg(lambda: cpu.apply(mn, mx, boost, mhz), lambda _: None)

    def load_plans(self):
        self.app.bg(health.power_plans, self.show_plans)

    def show_plans(self, plans):
        clear(self.plan_box)
        for guid, name, active in plans:
            row = ctk.CTkFrame(self.plan_box, fg_color=CARD, corner_radius=8)
            row.pack(fill="x", pady=2, padx=4)
            ctk.CTkLabel(row, text=name, font=("Segoe UI", 13, "bold")).pack(side="left", padx=12, pady=8)
            if active:
                badge(row, "ATIVO", GREEN, 70).pack(side="right", padx=12)
            else:
                ctk.CTkButton(row, text="Ativar", width=80, fg_color="gray40", hover_color="gray30",
                              command=lambda g=guid: self.activate(g)).pack(side="right", padx=12)

    def activate(self, guid):
        self.app.bg(lambda: health.set_power_plan(guid), lambda ok: self.load_plans())

    def use_plan(self, kind):
        def work():
            guid = health.ensure_plan(kind)
            return bool(guid and health.set_power_plan(guid))

        def done(ok):
            if not ok:
                messagebox.showinfo(APP_NAME, "Seu PC não aceita esse plano de energia.")
            self.load_plans()

        self.app.bg(work, done)

    def apply_timeouts(self):
        m, s = MINUTES[self.mon.get()], MINUTES[self.slp.get()]
        self.app.bg(lambda: health.set_timeouts(m, s),
                    lambda _: messagebox.showinfo(APP_NAME, "Tempos aplicados no plano ativo."))

    def build_tweaks(self):
        for t in tweaks.make_tweaks():
            row = ctk.CTkFrame(self.tweak_box, fg_color=CARD, corner_radius=8)
            row.pack(fill="x", pady=2, padx=4)
            sw = ctk.CTkSwitch(row, text="", width=46, progress_color=ACCENT)
            sw.configure(command=lambda t=t, sw=sw: self.set_tweak(t, sw))
            try:
                if t.is_on():
                    sw.select()
            except Exception:
                sw.configure(state="disabled")
            sw.pack(side="left", padx=(12, 4), pady=10)
            txt = ctk.CTkFrame(row, fg_color="transparent")
            txt.pack(side="left", fill="x", expand=True, padx=6, pady=5)
            ctk.CTkLabel(txt, text=t.name, font=("Segoe UI", 13, "bold"), anchor="w").pack(anchor="w")
            ctk.CTkLabel(txt, text=t.desc, text_color=MUTED, anchor="w", wraplength=600, justify="left").pack(anchor="w")

    def set_tweak(self, t, sw):
        want = sw.get() == 1
        try:
            t.apply(want)
        except Exception as e:
            sw.deselect() if want else sw.select()
            messagebox.showerror(APP_NAME, f"Não consegui aplicar: {e}")
