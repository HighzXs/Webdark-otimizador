---
tags: [backend]
arquivo: svcopt.py
---
# svcopt.py — serviços que dá pra desligar

Aba Memória ([[Velocidade]]), cartão "Serviços que você pode desligar". Api: `svc_list`, `svc_set`, `svc_bulk` ([[webapi.py]]).

- `SERVICES`: lista fixa (nome, título, o que faz, o que quebra, risco low/mid/high, `sug` = sugerido além da lista do dono). Só esses nomes são aceitos.
- `list_state`: lê `Start` no registro (`HKLM\SYSTEM\CurrentControlSet\Services\<nome>`), serve também para driver (Bowser). Serviço que não existe no Windows some da lista.
- `set_off(nome, off)`: `sc config start= disabled` + `net stop /y`; antes guarda o tipo de início original em `%APPDATA%\FaxinaVarzea\services.json` e usa isso para religar (inclusive "automático atrasado").
- Cria ponto de restauração uma vez (`Api._restore_once`). Precisa de administrador.
