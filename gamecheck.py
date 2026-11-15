"""Verificação para jogos: o que tem efeito comprovado no FPS e costuma estar errado sem a pessoa saber.

- Notebook com duas placas: jogos marcados para usar a placa dedicada (UserGpuPreferences, por usuário, dá pra desfazer).
- Driver de vídeo velho (só avisa e leva ao site do fabricante).
- Monitor abaixo da taxa máxima (troca com um clique; o Windows costuma ficar em 60 Hz).
- RAM sem XMP/EXPO em PC de mesa (só avisa: isso se liga na BIOS).
- Integridade de memória (VBS/HVCI): só mostra e abre a tela do Windows. O app não desliga proteção do Windows.
- HAGS e Modo de Jogo.
"""
import ctypes
import datetime
import glob
import json
import os
import re
import winreg
from ctypes import wintypes

import backend as bk

# ---------------------------------------------------------------- leitura do hardware (um PowerShell só)
_SCRIPT = (
    "$e='SilentlyContinue';"
    "$v=@(Get-CimInstance Win32_VideoController -EA $e|Select Name,AdapterCompatibility,DriverVersion,"
    "@{n='date';e={if($_.DriverDate){$_.DriverDate.ToString('yyyy-MM-dd')}}});"
    "$m=@(Get-CimInstance Win32_PhysicalMemory -EA $e|Select ConfiguredClockSpeed,Speed,SMBIOSMemoryType,FormFactor,PartNumber);"
    "$g=Get-CimInstance -Namespace root\\Microsoft\\Windows\\DeviceGuard Win32_DeviceGuard -EA $e;"
    "$b=@(Get-CimInstance Win32_Battery -EA $e).Count;"
    "[pscustomobject]@{gpus=$v;ram=$m;hvci=[bool](@($g.SecurityServicesRunning) -contains 2);battery=$b}|ConvertTo-Json -Depth 4 -Compress"
)


def _hw():
    try:
        d = json.loads(bk.ps(_SCRIPT, timeout=60) or "{}")
    except ValueError:
        d = {}
    as_list = lambda v: v if isinstance(v, list) else ([v] if v else [])
    return as_list(d.get("gpus")), as_list(d.get("ram")), bool(d.get("hvci")), int(d.get("battery") or 0)


# ------------------------------------------------------------------ placas de vídeo
_VIRTUAL = re.compile(r"basic|remote|virtual|parsec|dummy|meta|mirage|citrix", re.I)
_INTEGRATED = re.compile(r"\b(UHD|HD Graphics|Iris|Radeon\(TM\) Graphics|Radeon Graphics|Vega \d+ Graphics|Arc\(TM\) Graphics)\b", re.I)
_VENDOR = {"nvidia": ("NVIDIA", "https://www.nvidia.com/pt-br/drivers/"),
           "amd": ("AMD", "https://www.amd.com/pt/support/download/drivers.html"),
           "advanced micro": ("AMD", "https://www.amd.com/pt/support/download/drivers.html"),
           "intel": ("Intel", "https://www.intel.com.br/content/www/br/pt/support/detect.html")}


def _vendor(g):
    text = f"{g.get('AdapterCompatibility') or ''} {g.get('Name') or ''}".lower()
    for key, val in _VENDOR.items():
        if key in text:
            return val
    return ("", "")


def gpu_rows(gpus):
    today = datetime.date.today()
    rows = []
    for g in gpus:
        name = g.get("Name") or ""
        if not name or _VIRTUAL.search(name):
            continue
        vendor, url = _vendor(g)
        try:
            days = (today - datetime.date.fromisoformat(g.get("date") or "")).days
        except ValueError:
            days = None
        rows.append({"name": name, "vendor": vendor, "url": url, "version": g.get("DriverVersion") or "",
                     "date": g.get("date") or "", "days": days,
                     "integrated": bool(_INTEGRATED.search(name)) or (vendor == "Intel" and "arc" not in name.lower())})
    return rows


# --------------------------------------------------- jogos na placa dedicada (notebook com duas placas)
_PREF = r"Software\Microsoft\DirectX\UserGpuPreferences"
_HIGH = "GpuPreference=2;"
# pastas do Steam que não são jogos (e não devem ir pra placa dedicada: gastaria bateria à toa)
_NOT_GAMES = {"wallpaper_engine", "steamworks shared", "steamvr", "steam controller configs", "soundpad", "lossless scaling",
              "spacewar", "steam linux runtime", "proton experimental"}
_SKIP_EXE = re.compile(r"unins|setup|install|redist|vcredist|directx|dxsetup|crash|report|helper|launcher|updater|"
                       r"easyanticheat|battleye|\bbe_|ue4prereq|dotnet|vc_|cefprocess|webhelper|uploader", re.I)


def _steam_libraries():
    steam = bk._steam_path()
    if not steam:
        return []
    libs = [steam]
    try:
        with open(os.path.join(steam, "steamapps", "libraryfolders.vdf"), encoding="utf-8", errors="replace") as f:
            libs += [p.replace("\\\\", "\\") for p in re.findall(r'"path"\s+"([^"]+)"', f.read())]
    except OSError:
        pass
    seen, out = set(), []
    for lib in libs:
        common = os.path.normcase(os.path.normpath(os.path.join(lib, "steamapps", "common")))
        if common not in seen and os.path.isdir(common):
            seen.add(common)
            out.append(common)
    return out


def _epic_games():
    """[(nome, exe)] pelos manifestos do Epic Games Launcher (eles dizem qual é o .exe do jogo)."""
    out = []
    for item in glob.glob(os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"), r"Epic\EpicGamesLauncher\Data\Manifests\*.item")):
        try:
            with open(item, encoding="utf-8") as f:
                m = json.load(f)
            exe = os.path.join(m["InstallLocation"], m["LaunchExecutable"])
        except (OSError, ValueError, KeyError):
            continue
        if os.path.isfile(exe):
            out.append((m.get("DisplayName") or os.path.basename(exe), exe))
    return out


def _game_exes(folder, depth=3):
    """Executáveis de um jogo instalado (pula desinstalador, instaladores de dependência, anti-cheat etc.)."""
    found = []
    base = folder.rstrip("\\").count("\\")
    for root, dirs, files in os.walk(folder):
        if root.count("\\") - base >= depth:
            dirs[:] = []
        dirs[:] = [d for d in dirs if not re.search(r"redist|_commonredist|directx|support|prereq", d, re.I)]
        for f in files:
            if f.lower().endswith(".exe") and not _SKIP_EXE.search(f):
                p = os.path.join(root, f)
                try:
                    if os.path.getsize(p) > 1_000_000:
                        found.append(p)
                except OSError:
                    pass
    return found


def find_games():
    """[{name, exes}] dos jogos do Steam e da Epic neste PC."""
    games = []
    for common in _steam_libraries():
        try:
            names = sorted(os.listdir(common))
        except OSError:
            continue
        for name in names:
            if name.lower() in _NOT_GAMES or name.lower().startswith(("proton ", "steam linux")):
                continue
            exes = _game_exes(os.path.join(common, name))
            if exes:
                games.append({"name": name, "exes": exes})
    for name, exe in _epic_games():
        games.append({"name": name, "exes": [exe]})
    return games


def _read_prefs():
    out = {}
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _PREF) as k:
            i = 0
            while True:
                try:
                    n, v, _ = winreg.EnumValue(k, i)
                except OSError:
                    break
                out[os.path.normcase(n)] = v
                i += 1
    except OSError:
        pass
    return out


def gpu_pref_state(games):
    prefs = _read_prefs()
    total = sum(len(g["exes"]) for g in games)
    done = sum(1 for g in games for e in g["exes"] if prefs.get(os.path.normcase(e)) == _HIGH)
    return {"games": len(games), "exes": total, "set": done}


def gpu_pref_apply(games):
    """Marca os .exe dos jogos para a placa dedicada. -> lista do que o app gravou (para desfazer depois)."""
    prefs, written = _read_prefs(), []
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, _PREF, 0, winreg.KEY_SET_VALUE) as k:
        for g in games:
            for e in g["exes"]:
                if os.path.normcase(e) not in prefs:          # não mexe no que a pessoa já escolheu no Windows
                    winreg.SetValueEx(k, e, 0, winreg.REG_SZ, _HIGH)
                    written.append(e)
    return written


def gpu_pref_undo(written):
    """Apaga só o que o app gravou e que ainda está como placa dedicada."""
    prefs, n = _read_prefs(), 0
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _PREF, 0, winreg.KEY_SET_VALUE) as k:
            for e in written:
                if prefs.get(os.path.normcase(e)) == _HIGH:
                    try:
                        winreg.DeleteValue(k, e)
                        n += 1
                    except OSError:
                        pass
    except OSError:
        pass
    return n


# ------------------------------------------------------------------- taxa de atualização
class _DEVMODE(ctypes.Structure):
    _fields_ = [("dmDeviceName", wintypes.WCHAR * 32), ("dmSpecVersion", wintypes.WORD), ("dmDriverVersion", wintypes.WORD),
                ("dmSize", wintypes.WORD), ("dmDriverExtra", wintypes.WORD), ("dmFields", wintypes.DWORD),
                ("dmPosition", ctypes.c_long * 2), ("dmDisplayOrientation", wintypes.DWORD), ("dmDisplayFixedOutput", wintypes.DWORD),
                ("dmColor", ctypes.c_short), ("dmDuplex", ctypes.c_short), ("dmYResolution", ctypes.c_short),
                ("dmTTOption", ctypes.c_short), ("dmCollate", ctypes.c_short), ("dmFormName", wintypes.WCHAR * 32),
                ("dmLogPixels", wintypes.WORD), ("dmBitsPerPel", wintypes.DWORD), ("dmPelsWidth", wintypes.DWORD),
                ("dmPelsHeight", wintypes.DWORD), ("dmDisplayFlags", wintypes.DWORD), ("dmDisplayFrequency", wintypes.DWORD),
                ("rest", wintypes.DWORD * 8)]


class _DISPLAY_DEVICE(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("DeviceName", wintypes.WCHAR * 32), ("DeviceString", wintypes.WCHAR * 128),
                ("StateFlags", wintypes.DWORD), ("DeviceID", wintypes.WCHAR * 128), ("DeviceKey", wintypes.WCHAR * 128)]


_u32 = ctypes.WinDLL("user32")
_ATTACHED, _PRIMARY = 0x1, 0x4
_DM_FREQ = 0x400000
_CDS_UPDATEREGISTRY = 0x1


def _mode(dev, i):
    dm = _DEVMODE()
    dm.dmSize = ctypes.sizeof(_DEVMODE)
    return dm if _u32.EnumDisplaySettingsW(dev, i, ctypes.byref(dm)) else None


def displays():
    """[{device, name, primary, width, height, hz, max_hz}] dos monitores ligados."""
    out, i = [], 0
    while True:
        dd = _DISPLAY_DEVICE()
        dd.cb = ctypes.sizeof(dd)
        if not _u32.EnumDisplayDevicesW(None, i, ctypes.byref(dd), 0):
            break
        i += 1
        if not dd.StateFlags & _ATTACHED:
            continue
        cur = _mode(dd.DeviceName, -1)                         # ENUM_CURRENT_SETTINGS
        if not cur:
            continue
        best, j = cur.dmDisplayFrequency, 0
        while True:
            m = _mode(dd.DeviceName, j)
            if not m:
                break
            j += 1
            if (m.dmPelsWidth, m.dmPelsHeight) == (cur.dmPelsWidth, cur.dmPelsHeight) and m.dmBitsPerPel == cur.dmBitsPerPel:
                best = max(best, m.dmDisplayFrequency)
        mon = _DISPLAY_DEVICE()
        mon.cb = ctypes.sizeof(mon)
        name = mon.DeviceString if _u32.EnumDisplayDevicesW(dd.DeviceName, 0, ctypes.byref(mon), 0) else dd.DeviceString
        out.append({"device": dd.DeviceName, "name": name, "primary": bool(dd.StateFlags & _PRIMARY),
                    "width": cur.dmPelsWidth, "height": cur.dmPelsHeight, "hz": cur.dmDisplayFrequency, "max_hz": best})
    return out


def set_refresh(device, hz):
    """Troca só a frequência, mantendo a resolução. -> (ok, mensagem)."""
    cur = _mode(device, -1)
    if not cur:
        return False, "Não achei esse monitor."
    cur.dmDisplayFrequency = int(hz)
    cur.dmFields = _DM_FREQ
    r = _u32.ChangeDisplaySettingsExW(device, ctypes.byref(cur), None, _CDS_UPDATEREGISTRY, None)
    if r != 0:
        return False, f"O Windows não aceitou {hz} Hz (código {r}). Confira o cabo: em alta taxa costuma precisar de DisplayPort."
    return True, f"Monitor agora em {hz} Hz."


# ------------------------------------------------------------------------- RAM
_DDR = {26: "DDR4", 34: "DDR5", 24: "DDR3"}
_JEDEC_LOW = {"DDR4": 2400, "DDR5": 4800}       # até aqui, em PC de mesa, é sinal de XMP/EXPO desligado


def ram_state(ram, battery):
    if not ram:
        return None
    kind = _DDR.get(int(ram[0].get("SMBIOSMemoryType") or 0), "")
    speed = min(int(m.get("ConfiguredClockSpeed") or 0) for m in ram)
    desktop = all(int(m.get("FormFactor") or 0) == 8 for m in ram) and not battery     # 8 = DIMM (pente de PC de mesa)
    suspect = desktop and kind in _JEDEC_LOW and 0 < speed <= _JEDEC_LOW[kind]
    return {"kind": kind, "speed": speed, "sticks": len(ram), "desktop": desktop, "suspect": suspect}


# ---------------------------------------------------------------- HAGS e Modo de Jogo
_GFX = r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers"


def _reg(hive, path, name):
    try:
        with winreg.OpenKey(hive, path) as k:
            return winreg.QueryValueEx(k, name)[0]
    except OSError:
        return None


def hags_state():
    v = _reg(winreg.HKEY_LOCAL_MACHINE, _GFX, "HwSchMode")
    return None if v is None else v == 2


def hags_set(on):
    """Precisa de administrador e de reiniciar o PC."""
    try:
        with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, _GFX, 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, "HwSchMode", 0, winreg.REG_DWORD, 2 if on else 1)
    except OSError as e:
        return False, f"O Windows não deixou gravar ({e.strerror or e}). Precisa de administrador."
    return True, f"Agendamento de GPU {'ligado' if on else 'desligado'}. Reinicie o PC para valer."


def game_mode_on():
    return _reg(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\GameBar", "AutoGameModeEnabled") != 0


def game_mode_enable():
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\GameBar", 0, winreg.KEY_SET_VALUE) as k:
        winreg.SetValueEx(k, "AutoGameModeEnabled", 0, winreg.REG_DWORD, 1)
    return True, "Modo de Jogo ligado."


# ----------------------------------------------------------------------------- tudo
def scan():
    gpus, ram, hvci, battery = _hw()
    rows = gpu_rows(gpus)
    hybrid = any(g["integrated"] for g in rows) and any(not g["integrated"] for g in rows)
    games = find_games() if hybrid else []
    return {"gpus": rows, "hybrid": hybrid, "games": games, "gpu_pref": gpu_pref_state(games) if hybrid else None,
            "displays": displays(), "ram": ram_state(ram, battery), "hvci": hvci,
            "hags": hags_state(), "game_mode": game_mode_on()}
