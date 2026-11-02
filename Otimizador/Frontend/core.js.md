---
tags: [frontend]
arquivo: web/core.js
---
# web/core.js — base da interface

| Parte | O quê |
|---|---|
| Helpers | `$`, `$$` (respeitam `muted`), `esc`, `fmt` |
| Eventos | `handlers`, `window.__emit`, `on(evento, fn)`, **`OWNER`** (prefixo → tela dona), `current`, `curPage`, `INTAB` |
| Python | `ready`, `api` (Proxy → `window.pywebview.api`) |
| Avisos | `toast`, `adminPrompt`, `confirmBox`, `choiceBox`, `inputBox`, `busy` |
| Tema | `THEME_DEFAULT`, `applyTheme`, `saveTheme` |
| Rotas | `Pages`, **`NAV`** (menu), `go(id, tab)`, `makeGroup(title, sub, tabs)` |
| Início | `boot()`: monta menu, `api.info()` → `window.INFO` (admin, versão, drives, tema), botão de admin |

Ver [[Arquitetura]], [[Eventos]], [[Receitas]].
