---
tags: [tela, grupo]
id: speed
js: [web/pages4.js, web/pages2.js, web/pagesnet.js]
---
# ⚡ Velocidade (`Pages.speed`)

Grupo em `web/pages6.js`.

## Desempenho (`perf`) — `Pages.perf` em pages4.js
| O quê | Api ([[webapi.py]]) | Python |
|---|---|---|
| Plano de energia, timeouts | `power_info`, `power_set`, `power_quick`, `power_timeouts` | [[health.py]]: `power_plans`, `set_power_plan`, `ensure_plan`, `set_timeouts` |
| Ajustes do usuário (HKCU) | `tweaks_list`, `tweak_set` | [[tweaks.py]] `make_tweaks` |
| Ajustes do sistema (com aviso) | `systweaks_scan`, `systweak_set` | [[system.py]] `SYS_TWEAKS`, `apply_tweak`, `warning_text` |
| TRIM / otimizar disco | `trim_enable`, `optimize_disk` | `system.enable_trim`, `optimize_drive` |
| Clock da CPU | `clock_info`, `clock_apply`, `clock_live` | [[cpu.py]] |

Eventos: `sys:state`, `sys:applied`, `perf:clock`, `perf:log`, `perf:opt_done`.

## Inicialização (`start`) — `Pages.start` em pages2.js
Api: `start_scan`, `start_set`, `start_disable_recommended`. Python: [[startup.py]] (`list_startup`, `set_enabled`, `ADVICE`). Eventos: `start:list`, `start:bulk`.

## Rede (`net`) — `Pages.net` em pagesnet.js
Estado local `S` dentro do objeto. Api (seção "rede"): `net_scan`, `net_dns_test`, `net_dns_set`, `net_dns_reset`, `net_tx_set`, `net_delivery_set`, `net_apps`, `net_limit`, `net_unlimit`, `net_drivers`, `net_driver_updates`, `net_driver_search`, `net_open`, `net_repair`. Python: [[netopt.py]]. Eventos: `net:*`.
