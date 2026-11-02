---
tags: [backend]
arquivo: mem.py
---
# mem.py — memória RAM

Usado pela aba Memória ([[Velocidade]]) via métodos `mem_*` da [[webapi.py]].

| Parte | O quê |
|---|---|
| Permissão | `_enable_privilege` liga `SeProfileSingleProcessPrivilege` (só funciona como administrador) |
| Lista de espera | `ram_info`, `_standby_bytes` (NtQuerySystemInformation 80), `purge_standby(full)` (NtSetSystemInformation: 5 = só prioridade baixa, suave; 4 = tudo) |
| Programas | `GROUPS` (Chrome, Edge, Opera, Brave, Firefox, Discord, Spotify, Steam web helper; qual pode congelar), `group_rows`, `trim_group` (EmptyWorkingSet), `lower_group` (prioridade de memória + de CPU) |
| Congelar | `Freezer`: suspende só programas de `GROUPS`, nunca o que está em primeiro plano, sempre com prazo (5 a 120 min), grava `%APPDATA%\FaxinaVarzea\frozen.json` (PID + hora de criação) e descongela sobras na próxima abertura e em `_shutdown` |
| Congelar sozinho | `AutoFreeze` (thread de 4 s): `foreground_game` (tela cheia pelo `SHQueryUserNotificationState` ou pasta de jogos, com `NOT_GAMES` de exceção), `mic_cam_exes` (registro de privacidade: quem usa microfone/câmera nunca é congelado), 2 leituras com jogo congelam, 3 sem jogo descongelam, voltar a um programa congelado descongela na hora. Config em `preferences.json` (`mem_auto`) |
| Paginação | `pagefile_suggest` (pela RAM e 40% do espaço livre), `pagefile_info`, `pagefile_apply` (WMI, precisa reiniciar), `pagefile_auto` |
| SvcHost | `SVC_TABLE`, `svchost_tier` (maior faixa que cabe, com 10% de folga), `svchost_info`, `svchost_set` → `HKLM\SYSTEM\CurrentControlSet\Control\SvcHostSplitThresholdInKB` (DWORD, padrão 0x380000) |

SysMain não está aqui: usa o ajuste `sysmain` de [[system.py]] (`SYS_TWEAKS`, `apply_tweak`).
Ações que mexem no sistema (paginação, SvcHost, SysMain) criam um ponto de restauração uma vez (`Api._restore_once`).
