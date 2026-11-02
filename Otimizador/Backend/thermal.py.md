---
tags: [backend, temperatura]
arquivo: thermal.py
---
# thermal.py — vigia de temperatura

Lê sensores, avisa e baixa o clock da CPU (via [[cpu.py]]) antes de esquentar demais.

- **Curva**: lista `[°C, % clock máx]`. `DEFAULT_CURVE`, perfis `CURVE_MODES` (`gamer`, `careful`, `very`), `make_curve`, `curve_target`, `valid_curve`, `guess_tjmax`.
- **Config**: `class Config` (`limit`, `crit`), `load_config`, `save_config` → `%APPDATA%\FaxinaVarzea\settings.json` (`app_dir`).
- **Sensor**: `class Sensor` (`start`, `stop`, `get`) roda `SENSOR_SCRIPT` (PowerShell) e lê linhas com `parse_line`.
- **Guard**: `class Guard` (`level`, `target`, `tick`, `restore`, `recover`). Estados: `NOSENSOR`, `OK`, `WARN`, `HOT`, `CRIT` (`RANK`). `recover` desfaz limite de clock que ficou de uma sessão anterior.
- **Log**: `log_event`, `recent_events`, `hot_events_last_days`.

Loop: `Api._guard_loop` em [[webapi.py]]. Tela: Segurança em [[Saúde e proteção]]. Overlay: [[Utilitários]].
