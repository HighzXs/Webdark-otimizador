---
tags: [tela]
id: home
js: web/pages.js
---
# 🏠 Início (`Pages.home`)

**JS**: `web/pages.js` → `Pages.home`. Banner de atualização: `updBanner` em `web/pages5.js`.

| O quê | Api ([[webapi.py]], seção "início") | Python | Eventos |
|---|---|---|---|
| Resumo do disco/lixo | `summary` | `backend.quick_summary` | `summary` |
| CPU/RAM ao vivo | `live` | psutil | — |
| Ficha do PC | `specs` | `system.format_specs` | `specs` |
| Limpeza rápida | `quick_clean` | `backend.make_cleaners` / `run_cleaner` | `clean:step`, `clean:done`, `clean:freed` |
| Ponto de restauração | `restore_point` | `backend.create_restore_point` | — |
| Procurar atualização | `update_check_now` | [[updater.py]] | `update:*` |

Ver [[Eventos]], [[Arquitetura]].
