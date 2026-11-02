---
tags: [backend]
arquivo: tweaks.py
---
# tweaks.py — ajustes do usuário

Ajustes de desempenho/privacidade em HKCU (sem admin, reversíveis). `class Tweak` (`is_on`, `apply`), lista em `make_tweaks`. Animações via ctypes (`_anim_off`, `_set_anim`).

Para criar um ajuste novo: adicione um `Tweak` em `make_tweaks`. Tela: Desempenho em [[Velocidade]]. Ajustes que precisam de admin ficam em [[system.py]].
