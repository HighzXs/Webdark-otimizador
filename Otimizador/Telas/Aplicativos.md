---
tags: [tela, grupo]
id: apps
js: web/pages2.js
---
# 📦 Aplicativos (`Pages.apps`)

Grupo em `web/pages6.js`. Abas em `web/pages2.js`:

| Aba (id) | Objeto | Api ([[webapi.py]]) | Python ([[backend.py]]) | Eventos |
|---|---|---|---|---|
| Bloatware (`bloat`) | `Pages.bloat` | `bloat_scan`, `bloat_remove` | `list_appx`, `remove_appx`, regras `BLOAT_RULES`, `PROTECTED`, `HIDE_PREFIX` | `bloat:list`, `bloat:log`, `bloat:done` |
| Programas instalados (`progs`) | `Pages.progs` | `progs_scan`, `prog_uninstall`, `progs_uninstall_many`, `progs_queue_skip`, `progs_queue_stop` | `list_programs`, `launch_uninstaller`, `uninstall_and_wait`, `SUSPECT` | `progs:list`, `progs:q`, `progs:qdone` |

- **Desinstalar em lote**: fila na Api (`_uq_busy`, `_uq_skip`, `_uq_cancel`). `uninstall_and_wait` espera o desinstalador e os processos filhos (`_descendants`) e confere se a chave do registro sumiu (`regkey_exists`).
- Categorias do bloatware na tela: `LEVEL_TITLE` (lixo / opcional / outro).
