---
tags: [backend, entrada]
arquivo: webapp.py
---
# webapp.py — ponto de entrada

- `main()`: trata `--selftest` / `--relaunch-test`, garante instância única (`single.acquire`; espera 12 s se veio `--elevated`), cria a janela pywebview (1200×820, mín. 980×640) com `js_api=Api()`.
- `on_start()`: barra de título escura (`dark_titlebar`), `api.make_overlay()`, bandeja se o segundo plano estiver ligado, checagem de atualização após 8 s.
- `resource(nome)`: caminho de arquivo empacotado (`sys._MEIPASS` no .exe).
- `python webapp.py second` abre na segunda tela (testes).

## Instância única e segundo plano
- Abrir o .exe de novo com o app na bandeja: `single.acquire` falha → `single.focus_existing(TITLE)` mostra a janela escondida (ShowWindow + Alt + BringWindowToTop + SetForegroundWindow) e o processo novo sai.
- **Reabrir como administrador** (`Api.relaunch_admin`): usa `Api.quit` (não `window.destroy`). Motivo: no modo segundo plano `_on_closing` só esconde a janela, o processo antigo ficava vivo segurando o mutex e o processo elevado desistia após 12 s (bug corrigido em 2026-11-02).
- Limite: com o app já elevado, um .exe aberto sem admin não consegue mostrar a janela dele (UIPI); fechar pela bandeja.
- Testado no .exe buildado: selftest ok; janela escondida volta ao abrir o .exe de novo; sobra uma única instância. O fluxo com UAC não é automatizável, testar à mão.

Ver [[Build e release]], [[webapi.py]], [[Utilitários]].
