---
tags: [backend]
arquivos: [settings.py, single.py, tray.py, overlay.py, version.py, make_icon_webdark.py]
---
# Utilitários

| Arquivo | Função |
|---|---|
| `settings.py` | `load`/`save` de `preferences.json` (`DEFAULTS`: background, scan_minutes, last_notice, tray_tip_shown; tema e ajuda também vão aqui) |
| `single.py` | `acquire(wait)` (uma instância só), `focus_existing(title)` |
| `tray.py` | `class Tray` (pystray): `start`, `stop`, `notify` — modo segundo plano |
| `overlay.py` | `class Overlay` (Tk, sempre por cima) e `describe(...)`: texto/cor da temperatura no canto da tela |
| `version.py` | `VERSION`, `REPO` |
| `make_icon_webdark.py` | gera o ícone ([[Build e release]]) |
