---
tags: [backend, atualizacao]
arquivo: updater.py
---
# updater.py — atualização automática

GitHub Releases de `REPO` ([[Build e release]]). `check()` → `Update` (versão, notas, url) ou nada. `download(up, progress)` baixa o .exe, `_trusted(url)` só aceita github.com / githubusercontent.com. `can_self_update()`, `apply(new_path)` troca o executável e reabre.
