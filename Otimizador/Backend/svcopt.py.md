---
tags: [backend]
arquivo: svcopt.py
---
# svcopt.py — serviços que dá pra desligar

**Só desfazer.** Desligar serviços saiu do app em 2026-11-15 (serviço parado em Manual não gasta nada, e desligar quebrava impressora, VPN, Xbox). Aba Memória ([[Velocidade]]), cartão "Desfazer ajustes antigos", Api `mem_legacy_undo` ([[webapi.py]]).

- `TITLES`: nome do serviço → título que aparecia no app.
- `disabled_by_app`: serviços que o app desligou (estão em `%APPDATA%\FaxinaVarzea\services.json`) e continuam desligados.
- `restore_all`: volta cada um ao tipo de início guardado (`sc config`, inclusive "automático atrasado"). Precisa de administrador.
