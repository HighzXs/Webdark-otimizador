"""Demo A: customtkinter (o que o app usa hoje), com o melhor que dá pra fazer nele.

Arquivos = DataTable (Treeview, lista de um widget só). Ajustes = CTkScrollableFrame com um cartão por ajuste,
do jeito que as telas antigas eram. Role rápido nas duas pra comparar.
"""
import ctypes
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import customtkinter as ctk

from demo_data import SETTINGS, fmt_size, make_rows
from ui_common import ACCENT, ACCENT_H, CARD, GREEN, MUTED, RED, AMBER, apply_theme, gradient_title
import ui_table as T

apply_theme()
ctk.set_appearance_mode("dark")
LEVEL = {"ok": "ok", "care": "care", "danger": "danger"}


class Demo(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Demo A — customtkinter")
        self.geometry("1180x800")
        self.rows = make_rows(300)
        side = ctk.CTkFrame(self, width=220, corner_radius=0)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        ctk.CTkLabel(side, image=gradient_title("Faxina Várzea", 22), text="").pack(pady=(22, 0), padx=14, anchor="w")
        ctk.CTkLabel(side, text="demo A • customtkinter", text_color=MUTED).pack(padx=16, anchor="w", pady=(0, 16))
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.pack(side="right", fill="both", expand=True)
        self.pages, self.nav = [], []
        for i, name in enumerate(["🏠  Início", "📊  Arquivos", "⚙  Ajustes"]):
            b = ctk.CTkButton(side, text=name, anchor="w", height=40, font=("Segoe UI", 14), fg_color="transparent",
                              text_color=("gray10", "gray90"), hover_color=("gray75", "#1d1d2b"),
                              command=lambda i=i: self.go(i))
            b.pack(fill="x", padx=12, pady=2)
            self.nav.append(b)
        self.busy = ctk.CTkProgressBar(side, mode="indeterminate", height=5)
        ctk.CTkLabel(side, text="feito na porra 💚💛", text_color=MUTED).pack(side="bottom", pady=14)
        self.busy.pack(side="bottom", fill="x", padx=14)
        self.busy.pack_forget()
        self.pages = [self.home(), self.files(), self.settings()]
        self.go(0)

    def head(self, parent, t, s):
        ctk.CTkLabel(parent, text=t, font=("Segoe UI", 27, "bold")).pack(anchor="w", padx=28, pady=(24, 0))
        ctk.CTkLabel(parent, text=s, text_color=MUTED).pack(anchor="w", padx=28, pady=(0, 10))

    def go(self, i):
        for p in self.pages:
            p.pack_forget()
        self.pages[i].pack(fill="both", expand=True)
        for k, b in enumerate(self.nav):
            b.configure(fg_color=ACCENT if k == i else "transparent")

    def home(self):
        f = ctk.CTkFrame(self.content, fg_color="transparent")
        self.head(f, "Início", "Resumo do seu PC e uma faxina segura com um clique.")
        tiles = ctk.CTkFrame(f, fg_color="transparent")
        tiles.pack(fill="x", padx=24)
        for i, (t, v, s) in enumerate([("💽 Espaço livre (C:)", "231.9 GB", "de 475.9 GB"), ("🧹 Dá pra limpar", "618.9 MB", "lixo seguro"),
                                       ("🚀 Abrem com o Windows", "7", "programas ligados"), ("🧠 Memória em uso", "78%", "12.4 GB de 15.9 GB")]):
            c = ctk.CTkFrame(tiles, fg_color=CARD, corner_radius=14)
            c.grid(row=0, column=i, padx=5, sticky="nsew")
            tiles.grid_columnconfigure(i, weight=1, uniform="t")
            ctk.CTkLabel(c, text=t, text_color=MUTED).pack(anchor="w", padx=14, pady=(10, 0))
            ctk.CTkLabel(c, text=v, font=("Segoe UI", 26, "bold")).pack(anchor="w", padx=14)
            ctk.CTkLabel(c, text=s, text_color=MUTED).pack(anchor="w", padx=14, pady=(0, 10))
        box = ctk.CTkFrame(f, fg_color=CARD, corner_radius=14)
        box.pack(fill="x", padx=29, pady=14)
        row = ctk.CTkFrame(box, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=(16, 6))
        self.go_btn = ctk.CTkButton(row, text="⚡  Faxina rápida", height=44, width=200, font=("Segoe UI", 15, "bold"), command=self.fake)
        self.go_btn.pack(side="left")
        ctk.CTkLabel(row, text="Limpa só o que é seguro: temporários, cache, lixeira e restos do Windows.", text_color=MUTED).pack(side="left", padx=14)
        self.prog = ctk.CTkProgressBar(box, height=8)
        self.prog.set(0)
        self.prog.pack(fill="x", padx=18, pady=6)
        self.ptxt = ctk.CTkLabel(box, text="Pronto para começar.", text_color=MUTED)
        self.ptxt.pack(anchor="w", padx=18, pady=(0, 14))
        return f

    def fake(self):
        self.v = 0
        self.go_btn.configure(state="disabled")
        self.busy.pack(side="bottom", fill="x", padx=14)
        self.busy.start()
        self.tick()

    def tick(self):
        self.v += 1
        self.prog.set(self.v / 100)
        names = ["Arquivos temporários", "Cache dos navegadores", "Lixeira", "Miniaturas", "Relatórios de erro"]
        self.ptxt.configure(text=f"→ {names[min(self.v // 21, 4)]}…  {self.v}%")
        if self.v < 100:
            self.after(40, self.tick)
        else:
            self.go_btn.configure(state="normal")
            self.busy.stop()
            self.busy.pack_forget()
            self.ptxt.configure(text="✅ Pronto! 618.9 MB liberados.")

    def files(self):
        f = ctk.CTkFrame(self.content, fg_color="transparent")
        self.head(f, "Arquivos grandes", "Selecione uma linha e use os botões embaixo. (Aqui o botão por linha não existe.)")
        self.table = T.DataTable(f, [
            {"id": "on", "text": "", "width": 44, "anchor": "center", "toggle": True},
            {"id": "risk", "text": "RISCO", "width": 110, "sort": "text"},
            {"id": "path", "text": "ARQUIVO", "width": 470, "stretch": True, "sort": "text"},
            {"id": "size", "text": "TAMANHO", "width": 100, "anchor": "e", "sort": "num"},
        ], on_toggle=lambda iid, col: self.table.update(iid, on=T.CHECK_OFF if self.table.cell(iid, "on") == T.CHECK_ON else T.CHECK_ON))
        self.table.tag("ok", foreground="#4ade80")
        self.table.tag("care", foreground="#fbbf24")
        self.table.tag("danger", foreground="#f87171", bold=True)
        for i, r in enumerate(self.rows):
            self.table.add([T.CHECK_OFF, r["label"], r["path"], fmt_size(r["size"])], iid=f"r{i}", tags=(r["level"],), raw={"size": r["size"]})
        self.table.restripe()
        self.table.pack(fill="both", expand=True, padx=26, pady=4)
        bar = ctk.CTkFrame(f, fg_color="transparent")
        bar.pack(fill="x", padx=26, pady=10)
        ctk.CTkButton(bar, text="🧹 Apagar todos os seguros", command=lambda: None).pack(side="right")
        ctk.CTkButton(bar, text="🗑 Lixeira", fg_color=RED, hover_color="#b91c1c", width=100).pack(side="right", padx=8)
        ctk.CTkButton(bar, text="Mostrar", fg_color="gray40", hover_color="gray30", width=100).pack(side="right")
        ctk.CTkLabel(bar, text="300 arquivos", text_color=MUTED).pack(side="left")
        return f

    def settings(self):
        f = ctk.CTkFrame(self.content, fg_color="transparent")
        self.head(f, "Ajustes", "Tudo que dá pra personalizar. Role rápido pra testar o desenho.")
        sc = ctk.CTkScrollableFrame(f, fg_color="transparent")
        sc.pack(fill="both", expand=True, padx=18, pady=(0, 10))
        ctk.CTkLabel(sc, text="🎨 Aparência", font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=8, pady=(4, 4))
        c = ctk.CTkFrame(sc, fg_color=CARD, corner_radius=14)
        c.pack(fill="x", pady=4, padx=4)
        for label, widget in (("Blur atrás da janela (não existe no customtkinter)", None), ("Intensidade", "slider"), ("Fonte", "menu")):
            r = ctk.CTkFrame(c, fg_color="transparent")
            r.pack(fill="x", padx=16, pady=8)
            ctk.CTkLabel(r, text=label).pack(side="left")
            if widget == "slider":
                ctk.CTkSlider(r, width=220).pack(side="right")
            elif widget == "menu":
                ctk.CTkOptionMenu(r, values=["Segoe UI", "Consolas"], width=160).pack(side="right")
            else:
                ctk.CTkSwitch(r, text="", state="disabled").pack(side="right")
        ctk.CTkLabel(sc, text="⚡ Desempenho e privacidade", font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=8, pady=(10, 4))
        for name, desc, on in SETTINGS:
            c = ctk.CTkFrame(sc, fg_color=CARD, corner_radius=14)
            c.pack(fill="x", pady=4, padx=4)
            tx = ctk.CTkFrame(c, fg_color="transparent")
            tx.pack(side="left", fill="x", expand=True, padx=16, pady=10)
            ctk.CTkLabel(tx, text=name, font=("Segoe UI", 13, "bold"), anchor="w").pack(anchor="w")
            ctk.CTkLabel(tx, text=desc, text_color=MUTED, anchor="w").pack(anchor="w")
            sw = ctk.CTkSwitch(c, text="", width=46)
            if on:
                sw.select()
            sw.pack(side="right", padx=16)
        return f


if __name__ == "__main__":
    app = Demo()
    if len(sys.argv) > 1 and sys.argv[1] == "second":
        app.geometry("1180x800+1960+30")
    if len(sys.argv) > 2:
        from PIL import ImageGrab
        prefix = sys.argv[2]

        def pump(s):
            end = time.time() + s
            while time.time() < end:
                app.update()
                time.sleep(0.02)

        def shot(i):
            app.attributes("-topmost", True)
            app.lift()
            pump(0.6)
            x, y, w, h = app.winfo_rootx(), app.winfo_rooty(), app.winfo_width(), app.winfo_height()
            ImageGrab.grab(bbox=(x, y, x + w, y + h), all_screens=True).save(f"{prefix}_{i}.png")

        pump(2); shot(0)
        app.go(1); pump(1.2); shot(1)
        app.go(2); pump(2); shot(2)
        app.go(0); app.fake(); pump(2.8); shot(3)
        os._exit(0)
    app.mainloop()
