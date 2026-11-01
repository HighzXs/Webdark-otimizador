"""Demo B: PySide6 (Qt). Lista virtualizada, rolagem por pixel, degradês, animações e blur (acrílico) do Windows 11."""
import ctypes
import sys

from PySide6.QtCore import (Property, QAbstractTableModel, QEasingCurve, QModelIndex, QPoint, QPropertyAnimation,
                            QRectF, QSize, Qt, QTimer, Signal)
from PySide6.QtGui import (QBrush, QColor, QCursor, QFont, QFontMetrics, QLinearGradient, QPainter, QPainterPath, QPen)
from PySide6.QtWidgets import (QAbstractButton, QApplication, QComboBox, QFrame, QGridLayout, QHBoxLayout, QHeaderView,
                               QLabel, QLineEdit, QMainWindow, QProgressBar, QPushButton, QScrollArea, QSlider,
                               QStackedWidget, QStyledItemDelegate, QTableView, QVBoxLayout, QWidget,
                               QAbstractItemView, QStyle)

from demo_data import ACCENTS, SETTINGS, fmt_size, make_rows

STOPS = ["#4fd1e6", "#5aa3e0", "#8f71d0", "#b043d1"]
LEVEL_COLOR = {"ok": "#16a34a", "care": "#ca8a04", "danger": "#dc2626"}
state = {"accent": "#8b5cf6", "blur": True}


def qss():
    a = state["accent"]
    solid = not state["blur"]
    bg = "#05050a" if solid else "rgba(8,8,16,150)"
    card = "#10101a" if solid else "rgba(20,20,34,170)"
    return f"""
* {{ font-family: 'Segoe UI'; color: #e2e2ee; outline: none; }}
#root {{ background: {bg}; }}
#side {{ background: {'#0a0a12' if solid else 'rgba(6,6,12,170)'}; border-right: 1px solid rgba(255,255,255,0.06); }}
#card {{ background: {card}; border: 1px solid rgba(255,255,255,0.07); border-radius: 14px; }}
#navbtn {{ text-align: left; padding: 10px 16px; border: none; border-radius: 10px; font-size: 14px; color: #b9b9d0;
          background: transparent; }}
#navbtn:hover {{ background: rgba(255,255,255,0.06); color: white; }}
#navbtn:checked {{ background: {a}; color: white; font-weight: 600; }}
QPushButton#primary {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {a}, stop:1 #b043d1); color: white;
          border: none; border-radius: 10px; padding: 10px 22px; font-weight: 600; font-size: 14px; }}
QPushButton#primary:hover {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #a78bfa, stop:1 #d058f0); }}
QPushButton#primary:pressed {{ padding-top: 12px; }}
QPushButton#ghost {{ background: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.10); border-radius: 10px;
          padding: 9px 16px; }}
QPushButton#ghost:hover {{ background: rgba(255,255,255,0.13); }}
QPushButton#chip {{ background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.08); border-radius: 15px;
          padding: 6px 14px; color: #b9b9d0; }}
QPushButton#chip:hover {{ background: rgba(255,255,255,0.12); color: white; }}
QPushButton#chip:checked {{ background: {a}; color: white; border-color: {a}; }}
QLineEdit {{ background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.10); border-radius: 10px;
          padding: 9px 12px; selection-background-color: {a}; }}
QLineEdit:focus {{ border: 1px solid {a}; }}
QComboBox {{ background: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.10); border-radius: 10px;
          padding: 8px 12px; min-width: 140px; }}
QComboBox QAbstractItemView {{ background: #14141f; border: 1px solid rgba(255,255,255,0.12); selection-background-color: {a}; }}
QProgressBar {{ background: rgba(255,255,255,0.08); border: none; border-radius: 4px; max-height: 8px; min-height: 8px;
          text-align: center; color: transparent; }}
QProgressBar::chunk {{ border-radius: 4px; background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
          stop:0 #4fd1e6, stop:0.5 {a}, stop:1 #b043d1); }}
QSlider::groove:horizontal {{ height: 6px; background: rgba(255,255,255,0.10); border-radius: 3px; }}
QSlider::sub-page:horizontal {{ background: {a}; border-radius: 3px; }}
QSlider::handle:horizontal {{ background: white; width: 18px; height: 18px; margin: -6px 0; border-radius: 9px; }}
QScrollBar:vertical {{ background: transparent; width: 12px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: rgba(255,255,255,0.22); border-radius: 4px; min-height: 40px; margin: 0 2px; }}
QScrollBar::handle:vertical:hover {{ background: rgba(255,255,255,0.40); }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical, QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {{ background: none; height: 0; }}
QTableView {{ background: transparent; border: none; gridline-color: transparent; }}
QHeaderView::section {{ background: transparent; color: #8d8da8; border: none; border-bottom: 1px solid rgba(255,255,255,0.08);
          padding: 8px 6px; font-size: 11px; font-weight: 600; }}
QScrollArea {{ background: transparent; border: none; }}
#scrollbody {{ background: transparent; }}
#muted {{ color: #8d8da8; }}
#h1 {{ font-size: 26px; font-weight: 700; }}
#h2 {{ font-size: 15px; font-weight: 600; }}
#toast {{ background: #1c1c2b; border: 1px solid {a}; border-radius: 10px; padding: 10px 16px; }}
"""


def apply_backdrop(win, on):
    """Acrílico/Mica do Windows 11 atrás da janela (precisa de fundo translúcido)."""
    try:
        hwnd = int(win.winId())
        dwm = ctypes.windll.dwmapi
        dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(ctypes.c_int(1)), 4)                  # barra de título escura
        dwm.DwmSetWindowAttribute(hwnd, 38, ctypes.byref(ctypes.c_int(3 if on else 1)), 4)     # 3 = acrílico, 1 = nenhum

        class M(ctypes.Structure):
            _fields_ = [("a", ctypes.c_int)] * 4
        dwm.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(M(-1 if on else 0, -1 if on else 0, -1 if on else 0, -1 if on else 0)))
    except Exception as e:
        print("blur indisponível:", e)


class GradientLabel(QLabel):
    def __init__(self, text, size=20, parent=None):
        super().__init__(text, parent)
        f = QFont("Segoe UI", size)
        f.setBold(True)
        self.setFont(f)
        self.setMinimumHeight(QFontMetrics(f).height() + 8)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        g = QLinearGradient(0, 0, QFontMetrics(self.font()).horizontalAdvance(self.text()), 0)
        for i, c in enumerate(STOPS):
            g.setColorAt(i / (len(STOPS) - 1), QColor(c))
        p.setPen(QPen(QBrush(g), 1))
        p.setFont(self.font())
        p.drawText(self.rect(), Qt.AlignVCenter | Qt.AlignLeft, self.text())


class Toggle(QAbstractButton):
    """Interruptor com animação (o mesmo que o app usaria nas configurações)."""

    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(46, 26)
        self._pos = 1.0 if checked else 0.0
        self.anim = QPropertyAnimation(self, b"pos_", self)
        self.anim.setDuration(160)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.toggled.connect(self._go)

    def _go(self, on):
        self.anim.stop()
        self.anim.setEndValue(1.0 if on else 0.0)
        self.anim.start()

    def get_pos(self):
        return self._pos

    def set_pos(self, v):
        self._pos = v
        self.update()

    pos_ = Property(float, get_pos, set_pos)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        off, on = QColor(255, 255, 255, 40), QColor(state["accent"])
        mix = lambda a, b, t: QColor(int(a.red() + (b.red() - a.red()) * t), int(a.green() + (b.green() - a.green()) * t),
                                     int(a.blue() + (b.blue() - a.blue()) * t), int(a.alpha() + (b.alpha() - a.alpha()) * t))
        p.setPen(Qt.NoPen)
        p.setBrush(mix(off, on, self._pos))
        p.drawRoundedRect(self.rect(), 13, 13)
        x = 3 + self._pos * (self.width() - 26)
        p.setBrush(QColor("white"))
        p.drawEllipse(QRectF(x, 3, 20, 20))


class FilesModel(QAbstractTableModel):
    HEAD = ["", "RISCO", "ARQUIVO", "TAMANHO", ""]

    def __init__(self, rows):
        super().__init__()
        self.all, self.rows, self.checked = rows, rows, set()
        self.level, self.query = None, ""

    def refilter(self):
        self.beginResetModel()
        q = self.query.lower()
        self.rows = [r for r in self.all if (self.level is None or r["level"] == self.level)
                     and (not q or q in r["path"].lower())]
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return 5

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.UserRole:
            return self.rows[index.row()]
        return None

    def headerData(self, s, o, role=Qt.DisplayRole):
        if o == Qt.Horizontal and role == Qt.DisplayRole:
            return self.HEAD[s]
        return None


class FilesDelegate(QStyledItemDelegate):
    action = Signal(int, str)

    def __init__(self, view):
        super().__init__(view)
        self.view = view

    def sizeHint(self, option, index):
        return QSize(100, 60)

    def _buttons(self, rect):
        w = 76
        b1 = QRectF(rect.left() + 6, rect.center().y() - 15, w, 30)
        b2 = QRectF(b1.right() + 8, b1.top(), 40, 30)
        return b1, b2

    def paint(self, p, option, index):
        r = index.model().rows[index.row()]
        p.save()
        p.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(option.rect)
        cursor = self.view.viewport().mapFromGlobal(QCursor.pos())
        hover = option.rect.contains(cursor) or (self.view.rowAt(cursor.y()) == index.row() and self.view.viewport().rect().contains(cursor))
        if hover or option.state & QStyle.State_Selected:
            c = QColor(state["accent"])
            c.setAlpha(55 if option.state & QStyle.State_Selected else 28)
            p.setPen(Qt.NoPen)
            p.setBrush(c)
            p.drawRoundedRect(rect.adjusted(2, 3, -2, -3), 10, 10)
        col = index.column()
        if col == 0:
            box = QRectF(rect.center().x() - 10, rect.center().y() - 10, 20, 20)
            on = index.row() in set(i for i, rr in enumerate(index.model().rows) if id(rr) in index.model().checked)
            p.setPen(QPen(QColor(255, 255, 255, 90), 1.5))
            p.setBrush(QColor(state["accent"]) if on else Qt.NoBrush)
            p.drawRoundedRect(box, 6, 6)
            if on:
                p.setPen(QPen(QColor("white"), 2.2, Qt.SolidLine, Qt.RoundCap))
                path = QPainterPath(QPoint(int(box.left() + 5), int(box.center().y())))
                path.lineTo(box.center().x() - 1, box.bottom() - 6)
                path.lineTo(box.right() - 4, box.top() + 6)
                p.drawPath(path)
        elif col == 1:
            f = QFont("Segoe UI", 8)
            f.setBold(True)
            p.setFont(f)
            tw = QFontMetrics(f).horizontalAdvance(r["label"]) + 22
            pill = QRectF(rect.left() + 6, rect.center().y() - 11, tw, 22)
            c = QColor(LEVEL_COLOR[r["level"]])
            bg = QColor(c)
            bg.setAlpha(45)
            p.setPen(QPen(c, 1))
            p.setBrush(bg)
            p.drawRoundedRect(pill, 11, 11)
            p.setPen(c.lighter(140))
            p.drawText(pill, Qt.AlignCenter, r["label"])
        elif col == 2:
            name = r["path"].rsplit("\\", 1)[-1]
            folder = r["path"].rsplit("\\", 1)[0]
            f1 = QFont("Segoe UI", 10)
            f1.setBold(True)
            f2 = QFont("Segoe UI", 8)
            p.setPen(QColor("#e8e8f4"))
            p.setFont(f1)
            w = rect.width() - 12
            p.drawText(QRectF(rect.left() + 6, rect.top() + 8, w, 20), Qt.AlignVCenter,
                       QFontMetrics(f1).elidedText(name, Qt.ElideRight, int(w)))
            p.setPen(QColor("#8d8da8"))
            p.setFont(f2)
            p.drawText(QRectF(rect.left() + 6, rect.top() + 30, w, 18), Qt.AlignVCenter,
                       QFontMetrics(f2).elidedText(f"{folder}  •  {r['reason']}", Qt.ElideRight, int(w)))
        elif col == 3:
            f = QFont("Segoe UI", 10)
            f.setBold(True)
            p.setFont(f)
            p.setPen(QColor("#e8e8f4"))
            p.drawText(rect.adjusted(0, 0, -10, 0), Qt.AlignVCenter | Qt.AlignRight, fmt_size(r["size"]))
        elif col == 4 and (hover or option.state & QStyle.State_Selected):
            b1, b2 = self._buttons(rect)
            for b, txt, danger in ((b1, "Mostrar", False), (b2, "🗑", True)):
                over = b.contains(cursor.x(), cursor.y())
                base = QColor("#dc2626") if danger else QColor(255, 255, 255)
                base.setAlpha(190 if danger and over else 120 if danger else 60 if over else 28)
                p.setPen(Qt.NoPen)
                p.setBrush(base)
                p.drawRoundedRect(b, 8, 8)
                p.setPen(QColor("white"))
                p.setFont(QFont("Segoe UI", 9))
                p.drawText(b, Qt.AlignCenter, txt)
        p.restore()

    def editorEvent(self, event, model, option, index):
        if event.type() == event.Type.MouseButtonRelease:
            pos = event.position().toPoint()
            r = model.rows[index.row()]
            if index.column() == 0:
                model.checked.symmetric_difference_update({id(r)})
                self.view.viewport().update()
                return True
            if index.column() == 4:
                b1, b2 = self._buttons(QRectF(option.rect))
                if b1.contains(pos.x(), pos.y()):
                    self.action.emit(index.row(), "show")
                elif b2.contains(pos.x(), pos.y()):
                    self.action.emit(index.row(), "trash")
                return True
        return False


class FilesView(QTableView):
    def __init__(self):
        super().__init__()
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)

    def mouseMoveEvent(self, e):
        super().mouseMoveEvent(e)
        self.viewport().update()
        col = self.columnAt(int(e.position().x()))
        self.viewport().setCursor(Qt.PointingHandCursor if col in (0, 4) else Qt.ArrowCursor)

    def leaveEvent(self, e):
        self.viewport().update()


class Toast(QLabel):
    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("toast")
        self.hide()
        self.t = QTimer(self, singleShot=True, timeout=self.hide)

    def show_text(self, text):
        self.setText(text)
        self.adjustSize()
        self.move((self.parent().width() - self.width()) // 2, self.parent().height() - 90)
        self.show()
        self.raise_()
        self.t.start(2200)


def card(layout=None):
    f = QFrame()
    f.setObjectName("card")
    if layout:
        f.setLayout(layout)
    return f


class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Demo B — PySide6 (Qt)")
        self.resize(1180, 780)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.root = QWidget()
        self.root.setObjectName("root")
        self.setCentralWidget(self.root)
        h = QHBoxLayout(self.root)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)

        side = QFrame()
        side.setObjectName("side")
        side.setFixedWidth(220)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(14, 22, 14, 14)
        sl.addWidget(GradientLabel("Faxina Várzea", 17))
        sub = QLabel("demo B • Qt")
        sub.setObjectName("muted")
        sl.addWidget(sub)
        sl.addSpacing(16)
        self.stack = QStackedWidget()
        self.navs = []
        for i, name in enumerate(["🏠  Início", "📊  Arquivos", "⚙  Ajustes"]):
            b = QPushButton(name)
            b.setObjectName("navbtn")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, i=i: self.go(i))
            sl.addWidget(b)
            self.navs.append(b)
        sl.addStretch()
        self.busy = QProgressBar()
        self.busy.setRange(0, 0)
        self.busy.hide()
        sl.addWidget(self.busy)
        foot = QLabel("feito na porra 💚💛")
        foot.setObjectName("muted")
        foot.setAlignment(Qt.AlignCenter)
        sl.addWidget(foot)
        h.addWidget(side)
        h.addWidget(self.stack, 1)

        self.stack.addWidget(self.home_page())
        self.stack.addWidget(self.files_page())
        self.stack.addWidget(self.settings_page())
        self.toast = Toast(self.root)
        self.go(0)
        self.restyle()

    # ---------------------------------------------------------------- páginas
    def title(self, text, sub):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(2)
        t = QLabel(text)
        t.setObjectName("h1")
        s = QLabel(sub)
        s.setObjectName("muted")
        l.addWidget(t)
        l.addWidget(s)
        return w

    def home_page(self):
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(30, 26, 30, 20)
        v.setSpacing(16)
        v.addWidget(self.title("Início", "Resumo do seu PC e uma faxina segura com um clique."))
        grid = QGridLayout()
        grid.setSpacing(12)
        for i, (t, val, sub) in enumerate([("💽 Espaço livre (C:)", "231.9 GB", "de 475.9 GB"), ("🧹 Dá pra limpar", "618.9 MB", "lixo seguro"),
                                           ("🚀 Abrem com o Windows", "7", "programas ligados"), ("🧠 Memória em uso", "78%", "12.4 GB de 15.9 GB")]):
            c = card()
            cl = QVBoxLayout(c)
            cl.setContentsMargins(16, 14, 16, 14)
            a = QLabel(t)
            a.setObjectName("muted")
            b = QLabel(val)
            b.setStyleSheet("font-size: 26px; font-weight: 700;")
            s = QLabel(sub)
            s.setObjectName("muted")
            for x in (a, b, s):
                cl.addWidget(x)
            grid.addWidget(c, 0, i)
        v.addLayout(grid)
        c = card()
        cl = QVBoxLayout(c)
        cl.setContentsMargins(20, 18, 20, 18)
        cl.setSpacing(10)
        row = QHBoxLayout()
        self.go_btn = QPushButton("⚡  Faxina rápida")
        self.go_btn.setObjectName("primary")
        self.go_btn.setCursor(Qt.PointingHandCursor)
        self.go_btn.clicked.connect(self.fake_scan)
        row.addWidget(self.go_btn)
        hint = QLabel("Limpa só o que é seguro: temporários, cache, lixeira e restos do Windows.")
        hint.setObjectName("muted")
        row.addWidget(hint, 1)
        cl.addLayout(row)
        self.prog = QProgressBar()
        self.prog.setRange(0, 100)
        self.prog.setValue(0)
        cl.addWidget(self.prog)
        self.prog_txt = QLabel("Pronto para começar.")
        self.prog_txt.setObjectName("muted")
        cl.addWidget(self.prog_txt)
        v.addWidget(c)
        v.addStretch()
        self.timer = QTimer(self, interval=40, timeout=self.step)
        return page

    def fake_scan(self):
        self.prog.setValue(0)
        self.go_btn.setEnabled(False)
        self.busy.show()
        self.timer.start()

    def step(self):
        v = self.prog.value() + 1
        self.prog.setValue(v)
        names = ["Arquivos temporários", "Cache dos navegadores", "Lixeira", "Miniaturas", "Relatórios de erro"]
        self.prog_txt.setText(f"→ {names[min(v // 21, 4)]}…  {v}%")
        if v >= 100:
            self.timer.stop()
            self.go_btn.setEnabled(True)
            self.busy.hide()
            self.prog_txt.setText("✅ Pronto! 618.9 MB liberados.")
            self.toast.show_text("✅ 618.9 MB liberados")

    def files_page(self):
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(30, 26, 30, 20)
        v.setSpacing(12)
        v.addWidget(self.title("Arquivos grandes", "Passe o mouse numa linha: aparecem os botões Mostrar e Lixeira."))
        bar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍  Filtrar por nome ou pasta…")
        self.search.textChanged.connect(self.on_search)
        bar.addWidget(self.search, 1)
        self.chips = []
        for txt, lvl in (("Todos", None), ("Seguros", "ok"), ("Cuidado", "care"), ("Perigo", "danger")):
            b = QPushButton(txt)
            b.setObjectName("chip")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, l=lvl, b=b: self.on_chip(l, b))
            bar.addWidget(b)
            self.chips.append(b)
        self.chips[0].setChecked(True)
        clean = QPushButton("🧹  Apagar todos os seguros")
        clean.setObjectName("primary")
        clean.setCursor(Qt.PointingHandCursor)
        clean.clicked.connect(lambda: self.toast.show_text("🧹 Mandaria os seguros para a lixeira"))
        bar.addWidget(clean)
        v.addLayout(bar)

        self.model = FilesModel(make_rows(300))
        self.view = FilesView()
        self.view.setModel(self.model)
        d = FilesDelegate(self.view)
        d.action.connect(lambda row, what: self.toast.show_text(("📂 Mostrar: " if what == "show" else "🗑 Lixeira: ") + self.model.rows[row]["path"]))
        self.view.setItemDelegate(d)
        self.view.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.view.verticalScrollBar().setSingleStep(18)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setShowGrid(False)
        self.view.verticalHeader().hide()
        self.view.verticalHeader().setDefaultSectionSize(60)
        hh = self.view.horizontalHeader()
        hh.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        hh.setHighlightSections(False)
        hh.setSectionResizeMode(QHeaderView.Fixed)
        hh.setSectionResizeMode(2, QHeaderView.Stretch)
        self.view.setColumnWidth(0, 50)
        self.view.setColumnWidth(1, 120)
        self.view.setColumnWidth(3, 100)
        self.view.setColumnWidth(4, 150)
        self.view.setFrameShape(QFrame.NoFrame)
        c = card()
        cl = QVBoxLayout(c)
        cl.setContentsMargins(8, 4, 8, 8)
        cl.addWidget(self.view)
        v.addWidget(c, 1)
        self.count = QLabel("")
        self.count.setObjectName("muted")
        v.addWidget(self.count)
        self.update_count()
        return page

    def on_search(self, t):
        self.model.query = t
        self.model.refilter()
        self.update_count()

    def on_chip(self, lvl, btn):
        for b in self.chips:
            b.setChecked(b is btn)
        self.model.level = lvl
        self.model.refilter()
        self.update_count()

    def update_count(self):
        self.count.setText(f"{len(self.model.rows)} arquivos • {len(self.model.checked)} marcados")

    def settings_page(self):
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(30, 26, 0, 10)
        v.addWidget(self.title("Ajustes", "Tudo que dá pra personalizar. Role rápido pra testar o desenho."))
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        body = QWidget()
        body.setObjectName("scrollbody")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(0, 8, 30, 20)
        bl.setSpacing(10)

        lab = QLabel("🎨 Aparência")
        lab.setObjectName("h2")
        bl.addWidget(lab)
        c = card()
        cl = QVBoxLayout(c)
        cl.setContentsMargins(18, 14, 18, 14)
        cl.addWidget(QLabel("Cor de destaque (clique pra trocar ao vivo)"))
        sw = QHBoxLayout()
        for col in ACCENTS:
            b = QPushButton()
            b.setFixedSize(34, 34)
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet(f"background:{col}; border-radius:17px; border:2px solid rgba(255,255,255,0.25);")
            b.clicked.connect(lambda _=False, col=col: self.set_accent(col))
            sw.addWidget(b)
        sw.addStretch()
        cl.addLayout(sw)
        r = QHBoxLayout()
        r.addWidget(QLabel("Blur (acrílico do Windows 11) atrás da janela"), 1)
        t = Toggle(True)
        t.toggled.connect(self.set_blur)
        r.addWidget(t)
        cl.addLayout(r)
        r = QHBoxLayout()
        r.addWidget(QLabel("Intensidade"), 1)
        s = QSlider(Qt.Horizontal)
        s.setFixedWidth(220)
        s.setValue(60)
        r.addWidget(s)
        cl.addLayout(r)
        r = QHBoxLayout()
        r.addWidget(QLabel("Fonte"), 1)
        cb = QComboBox()
        cb.addItems(["Segoe UI", "Inter", "JetBrains Mono"])
        r.addWidget(cb)
        cl.addLayout(r)
        bl.addWidget(c)

        lab = QLabel("⚡ Desempenho e privacidade")
        lab.setObjectName("h2")
        bl.addWidget(lab)
        for name, desc, on in SETTINGS:
            c = card()
            r = QHBoxLayout(c)
            r.setContentsMargins(18, 12, 18, 12)
            tx = QVBoxLayout()
            tx.setSpacing(1)
            a = QLabel(name)
            a.setStyleSheet("font-weight: 600; font-size: 14px;")
            b = QLabel(desc)
            b.setObjectName("muted")
            tx.addWidget(a)
            tx.addWidget(b)
            r.addLayout(tx, 1)
            r.addWidget(Toggle(on))
            bl.addWidget(c)
        bl.addStretch()
        sc.setWidget(body)
        v.addWidget(sc, 1)
        return page

    # ----------------------------------------------------------------- tema
    def go(self, i):
        self.stack.setCurrentIndex(i)
        for k, b in enumerate(self.navs):
            b.setChecked(k == i)

    def restyle(self):
        QApplication.instance().setStyleSheet(qss())
        apply_backdrop(self, state["blur"])
        self.root.update()

    def set_accent(self, col):
        state["accent"] = col
        self.restyle()
        for w in self.findChildren(Toggle):
            w.update()

    def set_blur(self, on):
        state["blur"] = on
        self.restyle()

    def resizeEvent(self, e):
        super().resizeEvent(e)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = Main()
    scr = QApplication.screens()
    if len(sys.argv) > 1 and sys.argv[1] == "second" and len(scr) > 1:
        g = scr[1].geometry()
        w.move(g.x() + 40, g.y() + 30)
    if len(sys.argv) > 2:
        w.setWindowFlag(Qt.WindowStaysOnTopHint, True)      # só no modo de captura de tela
    w.show()
    apply_backdrop(w, True)
    if len(sys.argv) > 2:
        import os
        from PIL import ImageGrab

        def snap():
            x, y = w.mapToGlobal(QPoint(0, 0)).x(), w.mapToGlobal(QPoint(0, 0)).y()
            r = w.devicePixelRatioF()
            ImageGrab.grab(bbox=(int(x * r), int(y * r), int((x + w.width()) * r), int((y + w.height()) * r)),
                           all_screens=True).save(sys.argv[2] + "_" + str(snap.n) + ".png")
            snap.n += 1
        snap.n = 0
        QTimer.singleShot(1500, snap)
        QTimer.singleShot(1800, lambda: w.go(1))
        QTimer.singleShot(3500, snap)
        QTimer.singleShot(3800, lambda: w.view.verticalScrollBar().setValue(2400))
        QTimer.singleShot(4800, snap)
        QTimer.singleShot(5000, lambda: w.go(2))
        QTimer.singleShot(6500, snap)
        QTimer.singleShot(6600, lambda: w.go(0))
        QTimer.singleShot(6700, w.fake_scan)
        QTimer.singleShot(8200, snap)
        QTimer.singleShot(9500, app.quit)
    sys.exit(app.exec())
