---
tags: [frontend, estilo]
arquivos: [web/theme.css, web/components.css]
---
# CSS

- **web/theme.css**: variáveis em `:root` (`--accent`, `--glass`, `--blurpx`, `--glow`, `--font`, `--muted`, `--line`…; algumas são trocadas por `applyTheme` em [[core.js]]) e o layout: `.app` (grid menu 236px + conteúdo), `aside`, `.logo`, `.stage`, `.page`, `.busy`.
- **web/components.css**: peças reutilizáveis — `.card`, `.tiles/.tile`, `.btn`, `.ghost`, `.chip`, `.tabs`, `.tabbody`, `.list`, `.row`, `.cb`, `.pill`, `.tag`, `.bar`, `.meter`, `.sw` (interruptor), `.set`, `.logbox`, `.modal/.dialog`, `.empty`, `.tools`, `.filters`, `.fld`. Seções no fim: aviso de atualização (`.updside`, `.updbar`), admin (`.admincta`, `.adminnote`), Início (`.specs`, `.spec`, `.drv`, `.live`).

Antes de criar classe nova, procure uma parecida aqui.
