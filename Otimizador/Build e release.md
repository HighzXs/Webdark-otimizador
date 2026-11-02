---
tags: [mapa, build]
---
# Build e release

- **Versão**: `version.py` → `VERSION` e `REPO` (`HighzXs/Webdark-otimizador`). A barra lateral mostra `v` + VERSION.
- **Build**: `build_webdark.bat` → PyInstaller onefile → `dist\webdark\WebDark.exe`. Empacota `web/`, `icon.png`, `icon.ico`.
- **Ícone**: `make_icon_webdark.py` desenha o ícone com Pillow e gera `icon.ico` / `icon.png`.
- **Atualização**: [[updater.py]] lê o último GitHub Release, baixa o .exe (só de github.com / githubusercontent.com) e troca o arquivo. Na Api: `update_check`, `update_check_now`, `update_apply` (seção atualização). Banner: `updBanner` / `updStart` em pages5.js. Primeira checagem 8 s após abrir (`on_start` em [[webapp.py]]).
- **Autoteste do .exe**: `WebDark.exe --selftest saida.txt` (`selftest` em [[webapp.py]]). `--relaunch-test` testa reabrir.
- **Lançar**: subir VERSION → buildar → criar Release no GitHub com o .exe anexado.
