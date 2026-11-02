---
tags: [backend]
arquivo: health.py
---
# health.py — saúde, reparos, energia

- **Disco**: `class DiskInfo`, `disk_health`.
- **Diagnóstico**: `diagnose` (usa `_reboot_pending`, `uptime_days`, `_antivirus`).
- **Reparos** (saída ao vivo por `stream_cmd`): `sfc`, `dism_restore`, `dism_cleanup`, `chkdsk_scan`, `flush_dns`.
- **Plano de energia**: `power_plans`, `set_power_plan`, `ensure_plan`, `set_timeouts`, `has_battery`.

Telas: Saúde em [[Saúde e proteção]], Desempenho em [[Velocidade]].
