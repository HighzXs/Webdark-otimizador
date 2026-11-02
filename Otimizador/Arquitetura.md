---
tags: [mapa, arquitetura]
---
# Arquitetura

App desktop Windows. Janela **pywebview** (WebView2/edgechromium) mostra o HTML de `web/`. A lógica fica em Python.

```
webapp.py  ──cria janela──►  web/index.html  (core.js + pages*.js)
    │                             │  api.<metodo>(...)   (Proxy em core.js → window.pywebview.api)
    ▼                             ▼
webapi.py: class Api  ◄───────────┘
    │  _emit("evento", dados) ──► window.__emit ──► on("evento", fn) no JS
    ▼
módulos: backend, thermal, netopt, system, health, startup, cpu, tweaks, risk, updater
```

## Regras que importam
- **JS → Python**: todo método público de `Api` em [[webapi.py]] vira `api.nome()` no JS. Métodos com `_` no início ficam escondidos do JS.
- **Tarefa longa**: o método da Api chama `self._thread(fn)` e retorna na hora. O resultado chega por evento `_emit`. Exceção vira o evento `error` (o JS mostra toast).
- **Muitos avisos de progresso**: `self._throttled("evento")` (no máximo um a cada 0,25 s).
- **Dono do evento**: o prefixo antes de `:` (ex.: `dups:done` → `dups`) é ligado a uma tela pelo `OWNER` em [[core.js]]. Se a tela não está aberta, o handler roda "mudo" (`$` devolve null) só para guardar estado. **Prefixo novo precisa entrar no `OWNER`.**
- **Telas**: cada tela é um objeto `Pages.<id>` (ou `SpaceTabs.<id>`) com `mount(el)` e, se quiser, `show`, `unmount`, `info`. Telas com abas são montadas por `makeGroup()` em `web/pages6.js`.
- **Ordem dos scripts** em [[index.html]]: core → pages → pages2…5 → pagesnet → pages6 (grupos; precisa vir depois das abas) → pageshelp.
- **Admin**: o app roda sem admin. `window.INFO.admin` diz se é admin; `needAdmin()` (pages4.js) bloqueia ações. `Api.relaunch_admin` reabre elevado (`backend.relaunch_as_admin`).
- **Proteção ao apagar**: `Api._found` guarda o que o último escaneamento achou. `trash`/`dups_trash` só apagam caminhos dessa lista, e mandam para a lixeira (send2trash).
- **Uma instância só**: `single.acquire` em [[webapp.py]].

## Dados no disco (%APPDATA%\FaxinaVarzea\)
| Arquivo | Quem usa | Conteúdo |
|---|---|---|
| `preferences.json` | settings.py ([[Utilitários]]) | tema, ajuda, segundo plano, minutos |
| `settings.json` | [[thermal.py]] | config do vigia de temperatura / curva |
| `history.json` | [[backend.py]] | histórico do quanto foi limpo |

## Dependências
pywebview, pythonnet, psutil, pystray, Pillow, send2trash. Quase tudo do Windows passa por PowerShell (`backend.ps` / `ps_stream`), `powercfg`, registro (`winreg`) e ctypes.
