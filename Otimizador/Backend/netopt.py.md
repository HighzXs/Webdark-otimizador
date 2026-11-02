---
tags: [backend, rede]
arquivo: netopt.py
---
# netopt.py — rede

| Recurso | Funções / constantes |
|---|---|
| DNS | `DNS_SERVERS`, `TEST_NAMES`, `dns_query_ms`, `dns_benchmark`, `current_dns`, `set_dns`, `reset_dns` |
| Wi-Fi e adaptadores | `wifi_info`, `adapters_info`, `set_tx_power` (regex `_TX`) |
| Otimização de Entrega | `DO_POLICY`, `delivery_state`, `delivery_set` |
| Limite de banda por programa (QoS) | `QOS_PREFIX` (`"WebDark - "`), `net_apps`, `qos_list`, `qos_limit`, `qos_remove`, `_SKIP` |
| Drivers | `net_drivers`, `driver_updates` |
| Reparos | `repair_renew`, `repair_reset`, `repair_all` |

Tela: Rede em [[Velocidade]] (`web/pagesnet.js`).
