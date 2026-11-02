---
tags: [tela]
id: settings
js: [web/pages.js, web/pages5.js]
---
# 🎨 Ajustes (`Pages.settings`)

**JS**: `web/pages.js` → `Pages.settings` (tema). O bloco "modo segundo plano" vem de `web/pages5.js`.

| O quê | Api ([[webapi.py]]) | Onde fica |
|---|---|---|
| Tema (cor, blur, fonte, brilho) | `set_theme` | `THEME_DEFAULT`, `applyTheme`, `saveTheme` em [[core.js]]; variáveis CSS em [[CSS]] |
| Segundo plano / bandeja | `bg_get`, `bg_set` | `Api._tray_start`, [[Utilitários]] tray.py |
| Sair de vez | `quit` | `Api.quit`; evento `confirm_close` ao fechar a janela |
