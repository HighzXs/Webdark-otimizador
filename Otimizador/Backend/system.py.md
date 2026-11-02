---
tags: [backend]
arquivo: system.py
---
# system.py — ajustes de sistema, disco, processos, updates

| Recurso | Funções |
|---|---|
| Ajustes do sistema (admin, com aviso) | `class SysTweak`, `SYS_TWEAKS`, `service_states`, `tweak_state`, `warning_text`, `apply_tweak` |
| Disco | `system_disk_kind`, `trim_status`, `enable_trim`, `optimize_mode`, `optimize_drive` |
| Processos | `class ProcGroup`, `PROTECTED_NAMES`, `_is_protected`, `process_groups`, `close_group` |
| Downloads antigos | `downloads_dir`, `old_downloads` |
| Updates e drivers | `pending_updates`, `old_drivers`, `check_updates_and_drivers` |
| Ficha do PC | `format_specs`, `_RAM_TYPE` |

Telas: [[Velocidade]], [[Saúde e proteção]], [[Espaço e limpeza]], [[Início]].
