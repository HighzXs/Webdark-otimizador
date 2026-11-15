---
tags: [tela, grupo]
id: speed
js: [web/pages4.js, web/pages2.js, web/pagesnet.js, web/pagesmem.js, web/pagesgame.js]
---
# ⚡ Velocidade (`Pages.speed`)

Grupo em `web/pages6.js`.

## Desempenho (`perf`) — `Pages.perf` em pages4.js
| O quê | Api ([[webapi.py]]) | Python |
|---|---|---|
| Plano de energia, timeouts | `power_info`, `power_set`, `power_quick`, `power_timeouts` | [[health.py]]: `power_plans`, `set_power_plan`, `ensure_plan`, `set_timeouts` |
| Ajustes do usuário (HKCU) | `tweaks_list`, `tweak_set` | [[tweaks.py]] `make_tweaks` |
| Ajustes do sistema (com aviso) | `systweaks_scan`, `systweak_set` | [[system.py]] `SYS_TWEAKS`, `apply_tweak`, `warning_text` |
| TRIM / otimizar disco | `trim_enable`, `optimize_disk` | `system.enable_trim`, `optimize_drive` |
| Clock da CPU | `clock_info`, `clock_apply`, `clock_live` | [[cpu.py]] |

Eventos: `sys:state`, `sys:applied`, `perf:clock`, `perf:log`, `perf:opt_done`.

## Inicialização (`start`) — `Pages.start` em pages2.js
Api: `start_scan`, `start_set`, `start_disable_recommended`. Python: [[startup.py]] (`list_startup`, `set_enabled`, `ADVICE`). Eventos: `start:list`, `start:bulk`.

## Memória (`mem`) — `Pages.mem` em pagesmem.js
Cartões: Memória agora (só o uso), Programas em segundo plano (baixar prioridade, congelar, congelar sozinho ao jogar), Arquivo de paginação (status + voltar ao automático), Desfazer ajustes antigos (`#m-legacy`, só aparece se SvcHost ou serviços foram mudados por versões antigas). Api (seção "memória"): `mem_*`. Python: [[mem.py]], [[svcopt.py]]. Eventos: `mem:deep`, `mem:auto`. Atualiza a lista de programas a cada 10 s enquanto a aba está aberta.

## Rede (`net`) — `Pages.net` em pagesnet.js
Estado local `S` dentro do objeto. Api (seção "rede"): `net_scan`, `net_dns_test`, `net_dns_set`, `net_dns_reset`, `net_tx_reset`, `net_delivery_set`, `net_apps`, `net_limit`, `net_unlimit`, `net_drivers`, `net_driver_updates`, `net_driver_search`, `net_open`, `net_repair`. Python: [[netopt.py]]. Eventos: `net:*`.
- **Bug "cartões somem ao voltar pra aba Rede" (corrigido)**: `current_dns` ([[netopt.py]]) devolvia `servers` como `{"value": [...], "Count": n}` (o PowerShell 5.1 embrulha arrays em propriedade calculada). `paintDns` fazia `.join` nisso e dava TypeError, mas só depois da primeira leitura, então a primeira abertura funcionava e a volta à aba deixava o cartão DNS vazio (antes do `paintAll`, o erro abortava o `mount` e sumia tudo). Agora o Python normaliza para lista e o JS aceita as duas formas. Efeito colateral: `in_use` do benchmark de DNS passa a funcionar.
- **Cache da aba Rede**: `S.scan` guarda a última leitura. `paintAll` repinta todos os cartões a partir dele (cada um isolado); `load` troca o cache só se a leitura der certo e se destrava sozinho após 45 s. Ao voltar de minimizado (`visibilitychange`) repinta do cache e recarrega se passou de 30 s. `makeGroup.open` em core.js não deixa um erro no `mount` impedir o `show`.
- **Sinal do Wi-Fi sem Localização**: `netopt.wifi_info` devolve `status: "blocked"` (WlanQueryInterface erro 5). O Windows novo só libera a % do sinal com a Localização ligada, nem o administrador adianta, e `netsh wlan` e o WMI (`MSNdis_80211_ReceivedSignalStrength`) falham igual. `paintWifi` mostra então só uma nota discreta e a velocidade do adaptador (`LinkSpeed`). Não há contorno honesto; o app não liga a Localização por conta própria.

## Jogos (`game`) — `Pages.game` em pagesgame.js
Frase no topo com quantas coisas tiram FPS; painel "Precisa de atenção" (vermelho/amarelo) e "O resto". Cada item é uma linha (ponto de status, título, explicação, botões à direita), feita por `item(lv, título, texto, botões)`. Api `game_*`, Python [[gamecheck.py]], evento `game:scan` (dono `game` no `OWNER`). Troca de taxa do monitor pergunta "Manter?" e volta em 15 s sem resposta.
