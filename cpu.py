"""Controle de clock da CPU pelo plano de energia ativo (powercfg)."""
import re
import subprocess

import backend as bk

SUB = "54533251-82be-4824-96c1-47b60b740d00"  # SUB_PROCESSOR
SETTINGS = {
    "min": "893dee8e-2bef-41e0-89c6-b55d0929964c",    # estado mínimo do processador (%)
    "max": "bc5038f7-23e0-4960-96da-33abaf5935ec",    # estado máximo do processador (%)
    "boost": "be337238-0d82-4146-a960-4f3749d470c7",  # modo de turbo
    "freq": "75b0ae3f-bce0-45a7-8c89-c9611c25e100",   # limite de frequência em MHz (0 = sem limite)
}
BOOST_MODES = {"Desligado (sem turbo)": 0, "Normal": 1, "Agressivo": 2}

# nome -> (mínimo %, máximo %, turbo, limite MHz)
PRESETS = {
    "🧊 Frio e silencioso": (5, 70, 0, 0),
    "⚖ Normal": (5, 100, 1, 0),
    "🔥 Turbo total": (100, 100, 2, 0),
}


def _powercfg(*args):
    r = subprocess.run(["powercfg", *args], capture_output=True, stdin=subprocess.DEVNULL,
                       creationflags=bk.CREATE_NO_WINDOW)
    return r.stdout.decode("cp850", errors="replace")


def read(key):
    """-> (valor na tomada, valor na bateria) ou None se o PC não tem essa opção."""
    out = _powercfg("/query", "SCHEME_CURRENT", SUB, SETTINGS[key])
    hexes = re.findall(r"0x([0-9a-fA-F]{8})", out)
    if len(hexes) < 2:
        return None
    return int(hexes[-2], 16), int(hexes[-1], 16)


def write(key, value, battery=True):
    """Grava na tomada (e na bateria, se `battery`). Não ativa: chame `activate()` depois."""
    _powercfg("/setacvalueindex", "SCHEME_CURRENT", SUB, SETTINGS[key], str(int(value)))
    if battery:
        _powercfg("/setdcvalueindex", "SCHEME_CURRENT", SUB, SETTINGS[key], str(int(value)))


def write_pair(key, ac, dc):
    """Grava valores separados para tomada e bateria (usado para restaurar o original exato)."""
    _powercfg("/setacvalueindex", "SCHEME_CURRENT", SUB, SETTINGS[key], str(int(ac)))
    _powercfg("/setdcvalueindex", "SCHEME_CURRENT", SUB, SETTINGS[key], str(int(dc)))


def activate():
    _powercfg("/setactive", "SCHEME_CURRENT")


def snapshot():
    """Valores atuais (da tomada) de todas as opções. None = opção não existe neste PC."""
    out = {}
    for k in SETTINGS:
        v = read(k)
        out[k] = v[0] if v else None
    return out


def unhide():
    """Mostra turbo e limite de MHz, que o Windows esconde em vários PCs. Precisa de administrador."""
    for k in ("boost", "freq"):
        _powercfg("-attributes", SUB, SETTINGS[k], "-ATTRIB_HIDE")


def snapshot_unlocked():
    """Como `snapshot()`, mas tenta liberar as opções escondidas se for administrador."""
    s = snapshot()
    if (s["boost"] is None or s["freq"] is None) and bk.is_admin():
        unhide()
        s = snapshot()
    return s


def apply(min_pct, max_pct, boost=None, mhz=None):
    """Aplica no plano ativo. `boost`/`mhz` = None pula (opção indisponível)."""
    min_pct = max(0, min(100, int(min_pct)))
    max_pct = max(min_pct, min(100, int(max_pct)))
    write("min", min_pct)
    write("max", max_pct)
    if boost is not None:
        write("boost", boost)
    if mhz is not None:
        write("freq", mhz)
    activate()


def info():
    """-> (nome da CPU, clock base em MHz, núcleos lógicos)"""
    raw = bk.ps("$c = Get-CimInstance Win32_Processor | Select-Object -First 1; "
                "\"$($c.Name.Trim())|$($c.MaxClockSpeed)|$($c.NumberOfLogicalProcessors)\"", timeout=30).strip()
    try:
        name, mhz, cores = raw.split("|")
        return name, int(mhz), int(cores)
    except ValueError:
        return "CPU", 0, 0


def live():
    """-> (clock real em MHz, uso da CPU em %) ou None."""
    raw = bk.ps(
        "$p = Get-CimInstance Win32_PerfFormattedData_Counters_ProcessorInformation -Filter \"Name='_Total'\"; "
        "\"$($p.ProcessorFrequency)|$($p.PercentProcessorPerformance)|$($p.PercentProcessorUtility)\"",
        timeout=20).strip()
    try:
        base, perf, util = (float(x.replace(",", ".")) for x in raw.split("|"))
    except ValueError:
        return None
    return base * perf / 100.0, min(util, 100.0)
