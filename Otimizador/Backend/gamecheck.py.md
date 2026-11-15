---
tags: [backend, jogos]
arquivo: gamecheck.py
---
# gamecheck.py — verificação para jogos

Aba Jogos ([[Velocidade]], `web/pagesgame.js`). Só o que tem efeito comprovado no FPS e costuma estar errado sem a pessoa saber. Api (seção "jogos" da [[webapi.py]]): `game_scan` (evento `game:scan`), `game_gpu_apply`, `game_gpu_add`, `game_gpu_undo`, `game_refresh_set`, `game_hags_set`, `game_mode_enable`, `game_open`.

| Item | Como detecta | O que faz |
|---|---|---|
| Placa certa (notebook com duas) | `gpu_rows` (Win32_VideoController; `_INTEGRATED` acha Intel UHD/Iris, Radeon Graphics) | `find_games` (bibliotecas do Steam via `libraryfolders.vdf`, manifestos da Epic; pula `_NOT_GAMES` como Wallpaper Engine e `_SKIP_EXE`) → `gpu_pref_apply` grava `GpuPreference=2;` em `HKCU\Software\Microsoft\DirectX\UserGpuPreferences`, sem mexer no que a pessoa já escolheu. O que o app gravou fica em `preferences.json` (`gpu_pref_written`) para `gpu_pref_undo` |
| Driver de vídeo | data do driver (`days`) | só avisa (>180 dias amarelo, >365 vermelho) e abre o site do fabricante (`_VENDOR`) |
| Monitor | `displays` (EnumDisplaySettings: taxa atual × máxima na mesma resolução) | `set_refresh` (ChangeDisplaySettingsEx). A tela pergunta "Manter?" e volta sozinha em 15 s sem resposta (o Windows não faz isso por essa chamada) |
| RAM sem XMP/EXPO | `ram_state`: só PC de mesa (pente DIMM e sem bateria), DDR4 ≤ 2400 ou DDR5 ≤ 4800 | só avisa: liga na BIOS |
| Integridade de memória (VBS/HVCI) | Win32_DeviceGuard `SecurityServicesRunning` contém 2 | só mostra e abre `windowsdefender://coreisolation`. **O app nunca desliga proteção do Windows** (antivírus marcaria como malware) |
| HAGS | `HKLM\…\GraphicsDrivers\HwSchMode` (2 = ligado, ausente = padrão) | `hags_set` (admin, reiniciar) |
| Modo de Jogo | `HKCU\Software\Microsoft\GameBar\AutoGameModeEnabled` (ausente = ligado) | `game_mode_enable` |

Tudo vem de um PowerShell só (`_SCRIPT`) + varredura das pastas de jogos (só em notebook com duas placas).
