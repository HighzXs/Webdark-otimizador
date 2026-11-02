---
tags: [backend]
arquivo: backend.py
---
# backend.py — limpeza, disco, apps

Lógica sem interface (herdada do "Faxina Várzea"). ~950 linhas, agrupadas assim:

| Grupo | Funções |
|---|---|
| Admin / processo | `is_admin`, `relaunch_as_admin`, `fresh_start_env`, `low_priority`, `CREATE_NO_WINDOW` |
| PowerShell | `ps(script, timeout)`, `ps_stream(script)` |
| Disco e tamanhos | `fmt_size`, `fixed_drives`, `disk_usage`, `dir_size`, `path_size`, `scan_children`, `find_big_files`, `open_in_explorer`, `send_to_trash` |
| Limpeza | `class Cleaner`, `make_cleaners`, `_browser_caches`, `_app_caches`, `_steam_path`, `measure`, `run_cleaner`, `_wipe`, `_stop_services`/`_start_services`, `recycle_size`, `quick_summary` |
| Extras | `hiberfil_size`, `windows_old_size`, `hibernate_off`, `component_cleanup`, `open_windows_cleanmgr` |
| Bloatware (Appx) | `BLOAT_RULES`, `PROTECTED`, `HIDE_PREFIX`, `class AppxItem`, `list_appx`, `remove_appx` |
| Programas | `SUSPECT`, `class Program`, `list_programs`, `regkey_exists`, `launch_uninstaller`, `uninstall_and_wait`, `run_uninstaller`, `_descendants` |
| Histórico | `history_load`, `history_add`, `history_total` (`history.json`) |
| Restauração | `create_restore_point` |
| Duplicados | `user_folders`, `_hash_file`, `find_duplicates`, `_DUP_SKIP` |

Usado por: [[Espaço e limpeza]], [[Aplicativos]], [[Início]].
