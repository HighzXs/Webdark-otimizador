---
tags: [mapa, receitas]
---
# Receitas

## Botão que chama o Python
1. Método público novo na `Api` em [[webapi.py]], na seção da tela (seções são comentários `# ---- nome`).
2. Lógica pesada vai no módulo certo (ver [[00 Índice]] → Backend), não na Api.
3. No JS da tela: `const r = await api.meu_metodo(args)`.
4. Se demora: `self._thread(...)` + `self._emit("prefixo:done", dados)`, e `on("prefixo:done", ...)` no JS. Atualize [[Eventos]].

## Nova aba numa tela existente
1. Crie o objeto (`Pages.x = (() => { ...; return { mount(el) {...} }; })()`) num pages*.js.
2. Registre a aba no grupo em `web/pages6.js` (`["x", "🔧 Nome", Pages.x]`).
3. Ponha o prefixo dos eventos no `OWNER` em [[core.js]].
4. Use `head(title, sub)` (pages2.js): dentro de aba ele vira só a legenda.
5. Adicione dicas em `TIPS` em `web/pageshelp.js` ([[Ajuda]]).

## Nova tela no menu
1. Item em `NAV` em [[core.js]] (`[id, ícone, rótulo]`).
2. `Pages.<id>` num pages*.js (ou arquivo novo incluído em [[index.html]] antes de pages6.js).

## Caixas de diálogo e avisos (core.js)
`toast(texto)`, `confirmBox({title, body, ok, danger})`, `choiceBox({title, options})`, `inputBox({...})`, `adminPrompt(texto)`, `busy(+1/-1)`. Helpers: `$`, `$$`, `esc` (escapar HTML, **sempre** usar em texto vindo do sistema), `fmt` (bytes).

## Estilo e cores
Ver [[CSS]]. Cor de destaque vem do tema do usuário (`--accent`).

## Nova versão
Ver [[Build e release]].
