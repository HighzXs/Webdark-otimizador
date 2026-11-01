"""Tudo que liga junto com o Windows, inclusive o que o Gerenciador de Tarefas não mostra."""
import json
import os
import struct
import time
import winreg
from dataclasses import dataclass, field

import backend as bk

APPROVED = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved"

# (trecho em minúsculas, nível, explicação). off = pode desligar | keep = mantenha | ? = depende
ADVICE = [
    ("securityhealth", "keep", "Segurança do Windows. Mantenha."),
    ("windows defender", "keep", "Antivírus do Windows. Mantenha."),
    ("windefend", "keep", "Antivírus do Windows. Mantenha."),
    ("kaspersky", "keep", "Antivírus. Mantenha."),
    ("bitdefender", "keep", "Antivírus. Mantenha."),
    ("avast", "keep", "Antivírus. Mantenha."),
    ("avgui", "keep", "Antivírus. Mantenha."),
    ("avgsvc", "keep", "Antivírus. Mantenha."),
    ("norton", "?", "Antivírus de terceiros. Se não paga por ele, desinstale na aba Programas."),
    ("mcafee", "?", "Antivírus de terceiros, geralmente teste que vem no PC. Desinstale se não paga."),
    ("geforce experience", "off", "GeForce Experience: só precisa para gravar jogo e atualizar driver."),
    ("nvbackend", "off", "GeForce Experience: só precisa para gravar jogo e atualizar driver."),
    ("nvidia", "keep", "Driver de vídeo NVIDIA. Mantenha."),
    ("realtek", "keep", "Áudio. Se desligar, o som pode falhar."),
    ("synaptics", "keep", "Touchpad do notebook. Mantenha."),
    ("elantech", "keep", "Touchpad do notebook. Mantenha."),
    ("ctfmon", "keep", "Teclado e idiomas. Mantenha."),
    ("igfx", "keep", "Vídeo Intel. Mantenha."),
    ("intel", "keep", "Componente Intel (vídeo, rede ou chipset). Mantenha."),
    ("radeon", "keep", "Driver de vídeo AMD. Mantenha."),
    ("spotify", "off", "Spotify abre com o Windows. Abre rápido quando você precisar."),
    ("discord", "off", "Discord abre com o Windows. Abra quando for usar."),
    ("steam", "off", "Steam abre com o Windows. Abra quando for jogar."),
    ("epicgames", "off", "Epic Games abre com o Windows. Abra quando for jogar."),
    ("epic games", "off", "Epic Games abre com o Windows. Abra quando for jogar."),
    ("teams", "off", "Teams abre com o Windows. Abra quando for usar."),
    ("skype", "off", "Skype abre com o Windows. Abra quando for usar."),
    ("zoom", "off", "Zoom abre com o Windows. Abre quando você entra numa reunião."),
    ("telegram", "off", "Abre sozinho. Abra manualmente quando precisar."),
    ("whatsapp", "off", "Abre sozinho. Abra manualmente quando precisar."),
    ("onedrive", "?", "Sincroniza arquivos com a nuvem. Desligue só se não usa."),
    ("dropbox", "?", "Sincroniza arquivos com a nuvem. Desligue só se não usa."),
    ("googledrive", "?", "Sincroniza arquivos com a nuvem. Desligue só se não usa."),
    ("googleupdate", "off", "Atualizador do Google. O Chrome se atualiza quando você abre."),
    ("google update", "off", "Atualizador do Google. O Chrome se atualiza quando você abre."),
    ("microsoftedgeupdate", "off", "Atualizador do Edge. O Edge se atualiza quando você abre."),
    ("edgeupdate", "off", "Atualizador do Edge. O Edge se atualiza quando você abre."),
    ("adobe", "off", "Serviço/atualizador da Adobe. Os programas abrem normal sem ele."),
    ("acrobat", "off", "Atualizador do Acrobat. O leitor abre normal sem ele."),
    ("jusched", "off", "Atualizador do Java. Pode desligar."),
    ("java update", "off", "Atualizador do Java. Pode desligar."),
    ("itunes", "off", "Apple/iTunes. Só precisa ao conectar iPhone."),
    ("ipod", "off", "Apple/iTunes. Só precisa ao conectar iPhone."),
    ("apple mobile", "off", "Serviço da Apple. Só precisa ao conectar iPhone."),
    ("ccleaner", "off", "Abre sozinho para oferecer upgrade. Pode desligar."),
    ("utorrent", "off", "Torrent abre com o Windows. Abra quando for usar."),
    ("bittorrent", "off", "Torrent abre com o Windows. Abra quando for usar."),
    ("cortana", "off", "Assistente de voz da Microsoft. Pode desligar."),
    ("yourphone", "off", "Liga o PC ao celular. Pode desligar se não usa."),
    ("phonelink", "off", "Liga o PC ao celular. Pode desligar se não usa."),
    ("supportassist", "off", "Suporte automático da Dell. Pode desligar."),
    ("hp support", "off", "Suporte automático da HP. Pode desligar."),
    ("lenovo vantage", "off", "Utilitário da Lenovo. Pode desligar."),
    ("wildtangent", "off", "Jogos de teste. Desinstale pela aba Programas."),
    ("mediaget", "off", "Programa indesejado. Desinstale pela aba Programas."),
    ("logitech", "?", "Software do mouse/teclado Logitech. Desligue se não personaliza botões."),
    ("lghub", "?", "Software do mouse/teclado Logitech. Desligue se não personaliza botões."),
    ("razer", "?", "Software do periférico Razer. Desligue se não personaliza."),
    ("armoury", "?", "Software da ASUS. Desligue se não usa as luzes ou perfis."),
    ("onenote", "off", "Atalho do OneNote. Pode desligar."),
    ("msedge", "?", "Navegador Edge pré-carregando para abrir mais rápido."),
    ("microsoft edge", "?", "Navegador Edge pré-carregando para abrir mais rápido."),
]

_SKIP_SERVICES = {"windefend", "sense", "wdnissvc", "securityhealthservice", "mpssvc", "wscsvc"}


@dataclass
class StartupItem:
    kind: str            # run | folder | task | service
    name: str
    command: str
    where: str
    enabled: bool
    advice: str          # off | keep | ?
    note: str
    hidden: bool         # o Gerenciador de Tarefas não mostra
    admin: bool          # precisa de administrador para mudar
    ref: dict = field(default_factory=dict)


def _advice(*texts):
    blob = " ".join(t.lower() for t in texts if t)
    for frag, level, note in ADVICE:
        if frag in blob:
            return level, note
    return "?", "Não conheço. Pesquise o nome antes de desligar."


def _is_enabled(hive, sub, name):
    try:
        with winreg.OpenKey(hive, APPROVED + "\\" + sub) as k:
            data = winreg.QueryValueEx(k, name)[0]
        return not (data and data[0] & 1)
    except OSError:
        return True


def _write_approval(hive, sub, name, enabled):
    if enabled:
        data = b"\x02\x00\x00\x00" + b"\x00" * 8
    else:
        data = b"\x03\x00\x00\x00" + struct.pack("<Q", int((time.time() + 11644473600) * 1e7))
    with winreg.CreateKeyEx(hive, APPROVED + "\\" + sub, 0, winreg.KEY_SET_VALUE) as k:
        winreg.SetValueEx(k, name, 0, winreg.REG_BINARY, data)


def _list_run():
    out = []
    sources = [
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", "Run",
         "Registro do seu usuário", False, 0),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", "Run",
         "Registro (todos os usuários)", True, winreg.KEY_WOW64_64KEY),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run", "Run32",
         "Registro (programas 32 bits)", True, winreg.KEY_WOW64_64KEY),
    ]
    for hive, path, sub, where, admin, flag in sources:
        try:
            key = winreg.OpenKey(hive, path, 0, winreg.KEY_READ | flag)
        except OSError:
            continue
        with key:
            for i in range(winreg.QueryInfoKey(key)[1]):
                try:
                    name, cmd, _ = winreg.EnumValue(key, i)
                except OSError:
                    continue
                level, note = _advice(name, str(cmd))
                out.append(StartupItem("run", name, str(cmd), where, _is_enabled(hive, sub, name), level, note,
                                       False, admin, {"hive": hive, "sub": sub}))
    return out


def _list_folders():
    out = []
    sources = [
        (winreg.HKEY_CURRENT_USER,
         os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup"),
         "Pasta Inicializar (seu usuário)", False),
        (winreg.HKEY_LOCAL_MACHINE,
         os.path.join(os.environ.get("ProgramData", ""), r"Microsoft\Windows\Start Menu\Programs\Startup"),
         "Pasta Inicializar (todos)", True),
    ]
    for hive, folder, where, admin in sources:
        if not folder or not os.path.isdir(folder):
            continue
        for fn in os.listdir(folder):
            if fn.lower() == "desktop.ini":
                continue
            level, note = _advice(fn)
            out.append(StartupItem("folder", fn, os.path.join(folder, fn), where,
                                   _is_enabled(hive, "StartupFolder", fn), level, note, False, admin,
                                   {"hive": hive, "sub": "StartupFolder"}))
    return out


def _as_list(raw):
    raw = raw.strip()
    if not raw:
        return []
    data = json.loads(raw)
    return [data] if isinstance(data, dict) else data


def _list_tasks():
    script = (
        "Get-ScheduledTask | Where-Object { $_.TaskPath -notlike '\\Microsoft\\*' -and "
        "($_.Triggers | Where-Object { $_.CimClass.CimClassName -in 'MSFT_TaskLogonTrigger','MSFT_TaskBootTrigger' }) } | "
        "ForEach-Object { $a = $_.Actions | Select-Object -First 1; "
        "[pscustomobject]@{ Name=$_.TaskName; Path=$_.TaskPath; State=\"$($_.State)\"; "
        "Cmd=((\"$($a.Execute) $($a.Arguments)\").Trim()) } } | ConvertTo-Json -Compress"
    )
    out = []
    try:
        data = _as_list(bk.ps(script, timeout=90))
    except Exception:
        return out
    for d in data:
        level, note = _advice(d["Name"], d.get("Cmd", ""))
        out.append(StartupItem("task", d["Name"], d.get("Cmd") or "", "Tarefa agendada (escondida do Gerenciador)",
                               d.get("State") != "Disabled", level, note, True, True,
                               {"name": d["Name"], "path": d["Path"]}))
    return out


def _list_services():
    script = (
        "Get-CimInstance Win32_Service | Where-Object { $_.StartMode -eq 'Auto' -and $_.PathName -and "
        "($_.PathName -notmatch '(?i)\\\\windows\\\\') } | Select-Object Name,DisplayName,PathName | ConvertTo-Json -Compress"
    )
    out = []
    try:
        data = _as_list(bk.ps(script, timeout=90))
    except Exception:
        return out
    for d in data:
        name = d["Name"]
        path = (d.get("PathName") or "").lower()
        if name.lower() in _SKIP_SERVICES or "windows defender" in path or "microsoft shared" in path:
            continue
        level, note = _advice(name, d.get("DisplayName"), path)
        out.append(StartupItem("service", d.get("DisplayName") or name, d.get("PathName") or "",
                               "Serviço que liga com o Windows (escondido do Gerenciador)", True, level, note,
                               True, True, {"name": name}))
    return out


def list_startup():
    items = _list_run() + _list_folders() + _list_tasks() + _list_services()
    order = {"off": 0, "?": 1, "keep": 2}
    kinds = {"run": 0, "folder": 1, "task": 2, "service": 3}
    return sorted(items, key=lambda i: (kinds[i.kind], order[i.advice], i.name.lower()))


def _q(s):
    return s.replace("'", "''")


def set_enabled(item, enabled):
    """-> (ok, mensagem)"""
    try:
        if item.kind in ("run", "folder"):
            _write_approval(item.ref["hive"], item.ref["sub"], item.name, enabled)
            return True, ""
        if item.kind == "task":
            verb = "Enable" if enabled else "Disable"
            out = bk.ps(
                f"try {{ {verb}-ScheduledTask -TaskName '{_q(item.ref['name'])}' -TaskPath '{_q(item.ref['path'])}' "
                f"-ErrorAction Stop | Out-Null; 'OK' }} catch {{ 'FAIL|' + $_.Exception.Message }}"
            ).strip()
        else:
            mode = "Automatic" if enabled else "Manual"
            out = bk.ps(
                f"try {{ Set-Service -Name '{_q(item.ref['name'])}' -StartupType {mode} -ErrorAction Stop; 'OK' }} "
                f"catch {{ 'FAIL|' + $_.Exception.Message }}"
            ).strip()
        if out.endswith("OK"):
            return True, ""
        return False, out.split("|", 1)[-1][:160] or "Falhou."
    except PermissionError:
        return False, "Precisa de administrador."
    except OSError as e:
        return False, str(e)
