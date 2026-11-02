---
tags: [backend, ponte]
arquivo: webapi.py
---
# webapi.py — `class Api`

Ponte JS ↔ Python. Todo método público vira `api.<nome>()` no JS. Ver [[Arquitetura]].

## Infra (privado)
`_emit(evento, dados)`, `_throttled(evento, gap)`, `_thread(fn)`, `_shutdown`, `_guard_loop` (vigia de temperatura), `_tray_start`.
Estado no `__init__`: `_prefs`, `_cancels`, `_found`, `_appx/_progs/_starts/_procs` (resultado da última busca por id), `_cleaners`, `_dups`, `_tweaks`, fila de desinstalação `_uq_*`, `_cfg/_sensor/_guard` (thermal).

## Seções (comentários `# ---- nome`, na ordem do arquivo)
| Seção | Métodos | Tela |
|---|---|---|
| geral | `info`, `set_theme`, `help_state`, `help_save`, `relaunch_admin`, `reveal` | global |
| início | `summary`, `live`, `specs`, `quick_clean` | [[Início]] |
| segurança | `sec_state`, `sec_open`, `sec_save`, `sec_preset`, `sec_suggest`, `sec_import`, `sec_events`, `sec_procs`, `make_overlay` | [[Saúde e proteção]] |
| bandeja / janela | `attach`, `quit`, `bg_get`, `bg_set` | [[Ajustes]] |
| atualização | `update_check`, `update_check_now`, `update_apply` | [[Build e release]] |
| rede | `net_*` | [[Velocidade]] |
| memória | `mem_scan`, `mem_groups`, `mem_deep`, `mem_standby`, `mem_trim`, `mem_trim_all`, `mem_lower`, `mem_freeze`, `mem_unfreeze`, `mem_pagefile_apply`, `mem_pagefile_auto`, `mem_svchost_set`, `mem_sysmain_set`, `mem_auto_get`, `mem_auto_set`, `svc_list`, `svc_set`, `svc_bulk` (módulos [[svcopt.py]] e [[mem.py]]; `_freezer` no `__init__`, descongela em `_shutdown`) | [[Velocidade]] |
| saúde | `health_scan`, `updates_check`, `repair` | [[Saúde e proteção]] |
| desempenho | `power_*`, `tweaks_list`, `tweak_set`, `systweaks_scan`, `systweak_set`, `trim_enable`, `optimize_disk`, `clock_*` | [[Velocidade]] |
| limpeza | `clean_list`, `clean_run`, `extras_info`, `hibernate_off`, `open_cleanmgr`, `dism_cleanup`, `restore_point` | [[Espaço e limpeza]] |
| pastas / duplicados / downloads | `dirs_scan`, `dups_scan`, `dups_trash`, `dl_scan` | [[Espaço e limpeza]] |
| bloatware | `bloat_scan`, `bloat_remove` | [[Aplicativos]] |
| programas | `progs_scan`, `prog_uninstall`, `progs_uninstall_many`, `progs_queue_skip`, `progs_queue_stop` | [[Aplicativos]] |
| inicialização | `start_scan`, `start_set`, `start_disable_recommended` | [[Velocidade]] |
| processos | `proc_list`, `proc_close` | [[Saúde e proteção]] |
| arquivos grandes | `scan_files`, `cancel_scan`, `trash` | [[Espaço e limpeza]] |

Arquivo grande (~1100 linhas): abra só a seção que interessa (busque o comentário da seção).
