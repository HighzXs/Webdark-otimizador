---
tags: [backend]
arquivo: cpu.py
---
# cpu.py — clock da CPU

Controla o clock pelo plano de energia ativo (`powercfg`): `read`, `write`, `write_pair`, `activate`, `unhide`, `snapshot`, `snapshot_unlocked`, `apply(min_pct, max_pct, boost, mhz)`, `info`, `live`.

Usado por: Desempenho em [[Velocidade]] e pelo [[thermal.py]] (baixar clock quando esquenta).
