"""Ajustes de sistema (com aviso), TRIM, processos, downloads antigos, atualizações e drivers."""
import json
import os
import re
import subprocess
import time
from dataclasses import dataclass, field

import psutil

import backend as bk

NO_WINDOW = bk.CREATE_NO_WINDOW


def _q(s):
    return s.replace("'", "''")


def _as_list(raw):
    raw = raw.strip()
    if not raw:
        return []
    data = json.loads(raw)
    return [data] if isinstance(data, dict) else data


# ------------------------------------------------------------ serviços do Windows
@dataclass
class SysTweak:
    key: str
    name: str
    desc: str
    what: str                 # o que muda de verdade
    risks: str                # o que pode dar errado
    on_modes: dict            # serviço -> tipo de inicialização quando o ajuste está LIGADO
    off_modes: dict           # serviço -> tipo de inicialização ao DESFAZER
    on_ok: tuple              # tipos de inicialização que contam como "ajuste aplicado"
    stop_on: bool = True      # parar o serviço agora ao aplicar
    start_off: tuple = ()     # serviços para iniciar ao desfazer
    hdd_warning: str = ""     # aviso extra se o disco do sistema for HD


SYS_TWEAKS = [
    SysTweak(
        "telemetry", "Reduzir telemetria do Windows",
        "Coloca DiagTrack e dmwappushservice em Manual: o Windows para de enviar dados de uso em segundo plano.",
        "Os serviços DiagTrack (Experiências do Usuário Conectado) e dmwappushservice passam para Manual e são parados.",
        "Reduz, mas não zera a telemetria (isso só por política de grupo no Windows Pro). Pode atrapalhar "
        "relatórios de erro, o Hub de Feedback e alguns recursos do programa Insider. O Windows pode religar "
        "esses serviços depois de uma atualização grande.",
        {"DiagTrack": "Manual", "dmwappushservice": "Manual"},
        {"DiagTrack": "Automatic", "dmwappushservice": "Manual"},
        ("Manual", "Disabled"), True, ("DiagTrack",)),
    SysTweak(
        "sysmain", "Desligar SysMain (Superfetch)",
        "Útil em SSD: o serviço pré-carrega programas na memória e gasta disco/RAM à toa.",
        "O serviço SysMain é desativado e parado.",
        "Alguns programas podem abrir um pouco mais devagar na primeira vez, e o PC pode demorar mais para "
        "'esquentar' depois de ligar. Em HD isso costuma deixar o PC visivelmente MAIS LENTO.",
        {"SysMain": "Disabled"}, {"SysMain": "Automatic"}, ("Disabled",), True, ("SysMain",),
        "SEU DISCO É UM HD. Em HD o SysMain ajuda, e desligar tende a deixar o PC mais lento. "
        "Só continue se tiver certeza."),
    SysTweak(
        "wsearch", "Pausar a indexação do Windows Search",
        "Alivia o disco e o processador: o Windows para de catalogar seus arquivos em segundo plano.",
        "O serviço WSearch (Windows Search) é desativado e parado.",
        "A busca do menu Iniciar e do Explorador de Arquivos fica bem mais lenta e pode deixar de achar "
        "conteúdo de arquivos e e-mails. A busca do Outlook também pode parar de funcionar.",
        {"WSearch": "Disabled"}, {"WSearch": "Automatic"}, ("Disabled",), True, ("WSearch",)),
]


def service_states():
    """-> {nome do serviço: (StartMode, State)} só dos serviços dos ajustes."""
    names = sorted({n for t in SYS_TWEAKS for n in list(t.on_modes) + list(t.off_modes)})
    flt = " OR ".join(f"Name='{n}'" for n in names)
    raw = bk.ps(f'Get-CimInstance Win32_Service -Filter "{flt}" | Select-Object Name,StartMode,State | '
                "ConvertTo-Json -Compress", timeout=60)
    return {d["Name"]: (d["StartMode"], d["State"]) for d in _as_list(raw)}


def tweak_state(t, states):
    """True/False se o ajuste está aplicado; None se o serviço não existe neste Windows."""
    present = [n for n in t.on_modes if n in states]
    if not present:
        return None
    return all(states[n][0] in t.on_ok for n in present)


def warning_text(t, disk_kind):
    txt = (f"{t.name}\n\n"
           f"O QUE FAZ:\n{t.what}\n\n"
           f"⚠ O QUE PODE DAR ERRADO:\n{t.risks}\n\n"
           "↩ COMO DESFAZER: desligue este mesmo interruptor.")
    if t.hdd_warning and disk_kind == "HDD":
        txt += f"\n\n🛑 ATENÇÃO: {t.hdd_warning}"
    return txt + "\n\nQuer mesmo continuar?"


def apply_tweak(t, on):
    """-> (ok, mensagem). Precisa de administrador."""
    modes = t.on_modes if on else t.off_modes
    lines = []
    for name, mode in modes.items():
        n = _q(name)
        lines.append(f"Set-Service -Name '{n}' -StartupType {mode} -ErrorAction Stop")
        if on and t.stop_on:
            lines.append(f"Stop-Service -Name '{n}' -Force -ErrorAction SilentlyContinue")
        if not on and name in t.start_off:
            lines.append(f"Start-Service -Name '{n}' -ErrorAction SilentlyContinue")
    script = ("try { " + "; ".join(lines) + "; 'OK' } catch { 'FAIL|' + $_.Exception.Message }")
    out = bk.ps(script, timeout=90).strip()
    if out.endswith("OK"):
        return True, ""
    return False, out.split("|", 1)[-1][:200] or "Falhou."


# ---------------------------------------------------------------------- disco / TRIM
def system_disk_kind():
    """-> 'SSD', 'HDD' ou '' (não sei)."""
    out = bk.ps("try { (Get-Partition -DriveLetter C | Get-Disk | Get-PhysicalDisk).MediaType } catch { '' }",
                timeout=60).strip()
    return out if out in ("SSD", "HDD") else ""


def trim_status():
    """True = TRIM ligado, False = desligado, None = não consegui ler."""
    r = subprocess.run(["fsutil", "behavior", "query", "DisableDeleteNotify"], capture_output=True,
                       stdin=subprocess.DEVNULL, creationflags=NO_WINDOW)
    m = re.search(r"=\s*(\d)", r.stdout.decode("cp850", errors="replace"))
    return (m.group(1) == "0") if m else None


def enable_trim():
    r = subprocess.run(["fsutil", "behavior", "set", "DisableDeleteNotify", "0"], capture_output=True,
                       stdin=subprocess.DEVNULL, creationflags=NO_WINDOW)
    return r.returncode == 0


def optimize_mode(kind):
    return {"SSD": "ReTrim", "HDD": "Defrag"}.get(kind, "Analyze")


def optimize_drive(kind):
    """Gera as linhas do Optimize-Volume no C:."""
    mode = optimize_mode(kind)
    yield from bk.ps_stream(f"Optimize-Volume -DriveLetter C -{mode} -Verbose 4>&1 | ForEach-Object {{ \"$_\" }}")


# ------------------------------------------------------------------------ processos
PROTECTED_NAMES = {
    "system", "registry", "smss.exe", "csrss.exe", "wininit.exe", "winlogon.exe", "services.exe", "lsass.exe",
    "svchost.exe", "dwm.exe", "explorer.exe", "memory compression", "secure system", "fontdrvhost.exe",
    "sihost.exe", "taskhostw.exe", "ctfmon.exe", "runtimebroker.exe", "searchhost.exe", "searchindexer.exe",
    "startmenuexperiencehost.exe", "shellexperiencehost.exe", "msmpeng.exe", "securityhealthservice.exe",
    "securityhealthsystray.exe", "audiodg.exe", "spoolsv.exe", "wudfhost.exe", "lsaiso.exe", "conhost.exe",
    "system idle process", "dllhost.exe", "wmiprvse.exe", "textinputhost.exe", "applicationframehost.exe",
    "faxinavarzea.exe", "faxinavarzeateste.exe", "python.exe", "pythonw.exe",
}


@dataclass
class ProcGroup:
    name: str
    count: int = 0
    ram: int = 0
    cpu: float = 0.0
    pids: list = field(default_factory=list)
    protected: bool = False


def _is_protected(name, exe):
    low = name.lower()
    if low in PROTECTED_NAMES:
        return True
    win = (os.environ.get("SystemRoot") or r"C:\Windows").lower()
    return bool(exe) and exe.lower().startswith(win + "\\")


def process_groups():
    """Processos agrupados pelo nome (Chrome com 20 abas vira uma linha só)."""
    ncpu = psutil.cpu_count() or 1
    own = os.getpid()
    groups = {}
    for p in psutil.process_iter(["pid", "name", "memory_info", "exe"]):
        try:
            info = p.info
            name = info["name"] or "?"
            g = groups.setdefault(name.lower(), ProcGroup(name))
            g.count += 1
            g.ram += info["memory_info"].rss if info["memory_info"] else 0
            g.cpu += p.cpu_percent(None) / ncpu   # a 1ª leitura é 0: precisa de duas atualizações
            g.pids.append(info["pid"])
            if info["pid"] == own or _is_protected(name, info["exe"]):
                g.protected = True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return list(groups.values())


def close_group(g):
    """Fecha todos os processos do grupo. -> (fechados, erros)"""
    if g.protected:
        return 0, ["Processo protegido do Windows."]
    closed, errors = 0, []
    procs = []
    for pid in g.pids:
        try:
            p = psutil.Process(pid)
            p.terminate()
            procs.append(p)
        except psutil.NoSuchProcess:
            pass
        except psutil.AccessDenied:
            errors.append(f"PID {pid}: sem permissão")
    _, alive = psutil.wait_procs(procs, timeout=3)
    for p in alive:
        try:
            p.kill()
        except psutil.Error:
            errors.append(f"PID {p.pid}: não fechou")
    closed = len(procs) - len(errors)
    return max(closed, 0), errors


# ------------------------------------------------------------- downloads antigos
def downloads_dir():
    return os.path.join(os.path.expanduser("~"), "Downloads")


def old_downloads(days, cancel=None, min_bytes=100 * 1024, top=300):
    """Arquivos de Downloads sem modificação há `days` dias. -> [(tamanho, caminho)] do maior pro menor."""
    cutoff = time.time() - days * 86400
    out = []
    stack = [downloads_dir()]
    while stack:
        if cancel is not None and cancel.is_set():
            break
        d = stack.pop()
        try:
            with os.scandir(d) as it:
                for e in it:
                    try:
                        if e.is_symlink():
                            continue
                        st = e.stat(follow_symlinks=False)
                        if e.is_dir(follow_symlinks=False):
                            if not st.st_file_attributes & bk.FILE_ATTRIBUTE_REPARSE_POINT:
                                stack.append(e.path)
                        elif st.st_size >= min_bytes and st.st_mtime < cutoff:
                            out.append((st.st_size, e.path))
                    except OSError:
                        pass
        except OSError:
            pass
    out.sort(reverse=True)
    return out[:top]


# ----------------------------------------------------------- atualizações / drivers
def pending_updates():
    """-> (lista, erro). Só procura, nunca instala. Leva de 20s a 1min."""
    script = (
        "try { $s = New-Object -ComObject Microsoft.Update.Session; "
        "$r = $s.CreateUpdateSearcher().Search('IsInstalled=0 and IsHidden=0'); "
        "@($r.Updates | ForEach-Object { [pscustomobject]@{ Title=$_.Title; Size=[int64]$_.MaxDownloadSize; "
        "Driver=($_.Type -eq 2); Reboot=[bool]$_.RebootRequired } }) | ConvertTo-Json -Compress } "
        "catch { 'ERR|' + $_.Exception.Message }"
    )
    raw = bk.ps(script, timeout=240).strip()
    if raw.startswith("ERR|"):
        return [], raw[4:200]
    return _as_list(raw), ""


def old_drivers(years=3):
    """Drivers de vídeo, rede, áudio e bluetooth com data antiga. É estimativa pela data do driver."""
    script = (
        "Get-CimInstance Win32_PnPSignedDriver | Where-Object { $_.DriverDate -and $_.DeviceName -and "
        "$_.DeviceClass -in 'DISPLAY','NET','MEDIA','BLUETOOTH' -and $_.Manufacturer -notmatch 'Microsoft' } | "
        "Select-Object DeviceName,Manufacturer,DriverVersion,DeviceClass,"
        "@{n='Date';e={$_.DriverDate.ToString('yyyy-MM-dd')}} | ConvertTo-Json -Compress"
    )
    limit = time.strftime("%Y-%m-%d", time.localtime(time.time() - years * 365 * 86400))
    seen, out = set(), []
    for d in _as_list(bk.ps(script, timeout=120)):
        if d["Date"] < limit and d["DeviceName"] not in seen:
            seen.add(d["DeviceName"])
            out.append(d)
    return sorted(out, key=lambda d: d["Date"])


def check_updates_and_drivers():
    ups, err = pending_updates()
    return {"updates": ups, "error": err, "drivers": old_drivers()}
