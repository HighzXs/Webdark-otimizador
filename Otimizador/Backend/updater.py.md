---
tags: [backend, atualizacao]
arquivo: updater.py
---
# updater.py — atualização automática

GitHub Releases de `REPO` ([[Build e release]]). `check()` → `Update` (versão, notas, url) ou nada. `download(up, progress)` baixa o .exe, `_trusted(url)` só aceita github.com / githubusercontent.com. `can_self_update()`, `apply(new_path)` troca o executável e reabre.

## Permissões (bug corrigido em 2026-11-02)
- `download` **não** usa `tempfile.mkdtemp`: no Python 3.13+ ele cria a pasta com ACL só para SISTEMA/Administradores/dono. O .exe baixado pelo app elevado herdava isso, e o Explorer sem admin dava "O Windows não pode acessar o dispositivo, caminho ou arquivo especificado".
- O `atualizar.bat` usa `copy /b /y` por cima do .exe antigo (mantém a permissão dele), e não `move` (que levaria a ACL da pasta temporária).
- Conserto de um .exe já estragado: `icacls "<caminho>\WebDark.exe" /reset` num terminal como administrador.
