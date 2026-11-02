---
tags: [mapa, indice]
atualizado: 2026-11-01
versao: 1.2.0
---
# Mapa do WebDark Otimizador

Mapa do código para agentes (e pessoas): diz **onde fica cada coisa** para alterar só o necessário sem ler o projeto inteiro.

## Como usar
1. Ache a tela ou o recurso abaixo.
2. A nota diz o arquivo JS, os métodos da `Api` (webapi.py), os eventos e o módulo Python que fazem o trabalho.
3. Abra só esses arquivos. Procure pelo **nome da função** (números de linha mudam).
4. Mudou a estrutura (arquivo, tela, método da Api, evento novo)? **Atualize a nota correspondente aqui.**

## Visão geral
- [[Arquitetura]]: como Python e HTML conversam
- [[Eventos]]: todos os eventos Python → JS e a tela dona de cada um
- [[Receitas]]: passo a passo para mudanças comuns
- [[Build e release]]: gerar o .exe, versão, atualizador
- [[Legado]]: arquivos antigos (Tk) que **não** fazem parte do app

## Telas (menu lateral)
| Menu | Nota | Abas |
|---|---|---|
| 🏠 Início | [[Início]] | (sem abas) |
| 🧹 Espaço e limpeza | [[Espaço e limpeza]] | Limpeza, Pastas, Arquivos grandes, Duplicados, Downloads antigos |
| 📦 Aplicativos | [[Aplicativos]] | Bloatware, Programas instalados |
| ⚡ Velocidade | [[Velocidade]] | Desempenho, Inicialização, Rede, Memória |
| 🩺 Saúde e proteção | [[Saúde e proteção]] | Saúde, Segurança (temperatura), Processos |
| 💡 Ajuda | [[Ajuda]] | (sem abas) |
| 🎨 Ajustes | [[Ajustes]] | (sem abas) |

## Backend (Python)
[[webapi.py]] · [[webapp.py]] · [[backend.py]] · [[thermal.py]] · [[netopt.py]] · [[mem.py]] · [[svcopt.py]] · [[system.py]] · [[health.py]] · [[startup.py]] · [[cpu.py]] · [[tweaks.py]] · [[risk.py]] · [[updater.py]] · [[installer.py]] · [[Utilitários]] (settings, single, tray, overlay, version)

## Frontend (web/)
[[core.js]] · [[CSS]] · [[index.html]]
