---
tags: [backend]
arquivo: startup.py
---
# startup.py — o que liga com o Windows

- `class StartupItem`, `list_startup` junta: `_list_run` (chaves Run), `_list_folders` (pastas Inicializar), `_list_tasks` (tarefas agendadas), `_list_services` (serviços; `_SKIP_SERVICES` protege antivírus/firewall).
- Ligar/desligar: `set_enabled` (usa `StartupApproved` como o Gerenciador de Tarefas: `_is_enabled`, `_write_approval`).
- Conselhos por item: `ADVICE`, `_advice`.

Tela: Inicialização em [[Velocidade]].
