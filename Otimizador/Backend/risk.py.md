---
tags: [backend, seguranca]
arquivo: risk.py
---
# risk.py — risco de apagar arquivo

`assess(path)` → `Risk` (nível + rótulo). Regras em `_classify` (pasta, nome, extensão, idade, se está no Windows). `is_in_use` confere se o arquivo está aberto.

Mostrado como selo (`riskPill` em pages3.js) em Arquivos grandes, Duplicados e Downloads ([[Espaço e limpeza]]).
