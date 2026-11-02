---
tags: [tela]
id: help
js: web/pageshelp.js
---
# 💡 Ajuda (`Pages.help`)

**JS**: `web/pageshelp.js`.
- `TIPS`: dicas por tela/aba (id → lista). Ao criar aba nova, adicione aqui.
- `PLAN`: passos do plano de otimização. `TOPICS`: tópicos da tela de ajuda.
- Botão 💡 flutuante: `helpToggle`, `helpRefresh` (chamado por `go()` e `makeGroup` em [[core.js]]).
- "Mostrar onde fica": `pointTo(seletor)`, `goAndPoint(tela, seletor)`.
- **Otimização guiada (professor)**: botão "Me guie" no topo da tela Ajuda → `Tutor.start()`. `TUTOR` (mesma chave do `PLAN`) tem o texto curto "o que faz" + "o que clicar" de cada passo. O cartão flutuante `#tutor` (CSS `.tt-*` em components.css) leva à tela (`goAndPoint`), acende o botão e deixa o usuário clicar no real; "Feito, próximo" marca o passo em `HELP.done`. Passo novo no `PLAN` precisa de entrada no `TUTOR`.
- Progresso salvo: `api.help_state` / `api.help_save` → `preferences.json` (`_prefs["help"]`).
