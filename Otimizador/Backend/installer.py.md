---
tags: [backend, instalacao]
arquivo: installer.py
---
# installer.py — instalar como aplicativo do Windows

Por usuário (HKCU), sem admin.

| O quê | Onde |
|---|---|
| Pasta do programa | `INSTALL_DIR` = `%LOCALAPPDATA%\Programs\WebDark`, `EXE` = `…\WebDark.exe` |
| Atalho do menu Iniciar (pesquisa) | `START_LNK` = `%APPDATA%\Microsoft\Windows\Start Menu\Programs\WebDark Otimizador.lnk` |
| Atalho da Área de Trabalho | `_desktop_lnk()` (só na instalação; se o usuário apagar, não volta) |
| "Aplicativos instalados" | `UNINST_KEY` = `HKCU\…\Uninstall\WebDark` (`UninstallString` = `"EXE" --uninstall`) |

## Fluxo ([[webapp.py]] `main`)
- `--uninstall` → `uninstall()`: exige o app fechado (`single.acquire`), apaga atalhos e chave e chama um .bat que apaga a pasta depois que o processo sai. As configurações em `%APPDATA%\FaxinaVarzea` ficam.
- .exe solto (ex.: Downloads, não é o `EXE`, sem `--elevated`) → `offer(prefs)`:
  - já instalado com versão ≥ → abre o instalado e sai;
  - instalado mais velho → pergunta se quer atualizar a instalação;
  - não instalado → pergunta uma vez só (`prefs["install_asked"]`); se aceitar, `install()` copia o .exe, cria atalhos e abre o instalado.
- Cópia instalada aberta → `register()` numa thread em `on_start` (mantém atalho e `DisplayVersion` em dia depois do [[updater.py]]).

Atalhos são criados pelo PowerShell (`WScript.Shell`, `_shortcut`). Avisos usam `MessageBoxW` (antes da janela existir).

Testado em 2026-11-02 com pastas falsas: instalar/desinstalar ok. Ver [[Build e release]].
