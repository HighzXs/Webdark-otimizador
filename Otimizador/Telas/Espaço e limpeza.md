---
tags: [tela, grupo]
id: space
js: [web/pages.js, web/pages3.js, web/pages6.js]
---
# 🧹 Espaço e limpeza (`Pages.space`)

Grupo montado em `web/pages6.js`. Abas:

| Aba (id) | Objeto JS | Arquivo | Api ([[webapi.py]]) | Python | Eventos |
|---|---|---|---|---|---|
| Limpeza (`clean`) | `Pages.clean` | pages3.js | `clean_list`, `clean_run`, `extras_info`, `hibernate_off`, `open_cleanmgr`, `dism_cleanup` | [[backend.py]]: `make_cleaners`, `measure`, `run_cleaner`, `hibernate_off`, `component_cleanup`, `open_windows_cleanmgr` | `cl:*` |
| Pastas (`dirs`) | `SpaceTabs.dirs` | pages3.js | `dirs_scan`, `reveal` | `backend.scan_children` | `dirs:list` |
| Arquivos grandes (`files`) | `SpaceTabs.files` | pages.js | `scan_files`, `cancel_scan`, `trash`, `reveal` | `backend.find_big_files` + [[risk.py]] `assess` | `scan:progress`, `scan:done` |
| Duplicados (`dups`) | `SpaceTabs.dups` | pages3.js | `dups_scan`, `dups_trash` | `backend.find_duplicates` | `dups:progress`, `dups:done` |
| Downloads antigos (`dl`) | `SpaceTabs.dl` | pages3.js | `dl_scan`, `trash` | `system.old_downloads` | `dl:done` |

- Itens de limpeza (caches de navegador, Steam, apps, temp…) são definidos em `backend.make_cleaners` (`_browser_caches`, `_app_caches`).
- Cancelamento: `Api._cancels[...]` (`dirs`, `dups`, `dl`, `files`).
- Apagar só o que o escaneamento achou (`Api._found`), sempre para a lixeira.
- Helpers JS de pages3.js: `driveOptions`, `riskPill`.
