---
tags: [frontend, estilo]
arquivos: [web/theme.css, web/components.css]
---
# CSS

- **web/theme.css**: variáveis em `:root` (`--accent`, `--glass`, `--blurpx`, `--glow`, `--font`, `--muted`, `--line`…; algumas são trocadas por `applyTheme` em [[core.js]]) e o layout: `.app` (grid menu 236px + conteúdo), `aside`, `.logo`, `.stage`, `.page`, `.busy`.
- **web/components.css**: peças reutilizáveis — `.card`, `.tiles/.tile`, `.btn`, `.ghost`, `.chip`, `.tabs`, `.tabbody`, `.list`, `.row`, `.cb`, `.pill`, `.tag`, `.bar`, `.meter`, `.sw` (interruptor), `.set`, `.logbox`, `.modal/.dialog`, `.empty`, `.tools`, `.filters`, `.fld`. Seções no fim: aviso de atualização (`.updside`, `.updbar`), admin (`.admincta`, `.adminnote`), Início (`.specs`, `.spec`, `.drv`, `.live`).

Antes de criar classe nova, procure uma parecida aqui.

## Regras do visual (refinado em 2026-11-15 com as skills design-taste-frontend e impeccable)
- Cor de destaque **lisa** em botão, barra e marca: sem degradê, sem brilho (`box-shadow` colorido) e sem pulsar.
- Menu: item ativo = pílula neutra (`rgba(255,255,255,.09)`) com o ícone na cor de destaque.
- Abas das telas-mãe (`.tabs .chip`): texto com linha de 2px embaixo, sobre um fio de 1px. Chips fora de `.tabs` continuam pílula.
- Rótulos em sentence case (nada de caixa-alta espaçada). Números em `tabular-nums`.
- `.scroll` tem 72px de folga embaixo para o botão de dicas (`#helpfab`) nunca cobrir conteúdo.
- Fundo com brilho, desfoque e fonte continuam escolha do usuário em Ajustes (`--glow`, `--blurpx`, `--font`).
- Aba Jogos: `.gc-*` (lista em painel, ponto de status). Bloco neutro: `.autonote`; `.adminnote` é só para aviso de administrador.
