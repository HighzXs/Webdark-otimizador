"""Página Espaço: pastas, arquivos grandes (com risco), duplicados e downloads antigos.

Cada lista é uma DataTable (um widget só), nada de uma linha de widgets por item.
"""
import os
import threading
import time
from collections import Counter
from tkinter import messagebox

import customtkinter as ctk

import backend as bk
import risk
import system
from ui_common import *
from ui_table import CHECK_OFF, CHECK_ON, DataTable

FILTERS = {"Todos": None, "Seguros": risk.OK, "Cuidado": risk.CARE, "Perigo": risk.DANGER}
RANK = {risk.OK: 0, risk.CARE: 1, risk.DANGER: 2}
MAX_DIRS, MAX_DUPS = 300, 200
DUP_HINT = "Em cada grupo, uma cópia fica sem marca (a que sugiro manter)."
SEL_HINT = "Selecione uma linha para ver o caminho completo e o motivo."


def _resort(table):
    """Depois de mexer nas linhas: refaz a ordem escolhida no cabeçalho (ou só a zebra)."""
    col, rev = getattr(table, "_sort", (None, False))
    if col:
        table.sort_by(col, rev)
    else:
        table.restripe()


def _sync(table, entries):
    """Deixa a tabela com exatamente estas linhas [(iid, valores, tags, raw)], na ordem dada.

    Só apaga o que saiu, só cria o que é novo e só move o que mudou de lugar: não pisca nem perde a seleção.
    """
    want = {e[0] for e in entries}
    table.remove(*[i for i in table.rows() if i not in want])
    for iid, values, tags, raw in entries:
        if table.has(iid):
            table.update(iid, values=values, tags=tags, raw=raw)
        else:
            table.add(values, iid=iid, tags=tags, raw=raw)
    table.set_order([e[0] for e in entries])
    _resort(table)


def _date(mt):
    try:
        return time.strftime("%d/%m/%Y", time.localtime(mt))
    except (OverflowError, OSError, ValueError):
        return "?"


class RiskList:
    """Tabela de arquivos com aviso de risco + botões Mostrar/Lixeira + detalhe da seleção.

    Serve às abas 'Arquivos grandes' e 'Downloads antigos'. Os dados ficam na página (file_res / dl_res);
    aqui só se desenha a lista e se manda pra lixeira o que o usuário escolheu.
    """

    def __init__(self, page, parent, what, on_trashed, rel=None, empty="Nada aqui. 👍"):
        self.page, self.what, self.on_trashed, self.rel, self.empty = page, what, on_trashed, rel, empty
        self.rows = {}          # iid -> (tamanho, caminho, Risk)
        self.ids = {}           # caminho -> iid (fixo, pra atualizar sem recriar a linha)
        self._n = 0
        bottom = ctk.CTkFrame(parent, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", pady=(4, 0))
        self.trash_btn = ctk.CTkButton(bottom, text="🗑 Lixeira", width=120, fg_color=RED, hover_color=RED_H,
                                       state="disabled", command=self.trash)
        self.trash_btn.pack(side="right", padx=(6, 0))
        self.show_btn = ctk.CTkButton(bottom, text="Mostrar", width=80, fg_color="gray40", hover_color="gray30",
                                      state="disabled", command=self.show)
        self.show_btn.pack(side="right")
        self.details = ctk.CTkLabel(bottom, text=SEL_HINT, text_color=MUTED, font=("Segoe UI", 11), anchor="w",
                                    justify="left", wraplength=440, height=66)
        self.details.pack(side="left", fill="x", expand=True)
        bottom.bind("<Configure>", self._resize)

        self.table = DataTable(parent, [
            {"id": "risk", "text": "Risco", "width": 100, "sort": "num"},
            {"id": "path", "text": "Arquivo", "width": 340, "stretch": True, "sort": "text"},
            {"id": "size", "text": "Tamanho", "width": 90, "anchor": "e", "sort": "num"},
            {"id": "why", "text": "Motivo", "width": 260, "sort": "text"},
        ], on_select=lambda _sel: self.refresh())
        for lvl in (risk.OK, risk.CARE, risk.DANGER):
            self.table.tag("lvl_" + lvl, foreground=LEVEL_COLOR[lvl], bold=(lvl == risk.DANGER))
        self.table.pack(fill="both", expand=True, pady=4)

    def _resize(self, e):
        w = max(200, e.width - 240)
        if abs(w - int(self.details.cget("wraplength"))) > 4:
            self.details.configure(wraplength=w)

    # ---------------------------------------------------------------- conteúdo
    def reset(self, text=""):
        """Esvazia a tabela (ex.: ao começar uma busca) e mostra um aviso no meio."""
        self.table.clear()
        self.rows, self.ids = {}, {}
        self.table.message(text)
        self.refresh()

    def set(self, items):
        """Mostra estes [(tamanho, caminho, Risk)] atualizando as linhas no lugar."""
        entries = []
        self.rows = {}
        for size, p, r in items:
            iid = self.ids.get(p)
            if iid is None:
                self._n += 1
                iid = self.ids[p] = f"f{self._n}"
            self.rows[iid] = (size, p, r)
            shown = self.rel(p) if self.rel else p
            entries.append((iid, [risk.LABEL[r.level], shown, bk.fmt_size(size), r.text],
                            ("lvl_" + r.level,), {"risk": RANK.get(r.level, 0), "size": size}))
        _sync(self.table, entries)
        self.table.message("" if items else self.empty)
        self.refresh()

    # --------------------------------------------------------------- seleção
    def selected(self):
        return [self.rows[i] for i in self.table.sel() if i in self.rows]

    def refresh(self):
        """Atualiza detalhe e botões conforme a seleção (e se tem algo sendo apagado)."""
        sel = self.selected()
        locked = any(r.level == risk.DANGER for _, _, r in sel)
        busy = self.page.trashing
        self.show_btn.configure(state="normal" if sel else "disabled")
        self.trash_btn.configure(state="normal" if sel and not locked and not busy else "disabled",
                                 text="🔒 Bloqueado" if locked else "🗑 Lixeira")
        if not sel:
            text = SEL_HINT
        elif len(sel) == 1:
            size, p, r = sel[0]
            text = f"{p}\n{risk.LABEL[r.level]}: {r.text}"
        else:
            text = f"{len(sel)} arquivos selecionados • {bk.fmt_size(sum(s for s, _, _ in sel))}"
            if locked:
                text += "\nTem NÃO APAGUE na seleção: não dá pra mandar pra lixeira. Tire esse item."
        self.details.configure(text=text)

    def show(self):
        sel = self.selected()
        if sel:
            bk.open_in_explorer(sel[0][1])

    def trash(self):
        sel = self.selected()
        if not sel or self.page.trashing or any(r.level == risk.DANGER for _, _, r in sel):
            return
        if len(sel) == 1:
            _, p, r = sel[0]
            msg = f"{risk.LABEL[r.level]}: {r.text}\n\nMandar para a lixeira?\n\n{p}"
        else:
            total = sum(s for s, _, _ in sel)
            cnt = Counter(r.level for _, _, r in sel)
            parts = ", ".join(f"{cnt[l]} {risk.LABEL[l]}" for l in (risk.OK, risk.CARE) if cnt[l])
            msg = (f"Mandar {len(sel)} arquivo(s) para a lixeira?\nLibera {bk.fmt_size(total)} ({parts}). "
                   f"Dá pra recuperar da lixeira.")
            if cnt[risk.CARE]:
                msg += "\n\nCUIDADO: só você sabe se precisa de alguns desses arquivos."
            msg += "\n\n" + "\n".join(p for _, p, _ in sel[:6]) + ("\n…" if len(sel) > 6 else "")
        if not messagebox.askyesno(APP_NAME, msg):
            return
        self.page.set_trashing(True)

        def work():
            done, errs = [], []
            for s, p, _ in sel:
                try:
                    bk.send_to_trash(p)
                    done.append((s, p))
                except Exception as e:
                    errs.append(str(e) if len(sel) == 1 else f"{os.path.basename(p)}: {e}")
            return done, errs

        def finish(res):
            done, errs = res
            self.page.set_trashing(False)
            for s, _ in done:
                bk.history_add(self.what, s)
            self.on_trashed({p for _, p in done})
            if errs:
                if len(sel) == 1:
                    messagebox.showerror(APP_NAME, f"Não consegui: {errs[0]}")
                else:
                    messagebox.showerror(APP_NAME, f"Não consegui mandar {len(errs)} arquivo(s):\n" + "\n".join(errs[:5]))

        self.page.app.bg(work, finish)


class SpacePage(Page):
    def __init__(self, app):
        super().__init__(app, "Quem está comendo meu espaço?",
                         "Pastas pesadas, arquivos grandes com aviso de risco e arquivos duplicados.")
        self.drives = bk.fixed_drives() or ["C:\\"]
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=24)
        ctk.CTkLabel(top, text="Disco:").pack(side="left")
        self.drive = ctk.CTkOptionMenu(top, values=self.drives, width=90)
        self.drive.pack(side="left", padx=6)
        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, padx=14, pady=(4, 14))
        self.t_dirs = self.tabs.add("📁 Pastas")
        self.t_files = self.tabs.add("📄 Arquivos grandes")
        self.t_dups = self.tabs.add("👯 Duplicados")
        self.t_dl = self.tabs.add("📥 Downloads antigos")
        self.dl_res = []
        self.cur = None
        self.cancel = threading.Event()
        self.file_res = []
        self.groups = []
        self.marked = set()         # caminhos marcados nos duplicados
        self.trashing = False       # tem algo sendo mandado pra lixeira (trava os botões de apagar)
        self._dir_items = {}
        self._dup_rows = {}
        self._build_dirs()
        self._build_files()
        self._build_dups()
        self._build_downloads()

    def on_show(self):
        if not self.loaded:
            self.loaded = True
            self.scan_root()

    def new_cancel(self):
        self.cancel.set()
        self.cancel = threading.Event()
        return self.cancel

    def set_trashing(self, flag):
        self.trashing = flag
        self._files.refresh()
        self._dls.refresh()
        self._safe_state()
        self.update_dup_info()

    # ------------------------------------------------------------------ pastas
    def _build_dirs(self):
        bar = ctk.CTkFrame(self.t_dirs, fg_color="transparent")
        bar.pack(fill="x")
        ctk.CTkButton(bar, text="🔍 Escanear", width=110, command=self.scan_root).pack(side="left")
        self.up_btn = ctk.CTkButton(bar, text="⬆ Subir", width=80, fg_color="gray40", hover_color="gray30",
                                    command=self.go_up, state="disabled")
        self.up_btn.pack(side="left", padx=6)
        self.open_btn = ctk.CTkButton(bar, text="Abrir", width=70, fg_color="gray40", hover_color="gray30",
                                      state="disabled", command=self.open_selected)
        self.open_btn.pack(side="right")
        self.path_lbl = ctk.CTkLabel(bar, text="", text_color=MUTED)
        self.path_lbl.pack(side="left", padx=8)
        self.dir_hint = ctk.CTkLabel(self.t_dirs, text="Duplo clique numa pasta para entrar nela.",
                                     text_color=MUTED, font=("Segoe UI", 11))
        self.dir_hint.pack(side="bottom", anchor="w")
        self.dir_table = DataTable(self.t_dirs, [
            {"id": "name", "text": "Nome", "width": 380, "stretch": True, "sort": "text"},
            {"id": "size", "text": "Tamanho", "width": 100, "anchor": "e", "sort": "num"},
            {"id": "bar", "text": "Peso", "width": 130, "sort": "num"},
        ], selectmode="browse", on_open=self._dir_open, on_select=lambda _sel: self._dir_sel())
        self.dir_table.pack(fill="both", expand=True, pady=4)

    def scan_root(self):
        self.browse(self.drive.get())

    def go_up(self):
        parent = os.path.dirname(self.cur.rstrip("\\"))
        if len(parent) == 2:
            parent += "\\"
        if parent:
            self.browse(parent)

    def browse(self, path):
        ev = self.new_cancel()
        self.cur = path
        self.path_lbl.configure(text=shorten(path, 60))
        self.up_btn.configure(state="normal" if len(path.rstrip("\\")) > 2 else "disabled")
        self._dir_items = {}
        self.dir_table.clear()
        self.dir_table.message("Medindo… (o disco inteiro pode levar 1–2 minutos)")
        self._dir_sel()
        self.app.bg(lambda: bk.scan_children(path, ev), lambda items: self.show_dirs(path, items, ev))

    def show_dirs(self, path, items, ev):
        if ev.is_set() or path != self.cur:
            return
        t = self.dir_table
        t.clear()
        self._dir_items = {}
        note = "Duplo clique numa pasta para entrar nela."
        if not items:
            t.message("Vazio (ou sem permissão).")
        else:
            biggest = max(i[2] for i in items) or 1
            for n, item in enumerate(items[:MAX_DIRS]):
                name, p, size, is_dir = item
                iid = f"d{n}"
                self._dir_items[iid] = item
                full = round(size / biggest * 10)
                t.add([("📁 " if is_dir else "📄 ") + name, bk.fmt_size(size), "█" * full + "░" * (10 - full)],
                      iid=iid, raw={"size": size, "bar": size})
            _resort(t)
            if len(items) > MAX_DIRS:
                note += f"  Mostrando os {MAX_DIRS} maiores de {len(items)}."
        self.dir_hint.configure(text=note)
        self._dir_sel()

    def _dir_open(self, iid):
        item = self._dir_items.get(iid)
        if item and item[3]:
            self.browse(item[1])

    def _dir_sel(self):
        has = any(i in self._dir_items for i in self.dir_table.sel())
        self.open_btn.configure(state="normal" if has else "disabled")

    def open_selected(self):
        for iid in self.dir_table.sel():
            if iid in self._dir_items:
                bk.open_in_explorer(self._dir_items[iid][1])
                return

    # --------------------------------------------------------- arquivos grandes
    def _build_files(self):
        fb = ctk.CTkFrame(self.t_files, fg_color="transparent")
        fb.pack(fill="x")
        ctk.CTkLabel(fb, text="Maiores que").pack(side="left")
        self.minsz = ctk.CTkOptionMenu(fb, values=["50 MB", "100 MB", "500 MB", "1 GB"], width=100)
        self.minsz.set("100 MB")
        self.minsz.pack(side="left", padx=6)
        self.find_btn = ctk.CTkButton(fb, text="🔍 Procurar", width=110, command=self.find_files)
        self.find_btn.pack(side="left")
        self.file_status = ctk.CTkLabel(fb, text="", text_color=MUTED)
        self.file_status.pack(side="left", padx=10)

        fb2 = ctk.CTkFrame(self.t_files, fg_color="transparent")
        fb2.pack(fill="x", pady=(6, 0))
        ctk.CTkLabel(fb2, text="Mostrar:").pack(side="left")
        self.filter = ctk.CTkSegmentedButton(fb2, values=list(FILTERS), command=lambda _=None: self.show_files())
        self.filter.set("Todos")
        self.filter.pack(side="left", padx=6)
        self.safe_btn = ctk.CTkButton(fb2, text="🧹 Apagar todos os seguros", width=220, fg_color=ACCENT,
                                      hover_color=ACCENT_H, state="disabled", command=self.delete_safe)
        self.safe_btn.pack(side="right")
        legend = ctk.CTkLabel(self.t_files, text="SEGURO = o programa/Windows recria ou é lixo.   "
                                                 "CUIDADO = só você sabe se precisa.   "
                                                 "NÃO APAGUE = pode quebrar o Windows ou um programa.",
                              text_color=MUTED, font=("Segoe UI", 11))
        legend.pack(anchor="w", pady=(4, 0))
        self._files = RiskList(self, self.t_files, "Arquivo grande", self._files_trashed)
        self.file_table = self._files.table

    def find_files(self):
        ev = self.new_cancel()
        mb = {"50 MB": 50, "100 MB": 100, "500 MB": 500, "1 GB": 1024}[self.minsz.get()]
        root = self.drive.get()
        self.find_btn.configure(state="disabled")
        self.file_res = []
        self._safe_state()
        self._files.reset("Procurando…")

        def prog(n, d):
            self.app.post(lambda: self.file_status.configure(text=f"{n:,} arquivos verificados…".replace(",", ".")))

        def work():
            res = bk.find_big_files(root, mb * 1024 * 1024, ev, prog)
            self.app.post(lambda: self.file_status.configure(text="Avaliando o risco de cada arquivo…"))
            return [(s, p, risk.assess(p)) for s, p in res]

        def done(res):
            self.find_btn.configure(state="normal")
            self.file_res = res
            self.file_status.configure(text=f"{len(res)} arquivo(s) encontrados")
            self.show_files()

        self.app.bg(work, done)

    def _safe_items(self):
        return [(s, p, r) for s, p, r in self.file_res if r.level == risk.OK]

    def _safe_state(self):
        safe = self._safe_items()
        total = sum(s for s, _, _ in safe)
        self.safe_btn.configure(state="normal" if safe and not self.trashing else "disabled",
                                text=f"🧹 Apagar todos os seguros ({bk.fmt_size(total)})" if safe
                                else "🧹 Apagar todos os seguros")

    def show_files(self):
        want = FILTERS[self.filter.get()]
        self._safe_state()
        self._files.set([x for x in self.file_res if want is None or x[2].level == want])

    def _files_trashed(self, gone):
        self.file_res = [x for x in self.file_res if x[1] not in gone]
        self.show_files()

    def delete_safe(self):
        safe = self._safe_items()
        if not safe or self.trashing:
            return
        total = sum(s for s, _, _ in safe)
        if not messagebox.askyesno(APP_NAME, f"Mandar {len(safe)} arquivo(s) SEGUROS para a lixeira?\n"
                                             f"Libera {bk.fmt_size(total)}. Dá pra recuperar da lixeira."):
            return
        self.set_trashing(True)

        def work():
            done, freed = set(), 0
            for s, p, _ in safe:
                try:
                    bk.send_to_trash(p)
                    done.add(p)
                    freed += s
                except Exception:
                    pass
            return done, freed

        def finish(res):
            done, freed = res
            self.set_trashing(False)
            bk.history_add("Arquivos grandes seguros", freed)
            self.file_res = [x for x in self.file_res if x[1] not in done]
            self.show_files()
            messagebox.showinfo(APP_NAME, f"Pronto! {len(done)} arquivo(s), {bk.fmt_size(freed)} na lixeira.")

        self.app.bg(work, finish)

    # -------------------------------------------------------- downloads antigos
    def _build_downloads(self):
        bar = ctk.CTkFrame(self.t_dl, fg_color="transparent")
        bar.pack(fill="x")
        ctk.CTkLabel(bar, text="Sem mexer há mais de").pack(side="left")
        self.dl_days = ctk.CTkOptionMenu(bar, values=["30 dias", "60 dias", "90 dias", "180 dias", "1 ano"], width=100)
        self.dl_days.set("90 dias")
        self.dl_days.pack(side="left", padx=6)
        self.dl_btn = ctk.CTkButton(bar, text="🔍 Listar", width=100, command=self.find_downloads)
        self.dl_btn.pack(side="left")
        self.dl_status = ctk.CTkLabel(bar, text="", text_color=MUTED)
        self.dl_status.pack(side="left", padx=10)
        ctk.CTkLabel(self.t_dl, text="Só listo. Nada é apagado sozinho: você escolhe arquivo por arquivo.",
                     text_color=MUTED, font=("Segoe UI", 11)).pack(anchor="w", pady=(4, 0))
        self._dls = RiskList(self, self.t_dl, "Download antigo", self._dl_trashed, rel=self._dl_rel,
                             empty="Nada velho por aqui. 👍")
        self.dl_table = self._dls.table

    @staticmethod
    def _dl_rel(p):
        try:
            return os.path.relpath(p, system.downloads_dir())
        except ValueError:
            return p

    def find_downloads(self):
        ev = self.new_cancel()
        days = {"30 dias": 30, "60 dias": 60, "90 dias": 90, "180 dias": 180, "1 ano": 365}[self.dl_days.get()]
        self.dl_btn.configure(state="disabled")
        self.dl_res = []
        self._dls.reset("Procurando…")

        def work():
            return [(s, p, risk.assess(p)) for s, p in system.old_downloads(days, ev, top=200)]

        def done(res):
            self.dl_btn.configure(state="normal")
            self.dl_res = res
            total = sum(s for s, _, _ in res)
            more = " (os 200 maiores)" if len(res) >= 200 else ""
            self.dl_status.configure(text=f"{len(res)} arquivo(s){more} • {bk.fmt_size(total)}")
            self.show_downloads()

        self.app.bg(work, done)

    def show_downloads(self):
        self._dls.set(self.dl_res)

    def _dl_trashed(self, gone):
        self.dl_res = [x for x in self.dl_res if x[1] not in gone]
        self.show_downloads()

    # --------------------------------------------------------------- duplicados
    def _build_dups(self):
        t = self.t_dups
        bar = ctk.CTkFrame(t, fg_color="transparent")
        bar.pack(fill="x")
        ctk.CTkLabel(bar, text="Onde:").pack(side="left")
        self.dup_where = ctk.CTkOptionMenu(bar, values=["Minhas pastas"] + self.drives, width=130)
        self.dup_where.pack(side="left", padx=6)
        ctk.CTkLabel(bar, text="Maiores que").pack(side="left", padx=(8, 0))
        self.dup_min = ctk.CTkOptionMenu(bar, values=["1 MB", "10 MB", "100 MB"], width=90)
        self.dup_min.set("10 MB")
        self.dup_min.pack(side="left", padx=6)
        self.dup_btn = ctk.CTkButton(bar, text="🔍 Procurar", width=110, command=self.find_dups)
        self.dup_btn.pack(side="left")
        self.dup_status = ctk.CTkLabel(bar, text="", text_color=MUTED)
        self.dup_status.pack(side="left", padx=10)

        bar2 = ctk.CTkFrame(t, fg_color="transparent")
        bar2.pack(fill="x", pady=(6, 0))
        self.dup_del = ctk.CTkButton(bar2, text="🗑 Mandar marcados pra lixeira", width=240, fg_color=RED,
                                     hover_color=RED_H, state="disabled", command=self.del_dups)
        self.dup_del.pack(side="right")
        self.dup_info = ctk.CTkLabel(bar2, text=DUP_HINT, text_color=MUTED)
        self.dup_info.pack(side="left")
        self.dup_table = DataTable(t, [
            {"id": "mark", "text": "Marcar", "width": 70, "anchor": "center", "toggle": True},
            {"id": "file", "text": "Arquivo", "width": 520, "stretch": True},
            {"id": "date", "text": "Data", "width": 90, "anchor": "center"},
        ], tree=True, selectmode="browse", on_toggle=self._dup_toggle)
        self.dup_table.tag("grp", bold=True)
        self.dup_table.pack(fill="both", expand=True, pady=4)

    def _dup_status_text(self):
        n = len(self.groups)
        more = f" (mostrando os {MAX_DUPS} que mais desperdiçam)" if n > MAX_DUPS else ""
        return f"{n} grupo(s) de arquivos iguais{more}"

    def find_dups(self):
        ev = self.new_cancel()
        where = self.dup_where.get()
        roots = bk.user_folders() if where == "Minhas pastas" else [where]
        mb = {"1 MB": 1, "10 MB": 10, "100 MB": 100}[self.dup_min.get()]
        self.dup_btn.configure(state="disabled")
        self.groups, self.marked, self._dup_rows = [], set(), {}
        self.dup_table.clear()
        self.dup_table.message("Procurando… (pode levar alguns minutos)")
        self.update_dup_info()

        def prog(text):
            self.app.post(lambda: self.dup_status.configure(text=text))

        def done(groups):
            self.dup_btn.configure(state="normal")
            self.groups = groups
            self.dup_status.configure(text=self._dup_status_text())
            self.render_dups()

        self.app.bg(lambda: bk.find_duplicates(roots, mb * 1024 * 1024, ev, prog), done)

    def render_dups(self):
        """Desenha os grupos; em cada um, a primeira cópia (a que sugiro manter) fica sem marca."""
        t = self.dup_table
        t.clear()
        self._dup_rows, self.marked = {}, set()
        shown = self.groups[:MAX_DUPS]
        for n, g in enumerate(shown):
            g["files"].sort(key=lambda f: ("\\downloads\\" in f[0].lower(), f[1]))
            k = len(g["files"])
            gid = t.add(["", f"{k} cópias de {bk.fmt_size(g['size'])} • desperdício de "
                             f"{bk.fmt_size(g['size'] * (k - 1))}", ""], iid=f"g{n}", tags=("grp",))
            for i, (p, mt) in enumerate(g["files"]):
                iid = f"g{n}_{i}"
                self._dup_rows[iid] = (g, p)
                if i > 0:
                    self.marked.add(p)
                t.add([CHECK_ON if i > 0 else CHECK_OFF, p, _date(mt)], iid=iid, parent=gid)
        t.restripe()
        t.message("" if shown else "Nenhum duplicado. 👍")
        self.update_dup_info()

    def _dup_toggle(self, iid, col):
        info = self._dup_rows.get(iid)
        if not info:                    # clicou na linha do grupo
            return
        g, p = info
        if p in self.marked:
            self.marked.discard(p)
        else:
            if all(f in self.marked for f, _ in g["files"] if f != p):
                messagebox.showwarning(APP_NAME, "Pelo menos uma cópia de cada grupo precisa ficar sem marca, "
                                                 "senão você perderia o arquivo.")
                return
            self.marked.add(p)
        self.dup_table.update(iid, mark=CHECK_ON if p in self.marked else CHECK_OFF)
        self.update_dup_info()

    def _marked(self):
        return [(g["size"], p) for g in self.groups[:MAX_DUPS] for p, _ in g["files"] if p in self.marked]

    def update_dup_info(self):
        marked = self._marked()
        total = sum(s for s, _ in marked)
        self.dup_del.configure(state="normal" if marked and not self.trashing else "disabled")
        if marked:
            text = f"{len(marked)} marcado(s) • libera {bk.fmt_size(total)}"
        else:
            text = "Nenhuma cópia marcada." if self.groups else DUP_HINT
        self.dup_info.configure(text=text)

    def del_dups(self):
        if self.trashing:
            return
        for g in self.groups[:MAX_DUPS]:
            if all(p in self.marked for p, _ in g["files"]):
                messagebox.showwarning(APP_NAME, "Num dos grupos todas as cópias estão marcadas. "
                                                 "Desmarque pelo menos uma para não perder o arquivo.")
                return
        marked = self._marked()
        if not marked:
            return
        total = sum(s for s, _ in marked)
        if not messagebox.askyesno(APP_NAME, f"Mandar {len(marked)} cópia(s) para a lixeira?\n"
                                             f"Libera {bk.fmt_size(total)}. Dá pra recuperar da lixeira."):
            return
        self.set_trashing(True)

        def work():
            gone, freed = set(), 0
            for s, p in marked:
                try:
                    bk.send_to_trash(p)
                    gone.add(p)
                    freed += s
                except Exception:
                    pass
            return gone, freed

        def finish(res):
            gone, freed = res
            bk.history_add("Duplicados", freed)
            kept = []
            for g in self.groups:
                files = [f for f in g["files"] if f[0] not in gone]
                if len(files) > 1:
                    kept.append({"size": g["size"], "files": files})
            self.groups = kept
            self.dup_status.configure(text=self._dup_status_text())
            self.set_trashing(False)
            self.render_dups()
            messagebox.showinfo(APP_NAME, f"Pronto! {len(gone)} cópia(s), {bk.fmt_size(freed)} na lixeira.")

        self.app.bg(work, finish)
