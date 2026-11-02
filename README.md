# WebDark Otimizador

Otimizador para Windows. Limpa o PC, mostra a saúde do sistema e ajusta velocidade e rede, tudo com a opção de desfazer.

Versão atual: **1.2.0**

## O que ele faz

- **Espaço e limpeza**: limpeza de arquivos temporários, pastas, arquivos grandes, duplicados e downloads antigos.
- **Aplicativos**: remove bloatware e lista os programas instalados.
- **Velocidade**: plano de energia, programas que iniciam com o Windows e ajustes de rede (DNS, Wi-Fi, limite de banda por programa).
- **Saúde e proteção**: diagnóstico do sistema, temperatura e processos.
- **Ajuda**: dicas de cada tela.
- **Ajustes**: tema e preferências.

Mexe só em ajustes do Windows e dá para desfazer.

## Requisitos

- Windows 10 ou 11
- Python 3.12 ou mais recente (só para rodar pelo código-fonte)
- WebView2 (já vem no Windows 11 e na maioria dos Windows 10 atualizados)

Algumas ações pedem administrador. O app roda sem admin, e quando precisa, mostra o aviso "PRECISA DE ADMIN". Use "Reabrir como administrador".

## Rodar pelo código-fonte

```bash
pip install pywebview pythonnet psutil pystray Pillow send2trash
python webapp.py
```

## Gerar o .exe

```bash
pip install pyinstaller
build_webdark.bat
```

O executável sai em `dist\webdark\WebDark.exe`.

## Estrutura

- `webapp.py`: abre a janela (pywebview) e carrega a interface.
- `webapi.py`: classe `Api`, a ponte entre a interface e o Python.
- `backend.py`, `netopt.py`, `thermal.py`, `health.py`, `startup.py`, `tweaks.py` e outros: a lógica de cada função.
- `web/`: interface em HTML, CSS e JavaScript.
- `Otimizador/`: mapa do código em Markdown (abra com o Obsidian).

Arquivos `page_*.py`, `ui_*.py`, `app.py` e afins são de uma versão antiga em Tk e não fazem parte do app.

## Dados

Preferências, configurações e histórico ficam em `%APPDATA%\FaxinaVarzea\`.

## Atualizações

O app verifica o último Release no GitHub e pode baixar a nova versão. Só baixa de `github.com` e `githubusercontent.com`.

## Licença

Uso pessoal e fechado: feito só para mim e meus amigos. Não redistribuir.

---

Feito com ajuda do [Claude](https://claude.com/claude-code).
