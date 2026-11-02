# WebDark Otimizador

Programa para Windows que deixa o PC mais leve e rápido. Ele limpa arquivos inúteis, mostra a saúde do computador e ajusta a velocidade e a internet. Tudo que ele muda pode ser desfeito.

Versão atual: **1.2.0**

## O que ele faz

- **Espaço e limpeza**: apaga arquivos temporários e mostra o que ocupa espaço (pastas, arquivos grandes, duplicados e downloads antigos).
- **Aplicativos**: remove programas que vêm de fábrica e não servem para nada, e lista os programas instalados.
- **Velocidade**: ajusta o plano de energia, os programas que abrem junto com o Windows e a internet (DNS, Wi-Fi e limite de banda por programa).
- **Saúde e proteção**: verifica o estado do sistema, a temperatura e os processos abertos.
- **Ajuda**: explica o que cada tela faz.
- **Ajustes**: muda o tema e outras preferências.

## O que precisa

- Windows 10 ou 11
- Python 3.12 ou mais novo (só se for rodar pelo código)
- WebView2 (o Windows 11 já tem; no Windows 10 atualizado, geralmente também)

Algumas ações precisam de administrador. O app abre sem ser admin. Quando precisar, aparece o aviso "PRECISA DE ADMIN": clique em "Reabrir como administrador".

## Rodar pelo código

```bash
pip install pywebview pythonnet psutil pystray Pillow send2trash
python webapp.py
```

## Gerar o .exe

```bash
pip install pyinstaller
build_webdark.bat
```

O programa fica em `dist\webdark\WebDark.exe`.

## Como o projeto está organizado

- `webapp.py`: abre a janela do programa.
- `webapi.py`: liga a tela (interface) ao Python.
- `backend.py`, `netopt.py`, `thermal.py`, `health.py`, `startup.py`, `tweaks.py` e outros: fazem o trabalho de cada função.
- `web/`: a tela, em HTML, CSS e JavaScript.
- `Otimizador/`: mapa do código em Markdown (dá para abrir com o Obsidian).

Os arquivos `page_*.py`, `ui_*.py` e `app.py` são de uma versão antiga, feita com Tk. Não fazem parte do programa atual.

## Onde ficam os dados

Preferências, configurações e histórico ficam em `%APPDATA%\FaxinaVarzea\`.

## Atualizações

O programa checa a última versão publicada no GitHub e pode baixá-la. Ele só baixa de `github.com` e `githubusercontent.com`.

## Licença

Uso pessoal e fechado: feito só para mim e meus amigos. Não redistribuir.

---

Feito com ajuda do [Claude](https://claude.com/claude-code).
