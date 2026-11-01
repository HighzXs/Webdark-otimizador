"""Ícone na bandeja do Windows para o modo segundo plano."""
import pystray
from PIL import Image


class Tray:
    def __init__(self, app, icon_path, title, on_open, on_scan, on_quit):
        self.app, self.icon = app, None
        self._image = Image.open(icon_path)
        self._title = title
        self._on_open, self._on_scan, self._on_quit = on_open, on_scan, on_quit

    def start(self):
        if self.icon is not None:
            return
        # os cliques chegam na thread do ícone: passa para a thread da interface
        post = lambda fn: (lambda icon, item: self.app.post(fn))  # noqa: E731
        menu = pystray.Menu(
            pystray.MenuItem("Abrir", post(self._on_open), default=True),
            pystray.MenuItem("Verificar agora", post(self._on_scan)),
            pystray.MenuItem("Sair de vez", post(self._on_quit)),
        )
        self.icon = pystray.Icon("FaxinaVarzea", self._image, self._title, menu)
        self.icon.run_detached()

    def stop(self):
        if self.icon is not None:
            try:
                self.icon.stop()
            finally:
                self.icon = None

    def notify(self, title, message):
        if self.icon is not None:
            try:
                self.icon.notify(message, title)
            except Exception:
                pass
