"""Tabela rápida no estilo do app (ttk.Treeview).

Nenhuma linha vira widget: o customtkinter fica lento e embaralha o desenho com dezenas de linhas de
widgets dentro de um CTkScrollableFrame. Aqui a lista inteira é um widget só, e dá pra atualizar uma
linha no lugar (update/set_order) sem apagar nem recriar nada, então não pisca.

Uso básico:
    t = DataTable(parent, [
        {"id": "name", "text": "Nome", "width": 320, "stretch": True, "sort": "text"},
        {"id": "size", "text": "Tamanho", "width": 100, "anchor": "e", "sort": "num"},
        {"id": "on", "text": "Ligado", "width": 70, "anchor": "center", "toggle": True},
    ], on_open=duplo_clique, on_toggle=clicou_na_coluna_toggle, on_select=mudou_selecao)
    t.pack(fill="both", expand=True)
    iid = t.add(["foo.exe", "1.2 GB", CHECK_OFF], raw={"size": 1288490188})
    t.update(iid, size="1.3 GB", raw={"size": 1395864371})

Colunas com "sort" ordenam ao clicar no cabeçalho ("text" usa o texto, "num" usa o valor de raw[col]).
Colunas com "toggle": um clique na célula chama on_toggle(iid, col) (use CHECK_ON/CHECK_OFF/SWITCH_ON/SWITCH_OFF).
"""
import tkinter as tk
import weakref
from tkinter import ttk

import customtkinter as ctk

from ui_common import ACCENT_H, MUTED

CHECK_ON, CHECK_OFF = "☑", "☐"
SWITCH_ON, SWITCH_OFF = "● ligado", "○ desligado"

_tables = weakref.WeakSet()
_STYLE = "WD.Treeview"


def _palette():
    if ctk.get_appearance_mode() == "Dark":
        return {"bg": "#0e0e16", "alt": "#12121c", "fg": "#e2e2ee", "head": "#161622", "head_fg": "#9a9ab5",
                "head_active": "#1f1f30", "sel": ACCENT_H}
    return {"bg": "#ffffff", "alt": "#f2f2f8", "fg": "#1a1a24", "head": "#e4e4ee", "head_fg": "#44445a",
            "head_active": "#d4d4e2", "sel": ACCENT_H}


def _apply_style(widget):
    p = _palette()
    st = ttk.Style(widget)
    if st.theme_use() != "clam":
        st.theme_use("clam")      # só o 'clam' respeita as cores customizadas
    scale = widget.winfo_fpixels("1i") / 96
    st.configure(_STYLE, background=p["bg"], fieldbackground=p["bg"], foreground=p["fg"], borderwidth=0,
                 relief="flat", rowheight=int(30 * scale), font=("Segoe UI", 10))
    st.map(_STYLE, background=[("selected", p["sel"])], foreground=[("selected", "white")])
    st.layout(_STYLE, [("Treeview.treearea", {"sticky": "nswe"})])
    st.configure(_STYLE + ".Heading", background=p["head"], foreground=p["head_fg"], relief="flat", borderwidth=0,
                 font=("Segoe UI", 9, "bold"), padding=(8, 6))
    st.map(_STYLE + ".Heading", background=[("active", p["head_active"])])


def restyle_all():
    """Chamar depois de trocar entre tema escuro e claro."""
    for t in list(_tables):
        t.restyle()


class DataTable(ctk.CTkFrame):
    def __init__(self, parent, columns, *, tree=False, selectmode="extended", on_open=None, on_toggle=None,
                 on_select=None, **kw):
        kw.setdefault("fg_color", "transparent")
        super().__init__(parent, **kw)
        self.columns = columns
        self.on_open, self.on_toggle, self.on_select = on_open, on_toggle, on_select
        self.raw = {}                 # iid -> {coluna: valor para ordenar}
        self._tag_fonts = {}
        self._sort = (None, False)
        self._ids = [c["id"] for c in columns]
        _apply_style(self)

        self.tree = ttk.Treeview(self, style=_STYLE, columns=self._ids, selectmode=selectmode,
                                 show="tree headings" if tree else "headings")
        sb = ctk.CTkScrollbar(self, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        if tree:
            self.tree.column("#0", width=22, minwidth=22, stretch=False)
            self.tree.heading("#0", text="")
        for c in columns:
            self.tree.heading(c["id"], text=c["text"], anchor=c.get("anchor", "w"),
                              command=(lambda col=c["id"]: self.sort_by(col)) if c.get("sort") else "")
            self.tree.column(c["id"], width=c.get("width", 100), minwidth=c.get("minwidth", 40),
                             anchor=c.get("anchor", "w"), stretch=c.get("stretch", False))

        self.msg = ctk.CTkLabel(self, text="", text_color=MUTED)     # "Nada aqui", "Procurando…"
        self.tree.bind("<Button-1>", self._click, add="+")
        self.tree.bind("<Double-1>", self._double)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.on_select and self.on_select(self.sel()))
        self.restyle()
        _tables.add(self)

    # ------------------------------------------------------------------ aparência
    def restyle(self):
        _apply_style(self)
        p = _palette()
        self.tree.tag_configure("odd", background=p["bg"])
        self.tree.tag_configure("even", background=p["alt"])
        for name, opts in self._tag_fonts.items():
            self.tree.tag_configure(name, **opts)

    def tag(self, name, foreground=None, background=None, bold=False):
        """Cria uma etiqueta de cor para linhas (ex.: risco). Use em add(..., tags=(nome,))."""
        opts = {}
        if foreground:
            opts["foreground"] = foreground
        if background:
            opts["background"] = background
        if bold:
            opts["font"] = ("Segoe UI", 10, "bold")
        self._tag_fonts[name] = opts
        self.tree.tag_configure(name, **opts)

    # ------------------------------------------------------------------- conteúdo
    def message(self, text=""):
        """Mostra um texto no meio da tabela (ex.: 'Procurando…'); texto vazio esconde."""
        if text:
            self.msg.configure(text=text)
            self.msg.place(relx=0.5, rely=0.5, anchor="center")
        else:
            self.msg.place_forget()

    def add(self, values, iid=None, parent="", tags=(), raw=None, open=True):
        iid = self.tree.insert(parent, "end", iid=iid, values=list(values), tags=tuple(tags), open=open)
        if raw:
            self.raw[iid] = dict(raw)
        return iid

    def update(self, iid=None, values=None, tags=None, raw=None, **cells):
        """Muda a linha no lugar. Passe a lista inteira em `values` ou só as colunas que mudaram (id=valor).

        Sem argumentos vira o update() normal do Tk (processa eventos), que este método esconde.
        """
        if iid is None:
            return super().update()
        if values is not None:
            self.tree.item(iid, values=list(values))
        for col, val in cells.items():
            self.tree.set(iid, col, val)
        if tags is not None:
            self.tree.item(iid, tags=tuple(tags))
        if raw is not None:
            self.raw.setdefault(iid, {}).update(raw)

    def cell(self, iid, col):
        return self.tree.set(iid, col)

    def has(self, iid):
        return self.tree.exists(iid)

    def rows(self, parent=""):
        return list(self.tree.get_children(parent))

    def all_rows(self):
        """Todas as linhas folha, na ordem da tela (pula os grupos)."""
        out = []
        for top in self.tree.get_children(""):
            kids = self.tree.get_children(top)
            out.extend(kids if kids else [top])
        return out

    def remove(self, *iids):
        for iid in iids:
            if self.tree.exists(iid):
                self.tree.delete(iid)
            self.raw.pop(iid, None)

    def clear(self):
        self.tree.delete(*self.tree.get_children(""))
        self.raw.clear()
        self.message("")

    def sel(self):
        return list(self.tree.selection())

    def set_sel(self, iids):
        self.tree.selection_set([i for i in iids if self.tree.exists(i)])

    def set_order(self, iids, parent=""):
        """Põe as linhas nessa ordem mexendo só nas que mudaram de posição (nada é apagado, não pisca)."""
        current = list(self.tree.get_children(parent))
        for i, iid in enumerate(iids):
            if i < len(current) and current[i] == iid:
                continue
            self.tree.move(iid, parent, i)
            current = list(self.tree.get_children(parent))

    def restripe(self):
        """Alterna a cor de fundo das linhas (zebra). Chamar depois de adicionar/remover/ordenar."""
        n = 0
        for iid in self.all_rows():
            tags = [t for t in self.tree.item(iid, "tags") if t not in ("odd", "even")]
            tags.append("even" if n % 2 else "odd")
            self.tree.item(iid, tags=tags)
            n += 1

    # ------------------------------------------------------------------- ordenação
    def sort_by(self, col, reverse=None):
        kind = next((c.get("sort") for c in self.columns if c["id"] == col), None)
        if not kind:
            return
        if reverse is None:
            reverse = (self._sort[0] == col and not self._sort[1])
        self._sort = (col, reverse)

        def key(iid):
            if kind == "num":
                try:
                    return float(self.raw.get(iid, {}).get(col, 0))
                except (TypeError, ValueError):
                    return 0.0
            return str(self.raw.get(iid, {}).get(col, self.tree.set(iid, col))).lower()

        groups = [i for i in self.tree.get_children("") if self.tree.get_children(i)]
        for parent in groups if groups else [""]:      # com grupos, ordena só dentro de cada grupo
            kids = sorted(self.tree.get_children(parent), key=key, reverse=reverse)
            for i, iid in enumerate(kids):
                self.tree.move(iid, parent, i)
        for c in self.columns:
            arrow = (" ▼" if reverse else " ▲") if c["id"] == col else ""
            self.tree.heading(c["id"], text=c["text"] + arrow)
        self.restripe()

    # --------------------------------------------------------------------- cliques
    def _col_at(self, x):
        idx = self.tree.identify_column(x)           # '#0', '#1', …
        try:
            n = int(idx.lstrip("#")) - 1       # '#0' é a coluna da árvore; '#1' já é a 1ª coluna de dados
        except ValueError:
            return None
        return self._ids[n] if 0 <= n < len(self._ids) else None

    def _click(self, e):
        if self.tree.identify_region(e.x, e.y) != "cell" or not self.on_toggle:
            return None
        col = self._col_at(e.x)
        iid = self.tree.identify_row(e.y)
        if col and iid and next(c for c in self.columns if c["id"] == col).get("toggle"):
            self.on_toggle(iid, col)
            return "break"                           # clicar no interruptor não muda a seleção
        return None

    def _double(self, e):
        iid = self.tree.identify_row(e.y)
        if not iid or self.tree.identify_region(e.x, e.y) != "cell":
            return None
        col = self._col_at(e.x)
        if self.on_toggle and col and next(c for c in self.columns if c["id"] == col).get("toggle"):
            self.on_toggle(iid, col)         # o 2º clique rápido também vale como clique no interruptor
            return "break"
        if self.on_open:
            self.on_open(iid)
        return None
