---
tags: [backend]
arquivo: mem.py
---
# mem.py — memória RAM

Usado pela aba Memória ([[Velocidade]]) via métodos `mem_*` da [[webapi.py]].

| Parte | O quê |
|---|---|
| RAM agora | `ram_info` (total, disponível, %) |
| Programas | `GROUPS` (Chrome, Edge, Opera, Brave, Firefox, Discord, Spotify, Steam web helper; qual pode congelar), `group_rows`, `lower_group` (prioridade de memória + de CPU) |
| Congelar | `Freezer`: suspende só programas de `GROUPS`, nunca o que está em primeiro plano, sempre com prazo (5 a 120 min), grava `%APPDATA%\FaxinaVarzea\frozen.json` (PID + hora de criação) e descongela sobras na próxima abertura e em `_shutdown`. **Não** esvazia a RAM ao congelar (era o que fazia o programa travar ao descongelar) |
| Congelar sozinho | `AutoFreeze` (thread de 4 s): `foreground_game` (tela cheia pelo `SHQueryUserNotificationState` ou pasta de jogos, com `NOT_GAMES` de exceção), `mic_cam_exes` (registro de privacidade: quem usa microfone/câmera nunca é congelado), 2 leituras com jogo congelam, 3 sem jogo descongelam, voltar a um programa congelado descongela na hora. Config em `preferences.json` (`mem_auto`) |
| Paginação | `pagefile_info`, `pagefile_auto` (só volta ao automático; tamanho manual saiu) |
| SvcHost (só desfazer) | `svchost_changed`, `svchost_reset` → `HKLM\SYSTEM\CurrentControlSet\Control\SvcHostSplitThresholdInKB` volta a 0x380000 |

SysMain fica só em Desempenho ([[system.py]] `SYS_TWEAKS`).

## Removido em 2026-11-15 (não dava desempenho)
Lista de espera (`purge_standby`), liberar RAM (`trim_group`/EmptyWorkingSet), tamanho manual da paginação, ajuste do SvcHost e o cartão "Serviços que dá pra desligar". Quem usou versões antigas vê o cartão "Desfazer ajustes antigos" (Api `mem_legacy_undo`).
