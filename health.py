"""Saúde do disco, diagnóstico do Windows, reparos e plano de energia."""
import ctypes
import json
import re
import subprocess
import winreg
from dataclasses import dataclass, field

import backend as bk

NO_WINDOW = bk.CREATE_NO_WINDOW


# ---------------------------------------------------------------- saúde do disco
@dataclass
class DiskInfo:
    name: str
    kind: str
    size: int
    level: str                  # ok | care | bad
    headline: str
    details: list = field(default_factory=list)


def disk_health():
    script = (
        "$o = foreach ($d in Get-PhysicalDisk) { $r = $d | Get-StorageReliabilityCounter -ErrorAction SilentlyContinue; "
        "[pscustomobject]@{ Name=$d.FriendlyName; Media=\"$($d.MediaType)\"; Bus=\"$($d.BusType)\"; "
        "Size=[int64]$d.Size; Health=\"$($d.HealthStatus)\"; Op=\"$($d.OperationalStatus)\"; Temp=$r.Temperature; "
        "Wear=$r.Wear; Hours=$r.PowerOnHours; ReadErr=$r.ReadErrorsTotal; WriteErr=$r.WriteErrorsTotal } }; "
        "$o | ConvertTo-Json -Compress"
    )
    raw = bk.ps(script, timeout=90).strip()
    if not raw:
        return []
    data = json.loads(raw)
    if isinstance(data, dict):
        data = [data]
    out = []
    for d in data:
        kind = {"SSD": "SSD", "HDD": "HD", "SCM": "SCM"}.get(d.get("Media"), "Disco")
        if d.get("Bus") == "NVMe":
            kind = "SSD NVMe"
        level, headline = "ok", "Saudável. Nada a fazer."
        details = [f"Tipo: {kind}  •  Tamanho: {bk.fmt_size(d.get('Size') or 0)}"]
        if d.get("Health") not in ("Healthy", None, ""):
            level, headline = "bad", "O Windows reporta problema neste disco. Faça backup agora."
        elif d.get("Op") and "OK" not in str(d["Op"]):
            level, headline = "bad", "Estado do disco: " + str(d["Op"]) + ". Faça backup e procure suporte."
        wear = d.get("Wear")
        if wear is not None:
            details.append(f"Desgaste: {wear}%")
            if wear >= 95:
                level, headline = "bad", "SSD no fim da vida útil. Troque o quanto antes."
            elif wear >= 80 and level == "ok":
                level, headline = "care", "SSD bem gasto. Planeje a troca e mantenha backup."
        temp = d.get("Temp")
        if temp:
            details.append(f"Temperatura: {temp} °C")
            if temp >= 70 and level == "ok":
                level, headline = "care", "Disco quente. Limpe o gabinete/ventilação."
        hours = d.get("Hours")
        if hours:
            details.append(f"Ligado há {hours // 24} dias no total")
        errs = (d.get("ReadErr") or 0) + (d.get("WriteErr") or 0)
        if errs:
            details.append(f"Erros de leitura/escrita: {errs}")
            if level == "ok":
                level, headline = "care", "O disco já teve erros. Faça backup e vigie."
        if wear is None and temp is None and hours is None:
            details.append("Sem dados detalhados (SMART). Abrir como administrador pode mostrar mais.")
        out.append(DiskInfo(d.get("Name") or "Disco", kind, d.get("Size") or 0, level, headline, details))
    return out


# ------------------------------------------------------------------ diagnóstico
def _reboot_pending():
    for path in (r"SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending",
                 r"SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired"):
        try:
            winreg.CloseKey(winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path))
            return True
        except OSError:
            pass
    return False


def uptime_days():
    k = ctypes.windll.kernel32
    k.GetTickCount64.restype = ctypes.c_ulonglong
    return k.GetTickCount64() / 86_400_000


def _antivirus():
    script = (
        "try { Get-CimInstance -Namespace root/SecurityCenter2 -ClassName AntiVirusProduct -ErrorAction Stop | "
        "ForEach-Object { [pscustomobject]@{ Name=$_.displayName; On=((($_.productState -band 0xF000) -eq 0x1000)) } } "
        "| ConvertTo-Json -Compress } catch { '' }"
    )
    raw = bk.ps(script, timeout=60).strip()
    if not raw:
        return None
    data = json.loads(raw)
    return [data] if isinstance(data, dict) else data


def diagnose():
    """-> [(nível ok|care|bad, texto)]"""
    import startup
    res = []
    for root in bk.fixed_drives():
        try:
            total, _, free = bk.disk_usage(root)
        except OSError:
            continue
        pct = free / total * 100
        txt = f"Disco {root[:2]}: {bk.fmt_size(free)} livres ({pct:.0f}%)."
        res.append(("bad" if pct < 8 else "care" if pct < 15 else "ok",
                    txt + (" Quase cheio, o PC fica lento." if pct < 15 else "")))
    if _reboot_pending():
        res.append(("care", "O Windows está esperando você reiniciar para terminar uma atualização."))
    else:
        res.append(("ok", "Nenhuma reinicialização pendente."))
    up = uptime_days()
    res.append(("care" if up > 14 else "ok",
                f"PC ligado há {up:.0f} dia(s) sem reiniciar." + (" Reiniciar ajuda o desempenho." if up > 14 else "")))
    try:
        av = _antivirus()
        if av is None:
            res.append(("care", "Não consegui verificar o antivírus."))
        elif any(a.get("On") for a in av):
            res.append(("ok", "Antivírus ativo: " + ", ".join(a["Name"] for a in av if a.get("On")) + "."))
        else:
            res.append(("bad", "Nenhum antivírus ativo. Ligue o Segurança do Windows."))
    except Exception:
        res.append(("care", "Não consegui verificar o antivírus."))
    try:
        n = sum(1 for i in startup._list_run() + startup._list_folders() if i.enabled)
        res.append(("care" if n > 12 else "ok", f"{n} programa(s) abrindo junto com o Windows."
                    + (" É muito. Veja a aba Inicialização." if n > 12 else "")))
    except Exception:
        pass
    try:
        for d in disk_health():
            res.append((d.level, f"{d.name}: {d.headline}"))
    except Exception:
        pass
    try:
        plans = power_plans()
        act = next((p for p in plans if p[2]), None)
        if act and ("econom" in act[1].lower() or "saver" in act[1].lower()) and not has_battery():
            res.append(("care", f"Plano de energia '{act[1]}' deixa o PC mais lento. Veja a aba Desempenho."))
    except Exception:
        pass
    return res


# --------------------------------------------------------------------- reparos
def stream_cmd(args, enc="cp850"):
    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                         creationflags=NO_WINDOW)
    buf = b""
    while True:
        chunk = p.stdout.read1(4096)  # devolve assim que chega algo, sem esperar o fim da linha
        if not chunk:
            break
        buf += chunk.replace(b"\x00", b"")
        *done, buf = re.split(rb"[\r\n]+", buf)
        for part in done:
            text = part.decode(enc, errors="replace").strip()
            if text:
                yield text
    tail = buf.decode(enc, errors="replace").strip()
    if tail:
        yield tail
    p.wait()


def sfc():
    return stream_cmd(["sfc", "/scannow"])


def dism_restore():
    return stream_cmd(["Dism.exe", "/Online", "/Cleanup-Image", "/RestoreHealth"])


def dism_cleanup():
    return stream_cmd(["Dism.exe", "/Online", "/Cleanup-Image", "/StartComponentCleanup"])


def chkdsk_scan():
    return stream_cmd(["chkdsk", "C:", "/scan"])


def flush_dns():
    return stream_cmd(["ipconfig", "/flushdns"])


# --------------------------------------------------------------- plano de energia
KNOWN = {
    "balanced": "381b4222-f694-41f0-9685-ff5bb260df2e",
    "high": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
    "saver": "a1841308-3541-4fab-bc81-f71556f20b4a",
    "ultimate": "e9a42b02-d5df-448d-aa00-03f14749eb61",
}
_GUID = r"([0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12})"


def _powercfg(*args):
    r = subprocess.run(["powercfg", *args], capture_output=True, creationflags=NO_WINDOW)
    return r.stdout.decode("cp850", errors="replace")


def power_plans():
    """-> [(guid, nome, ativo)]"""
    out = []
    for line in _powercfg("/list").splitlines():
        m = re.search(_GUID + r"\s+\((.*?)\)(\s*\*)?", line)
        if m:
            out.append((m.group(1).lower(), m.group(2), bool(m.group(3))))
    return out


def set_power_plan(guid):
    return subprocess.run(["powercfg", "/setactive", guid], capture_output=True,
                          creationflags=NO_WINDOW).returncode == 0


def ensure_plan(kind):
    """Devolve o GUID do plano (cria se não existir) ou None."""
    words = {"high": ("alto desempenho", "high performance"), "ultimate": ("máximo", "maximo", "ultimate"),
             "balanced": ("equilibrado", "balanced"), "saver": ("econom", "saver")}[kind]
    for guid, name, _ in power_plans():
        if guid == KNOWN[kind] or any(w in name.lower() for w in words):
            return guid
    m = re.search(_GUID, _powercfg("-duplicatescheme", KNOWN[kind]))
    return m.group(1).lower() if m else None


def set_timeouts(monitor_min, sleep_min):
    for what, val in (("monitor-timeout-ac", monitor_min), ("monitor-timeout-dc", monitor_min),
                      ("standby-timeout-ac", sleep_min), ("standby-timeout-dc", sleep_min)):
        _powercfg("/change", what, str(val))


class _SPS(ctypes.Structure):
    _fields_ = [("AC", ctypes.c_ubyte), ("Flag", ctypes.c_ubyte), ("Pct", ctypes.c_ubyte), ("Sys", ctypes.c_ubyte),
                ("Life", ctypes.c_ulong), ("Full", ctypes.c_ulong)]


def has_battery():
    s = _SPS()
    if ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(s)):
        return s.Flag not in (128, 255)
    return False
