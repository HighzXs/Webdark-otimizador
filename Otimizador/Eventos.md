---
tags: [mapa, eventos]
---
# Eventos (Python → JS)

Emitidos em [[webapi.py]] por `self._emit(...)`. Escutados com `on("evento", fn)` no JS. O dono vem do `OWNER` em [[core.js]].

| Prefixo | Tela dona | Eventos | JS |
|---|---|---|---|
| `summary`, `clean:*`, `specs` | home | `summary`, `clean:step`, `clean:done`, `clean:freed`, `specs` | pages.js ([[Início]]) |
| `scan:*` | files | `scan:progress`, `scan:done` | pages.js (Arquivos grandes) |
| `cl:*` | clean | `cl:list`, `cl:size`, `cl:sized`, `cl:step`, `cl:log`, `cl:done`, `cl:dism_done` | pages3.js (Limpeza) |
| `dirs:*` | dirs | `dirs:list` | pages3.js |
| `dups:*` | dups | `dups:progress`, `dups:done` | pages3.js |
| `dl:*` | dl | `dl:done` | pages3.js |
| `bloat:*` | bloat | `bloat:list`, `bloat:log`, `bloat:done` | pages2.js |
| `progs:*` | progs | `progs:list`, `progs:q`, `progs:qdone` | pages2.js |
| `start:*` | start | `start:list`, `start:bulk` | pages2.js |
| `proc:*` | proc | (sem evento, resposta direta) | pages2.js |
| `health:*` | health | `health:disks`, `health:diag`, `health:upd`, `health:log`, `health:repair_done` | pages4.js |
| `sys:*`, `perf:*` | perf | `sys:state`, `sys:applied`, `perf:clock`, `perf:log`, `perf:opt_done` | pages4.js |
| `sec:*` | security | `sec:cfg`, `sec:tick` | pages5.js |
| `net:*` | net | `net:dns`, `net:dns_progress`, `net:drivers`, `net:drvupd`, `net:log`, `net:repair_done` | pagesnet.js |
| (sem dono) | global | `error`, `confirm_close`, `update:available`, `update:progress`, `update:failed` | core.js / pages5.js |

Alguns nomes são montados em f-string (ex.: `…:log`, `…_done`): procure pelo prefixo em webapi.py.
