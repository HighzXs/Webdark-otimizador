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
| Ícones | `ICON(nome, classe)`: SVG de traço único (home, space, apps, speed, protect, help, settings, refresh, shield). **Não usar emoji como ícone** em menu, abas, títulos e botões novos |
| Rotas | `Pages`, **`NAV`** (menu: `[id, rótulo]`, o ícone vem de `ICON(id)`), `go(id, tab)`, `makeGroup(title, sub, tabs)` |
| Início | `boot()`: monta menu, `api.info()` → `window.INFO` (admin, versão, drives, tema), botão de admin |

Ver [[Arquitetura]], [[Eventos]], [[Receitas]].
