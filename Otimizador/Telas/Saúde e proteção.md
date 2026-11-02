---
tags: [tela, grupo]
id: protect
js: [web/pages4.js, web/pages5.js, web/pages2.js]
---
# 🩺 Saúde e proteção (`Pages.protect`)

Grupo em `web/pages6.js`.

## Saúde (`health`) — `Pages.health` em pages4.js
Api: `health_scan`, `updates_check`, `repair`. Python: [[health.py]] (`disk_health`, `diagnose`, `sfc`, `dism_restore`, `dism_cleanup`, `chkdsk_scan`, `flush_dns`) e [[system.py]] (`check_updates_and_drivers`). Eventos: `health:*`. Constantes de nível na tela: `LV`, `LV_TEXT`, `PILL`.

## Segurança / temperatura (`security`) — `Pages.security` em pages5.js
Api (seção "segurança"): `sec_state`, `sec_open`, `sec_save`, `sec_preset`, `sec_suggest`, `sec_import`, `sec_events`, `sec_procs`. Python: [[thermal.py]] (`Sensor`, `Guard`, `Config`, curvas). Overlay de temperatura: `Api.make_overlay` + `overlay.describe` ([[Utilitários]]). Loop do vigia: `Api._guard_loop`. Eventos: `sec:cfg`, `sec:tick`.

## Processos (`proc`) — `Pages.proc` em pages2.js
Api: `proc_list`, `proc_close`. Python: [[system.py]] `process_groups`, `close_group`, `PROTECTED_NAMES`.
