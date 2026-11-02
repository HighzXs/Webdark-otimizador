"""Memória RAM: lista de espera (standby), limpeza e congelamento por programa, arquivo de paginação e SvcHost."""
import ctypes
import json
import os
import threading
import time
import winreg
from ctypes import wintypes

import psutil

import backend as bk

PAGE = 4096
MB = 1024 * 1024
GB = 1024 * MB

_nt = ctypes.WinDLL("ntdll")
_k32 = ctypes.WinDLL("kernel32", use_last_error=True)
_adv = ctypes.WinDLL("advapi32", use_last_error=True)
_psapi = ctypes.WinDLL("psapi", use_last_error=True)
_u32 = ctypes.WinDLL("user32")

_nt.NtQuerySystemInformation.argtypes = [wintypes.ULONG, ctypes.c_void_p, wintypes.ULONG, ctypes.c_void_p]
_nt.NtQuerySystemInformation.restype = ctypes.c_long
_nt.NtSetSystemInformation.argtypes = [wintypes.ULONG, ctypes.c_void_p, wintypes.ULONG]
_nt.NtSetSystemInformation.restype = ctypes.c_long
_k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
_k32.OpenProcess.restype = wintypes.HANDLE
_k32.CloseHandle.argtypes = [wintypes.HANDLE]
_k32.GetCurrentProcess.restype = wintypes.HANDLE
_k32.SetProcessInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
_psapi.EmptyWorkingSet.argtypes = [wintypes.HANDLE]
_adv.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
_adv.LookupPrivilegeValueW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.c_void_p]
_adv.AdjustTokenPrivileges.argtypes = [wintypes.HANDLE, wintypes.BOOL, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p, ctypes.c_void_p]
_u32.GetForegroundWindow.restype = wintypes.HWND
_u32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]

_SystemMemoryListInformation = 80
_PURGE_LOW_STANDBY, _PURGE_STANDBY = 5, 4


# ---------------------------------------------------------------- permissões
class _LUID(ctypes.Structure):
    _fields_ = [("lo", wintypes.DWORD), ("hi", wintypes.LONG)]


class _TOKEN_PRIV(ctypes.Structure):
    _fields_ = [("count", wintypes.DWORD), ("luid", _LUID), ("attr", wintypes.DWORD)]


def _enable_privilege(name):
    """Liga um privilégio que o administrador já tem mas o Windows deixa desligado no processo. False se não deu."""
    tok = wintypes.HANDLE()
    if not _adv.OpenProcessToken(_k32.GetCurrentProcess(), 0x28, ctypes.byref(tok)):      # ADJUST_PRIVILEGES | QUERY
        return False
    try:
        luid = _LUID()
        if not _adv.LookupPrivilegeValueW(None, name, ctypes.byref(luid)):
            return False
        tp = _TOKEN_PRIV(1, luid, 2)                                                       # SE_PRIVILEGE_ENABLED
        ctypes.set_last_error(0)
        _adv.AdjustTokenPrivileges(tok, False, ctypes.byref(tp), 0, None, None)
        return ctypes.get_last_error() == 0                                                # 1300 = o processo não tem esse privilégio
    finally:
        _k32.CloseHandle(tok)


# ------------------------------------------------------------- RAM e lista de espera
class _MEMLIST(ctypes.Structure):
    _fields_ = [("zero", ctypes.c_size_t), ("free", ctypes.c_size_t), ("modified", ctypes.c_size_t),
                ("modified_nowrite", ctypes.c_size_t), ("bound", ctypes.c_size_t),
                ("by_priority", ctypes.c_size_t * 8), ("repurposed", ctypes.c_size_t * 8), ("modified_pf", ctypes.c_size_t)]


def _standby_bytes():
    """Tamanho da lista de espera (cache de arquivos que o Windows guarda na RAM). None sem administrador."""
    if not bk.is_admin() or not _enable_privilege("SeProfileSingleProcessPrivilege"):
        return None
    s = _MEMLIST()
    if _nt.NtQuerySystemInformation(_SystemMemoryListInformation, ctypes.byref(s), ctypes.sizeof(s), None) != 0:
        return None
    return sum(s.by_priority) * PAGE


def ram_info():
    vm = psutil.virtual_memory()
    return {"total": vm.total, "avail": vm.available, "percent": vm.percent, "standby": _standby_bytes()}


def purge_standby(full):
    """Esvazia a lista de espera. `full=False` só solta a de prioridade baixa: bem mais suave, não faz o jogo engasgar."""
    if not bk.is_admin():
        return {"ok": False, "msg": "Precisa de administrador. Use “Reabrir como administrador”."}
    if not _enable_privilege("SeProfileSingleProcessPrivilege"):
        return {"ok": False, "msg": "O Windows não liberou a permissão de memória para este programa."}
    before = ram_info()
    cmd = ctypes.c_int(_PURGE_STANDBY if full else _PURGE_LOW_STANDBY)
    st = _nt.NtSetSystemInformation(_SystemMemoryListInformation, ctypes.byref(cmd), 4)
    if st != 0:
        return {"ok": False, "msg": f"O Windows recusou (código 0x{st & 0xFFFFFFFF:08X})."}
    time.sleep(0.4)
    after = ram_info()
    freed = max(0, (before["standby"] or 0) - (after["standby"] or 0))
    return {"ok": True, "msg": f"Lista de espera esvaziada: {bk.fmt_size(freed)} liberados.", "ram": after}


# ------------------------------------------------------------ programas em segundo plano
# id: (nome, tipo, executáveis, pode congelar, aviso ao congelar)
GROUPS = {
    "chrome": ("Google Chrome", "Navegador", ("chrome.exe",), True, "abas e downloads param"),
    "msedge": ("Microsoft Edge", "Navegador", ("msedge.exe",), True, "abas e downloads param"),
    "opera": ("Opera / Opera GX", "Navegador", ("opera.exe",), True, "abas e downloads param"),
    "brave": ("Brave", "Navegador", ("brave.exe",), True, "abas e downloads param"),
    "firefox": ("Firefox", "Navegador", ("firefox.exe",), True, "abas e downloads param"),
    "discord": ("Discord", "Launcher", ("discord.exe",), True, "você sai do chat de voz e não recebe mensagens"),
    "spotify": ("Spotify", "Launcher", ("spotify.exe",), True, "a música para"),
    "steam": ("Steam (janelas e loja)", "Launcher", ("steamwebhelper.exe",), False, ""),   # o overlay do jogo usa esse processo
}


def _foreground_pid():
    pid = wintypes.DWORD()
    _u32.GetWindowThreadProcessId(_u32.GetForegroundWindow(), ctypes.byref(pid))
    return pid.value


def _procs(gid):
    exes = GROUPS[gid][2]
    out = []
    for p in psutil.process_iter(["name"]):
        try:
            if (p.info["name"] or "").lower() in exes:
                out.append(p)
        except psutil.Error:
            pass
    return out


def _rss(procs):
    total = 0
    for p in procs:
        try:
            total += p.memory_info().rss
        except psutil.Error:
            pass
    return total


def _open(pid, access):
    return _k32.OpenProcess(access, False, pid)


def _empty_working_set(pid):
    h = _open(pid, 0x0400 | 0x0100)                 # QUERY_INFORMATION | SET_QUOTA
    if not h:
        return False
    try:
        return bool(_psapi.EmptyWorkingSet(h))
    finally:
        _k32.CloseHandle(h)


def _set_memory_priority(pid, value):
    """1 = muito baixa ... 5 = normal. O Windows tira da RAM primeiro o que tem prioridade baixa."""
    h = _open(pid, 0x0200)                          # SET_INFORMATION
    if not h:
        return False
    try:
        v = wintypes.ULONG(value)
        return bool(_k32.SetProcessInformation(h, 0, ctypes.byref(v), 4))     # ProcessMemoryPriority
    finally:
        _k32.CloseHandle(h)


def group_rows(frozen):
    """Só os programas da lista que estão abertos agora. `frozen` = Freezer.state()."""
    fg = _foreground_pid()
    rows = []
    for gid, (label, kind, _exes, can_freeze, warn) in GROUPS.items():
        procs = _procs(gid)
        if not procs and gid not in frozen:
            continue
        rows.append({"id": gid, "label": label, "kind": kind, "count": len(procs), "rss": _rss(procs),
                     "can_freeze": can_freeze, "freeze_warn": warn, "foreground": any(p.pid == fg for p in procs),
                     "frozen": frozen.get(gid)})
    return rows


def trim_group(gid):
    """Devolve à RAM livre o que o programa guardou sem usar agora. Ele pega de volta o que precisar."""
    if gid not in GROUPS:
        return {"ok": False, "msg": "Programa desconhecido."}
    procs = _procs(gid)
    if not procs:
        return {"ok": False, "msg": "Esse programa não está aberto."}
    fg = _foreground_pid()
    if any(p.pid == fg for p in procs):
        return {"ok": False, "msg": f"Você está usando o {GROUPS[gid][0]} agora. Troque de janela e tente de novo."}
    before = _rss(procs)
    for p in procs:
        _empty_working_set(p.pid)
    time.sleep(0.3)
    freed = max(0, before - _rss(procs))
    return {"ok": True, "msg": f"{GROUPS[gid][0]}: {bk.fmt_size(freed)} liberados.", "freed": freed}


def lower_group(gid, on):
    """Prioridade de memória e de processador mais baixas (ou de volta ao normal) para o programa e seus filhos."""
    if gid not in GROUPS:
        return {"ok": False, "msg": "Programa desconhecido."}
    procs = _procs(gid)
    if not procs:
        return {"ok": False, "msg": "Esse programa não está aberto."}
    fg = _foreground_pid()
    if on and any(p.pid == fg for p in procs):
        return {"ok": False, "msg": f"Você está usando o {GROUPS[gid][0]} agora. Troque de janela e tente de novo."}
    done = 0
    for p in procs:
        try:
            p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS if on else psutil.NORMAL_PRIORITY_CLASS)
            if _set_memory_priority(p.pid, 2 if on else 5):
                done += 1
        except psutil.Error:
            pass
    if not done:
        return {"ok": False, "msg": "O Windows não deixou mexer nesses processos."}
    return {"ok": True, "msg": f"{GROUPS[gid][0]}: prioridade {'baixa' if on else 'normal'} em {done} processos."}


# --------------------------------------------------------------------- congelar
def _data_file():
    base = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "FaxinaVarzea")
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "frozen.json")


class Freezer:
    """Congela (suspende) programas da lista durante um jogo. Regras que evitam deixar algo travado pra sempre:
    só os programas de GROUPS; nunca o que está na frente; sempre com prazo; tudo volta ao fechar o WebDark;
    e, se o WebDark for morto à força, na próxima abertura ele descongela o que ficou (confere PID + hora de criação)."""

    def __init__(self):
        self._lock = threading.Lock()
        self._items = {}              # gid -> {"since", "until", "procs": [[pid, create_time], ...]}
        self._stop = threading.Event()
        self._resume_leftovers()
        threading.Thread(target=self._watch, daemon=True).start()

    # ---- persistência
    def _save(self):
        try:
            if self._items:
                with open(_data_file(), "w", encoding="utf-8") as f:
                    json.dump(self._items, f)
            elif os.path.exists(_data_file()):
                os.remove(_data_file())
        except OSError:
            pass

    @staticmethod
    def _resume_procs(procs):
        for pid, ct in procs:
            try:
                p = psutil.Process(pid)
                if abs(p.create_time() - ct) < 1:         # mesmo processo (o PID pode ter sido reaproveitado)
                    p.resume()
            except psutil.Error:
                pass

    def _resume_leftovers(self):
        try:
            with open(_data_file(), encoding="utf-8") as f:
                old = json.load(f)
        except (OSError, ValueError):
            return
        for rec in old.values():
            self._resume_procs(rec.get("procs", []))
        self._save()

    def _watch(self):
        while not self._stop.wait(5):
            now = time.time()
            with self._lock:
                late = [g for g, r in self._items.items() if r["until"] <= now]
            for g in late:
                self.unfreeze(g)

    # ---- uso
    def state(self):
        now = time.time()
        with self._lock:
            return {g: {"since": r["since"], "left": max(0, int(r["until"] - now)), "auto": bool(r.get("auto"))}
                    for g, r in self._items.items()}

    def freeze(self, gid, minutes, auto=False):
        g = GROUPS.get(gid)
        if g is None or not g[3]:
            return {"ok": False, "msg": "Esse programa não pode ser congelado."}
        if self._stop.is_set():                                # o WebDark está fechando: não congela mais nada
            return {"ok": False, "msg": "O WebDark está fechando."}
        minutes = max(5, min(480 if auto else 120, int(minutes)))
        with self._lock:
            if gid in self._items:
                return {"ok": False, "msg": "Já está congelado."}
        procs = _procs(gid)
        if not procs:
            return {"ok": False, "msg": "Esse programa não está aberto."}
        fg = _foreground_pid()
        if any(p.pid == fg for p in procs):
            return {"ok": False, "msg": f"Você está usando o {g[0]} agora. Troque de janela e tente de novo."}
        held = []
        for p in procs:
            try:
                ct = p.create_time()
                p.suspend()
                held.append([p.pid, ct])
            except psutil.Error:
                pass
        if not held:
            return {"ok": False, "msg": "O Windows não deixou congelar. Tente reabrir como administrador."}
        for pid, _ in held:                                    # parado, o programa não usa mais a RAM: devolve tudo
            _empty_working_set(pid)
        now = time.time()
        with self._lock:
            self._items[gid] = {"since": now, "until": now + minutes * 60, "procs": held, "auto": auto}
            self._save()
        return {"ok": True, "msg": f"{g[0]} congelado por até {minutes} min ({len(held)} processos)."}

    def unfreeze(self, gid=None, only_auto=False):
        with self._lock:
            ids = [gid] if gid else [i for i, r in self._items.items() if r.get("auto") or not only_auto]
            recs = [self._items.pop(i) for i in ids if i in self._items]
            self._save()
        for r in recs:
            self._resume_procs(r["procs"])
        return {"ok": True, "msg": "Descongelado." if recs else "Nada estava congelado."}

    def shutdown(self):
        self._stop.set()
        self.unfreeze()


# ----------------------------------------------------------- congelar sozinho ao jogar
_shell = ctypes.WinDLL("shell32")
_shell.SHQueryUserNotificationState.argtypes = [ctypes.POINTER(ctypes.c_int)]

# o que nunca conta como jogo, mesmo em tela cheia (vídeo, apresentação, navegador em F11)
NOT_GAMES = {"chrome.exe", "msedge.exe", "opera.exe", "brave.exe", "firefox.exe", "vivaldi.exe", "vlc.exe", "mpv.exe",
             "potplayermini64.exe", "wmplayer.exe", "explorer.exe", "powerpnt.exe", "acrobat.exe", "acrord32.exe", "teams.exe",
             "zoom.exe", "discord.exe", "spotify.exe", "webdark.exe", "python.exe", "pythonw.exe", "obs64.exe", "steam.exe",
             "battle.net.exe", "epicgameslauncher.exe", "applicationframehost.exe", "searchhost.exe", "shellexperiencehost.exe"}
GAME_PATHS = ("steamapps\\common", "epic games\\", "riot games\\", "gog galaxy\\games", "xboxgames\\", "ea games\\",
              "ubisoft game launcher\\games", "rockstar games\\")


def foreground_game():
    """Nome do jogo que está na frente agora, ou None. Jogo = tela cheia (o Windows avisa) ou programa de pasta de jogos."""
    pid = _foreground_pid()
    if not pid or pid == os.getpid():
        return None
    try:
        p = psutil.Process(pid)
        name, exe = p.name().lower(), (p.exe() or "").lower()
    except psutil.Error:
        return None
    if name in NOT_GAMES or "launcher" in name:
        return None
    st = ctypes.c_int(0)
    _shell.SHQueryUserNotificationState(ctypes.byref(st))
    if st.value in (2, 3) or any(h in exe for h in GAME_PATHS):          # 2 = tela cheia, 3 = jogo em tela cheia exclusiva
        return name
    return None


def mic_cam_exes():
    """Nomes dos programas usando microfone ou câmera neste instante (chamada de voz/vídeo). Vem do registro de privacidade do Windows."""
    out = set()
    for cap in ("microphone", "webcam"):
        base = rf"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\{cap}\NonPackaged"
        try:
            k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, base)
        except OSError:
            continue
        with k:
            i = 0
            while True:
                try:
                    sub = winreg.EnumKey(k, i)
                except OSError:
                    break
                i += 1
                try:
                    with winreg.OpenKey(k, sub) as s:
                        start = winreg.QueryValueEx(s, "LastUsedTimeStart")[0]
                        stop = winreg.QueryValueEx(s, "LastUsedTimeStop")[0]
                except OSError:
                    continue
                if start and not stop:
                    out.add(sub.split("#")[-1].lower())
    return out


class AutoFreeze:
    """Joguei? Congela sozinho os programas escolhidos (que não estão em chamada) e descongela quando o jogo sai da frente.
    Confere a cada 4 s: 2 leituras seguidas com jogo para congelar, 3 sem jogo para descongelar (alt-tab rápido não pisca).
    Se você voltar pra um programa congelado, ele é descongelado na hora."""

    def __init__(self, freezer, get_cfg, notify):
        self._fz, self._cfg, self._notify = freezer, get_cfg, notify
        self.game, self.skipped = None, {}
        self._on_ticks = self._off_ticks = 0
        self._retry = {}
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while True:
            time.sleep(4)
            try:
                self._tick()
            except Exception:
                pass

    def _tick(self):
        cfg = self._cfg()
        if not cfg.get("on"):
            if self.game or self._fz.state():
                self._release()
            self._on_ticks = self._off_ticks = 0
            return
        fg = _foreground_pid()
        for gid in list(self._fz.state()):                       # voltou pra um congelado: libera na hora
            if any(p.pid == fg for p in _procs(gid)):
                self._fz.unfreeze(gid)
                self._notify(f"{GROUPS[gid][0]} descongelado: você voltou pra ele.")
        game = foreground_game()
        if game:
            self._off_ticks = 0
            self._on_ticks += 1
            if self.game != game and self._on_ticks >= 2:
                self.game = game
                self._notify(f"Jogo detectado ({game}).")
            if self._on_ticks >= 2:
                self._freeze_eligible(cfg)
        else:
            self._on_ticks = 0
            if self.game:
                self._off_ticks += 1
                if self._off_ticks >= 3:
                    self._release()

    def _freeze_eligible(self, cfg):
        busy, frozen, now = mic_cam_exes(), self._fz.state(), time.time()
        self.skipped = {}
        for gid in cfg.get("groups", []):
            g = GROUPS.get(gid)
            if g is None or not g[3] or gid in frozen or not _procs(gid):
                continue
            if any(e in busy for e in g[2]):
                self.skipped[gid] = "em chamada (microfone ou câmera ligados)"
                continue
            if now - self._retry.get(gid, 0) < 30:
                continue
            self._retry[gid] = now
            r = self._fz.freeze(gid, 480, auto=True)
            if r["ok"]:
                self._notify(f"{g[0]} congelado enquanto você joga.")

    def _release(self):
        had = any(v["auto"] for v in self._fz.state().values())
        self._fz.unfreeze(only_auto=True)
        self.game, self.skipped = None, {}
        self._on_ticks = self._off_ticks = 0
        if had:
            self._notify("Jogo fechado: programas descongelados.")

    def status(self):
        return {"game": self.game, "skipped": self.skipped}


# ------------------------------------------------------------- arquivo de paginação
def _ram_gb():
    return max(1, round(psutil.virtual_memory().total / GB))


def pagefile_suggest(ram_gb, free_mb):
    """(inicial, máximo) em MB. Segue o tamanho da RAM; nunca passa de 40% do espaço livre do disco."""
    if ram_gb <= 4:
        init, mx = ram_gb * 1536, ram_gb * 3072
    elif ram_gb <= 8:
        init, mx = ram_gb * 1024, ram_gb * 2048
    elif ram_gb <= 16:
        init, mx = ram_gb * 512, ram_gb * 1024
    else:
        init, mx = 8192, 16384
    cap = int(free_mb * 0.4)
    mx = max(1024, min(mx, cap))
    return min(init, mx), mx


def pagefile_info():
    drive = os.environ.get("SystemDrive", "C:")
    try:
        free_mb = psutil.disk_usage(drive + "\\").free // MB
    except OSError:
        free_mb = 0
    script = ("$cs=Get-CimInstance Win32_ComputerSystem;"
              "$s=@(Get-CimInstance Win32_PageFileSetting|Select Name,InitialSize,MaximumSize);"
              "$u=@(Get-CimInstance Win32_PageFileUsage|Select Name,AllocatedBaseSize,CurrentUsage,PeakUsage);"
              "[pscustomobject]@{auto=[bool]$cs.AutomaticManagedPagefile;set=$s;use=$u}|ConvertTo-Json -Depth 4 -Compress")
    try:
        d = json.loads(bk.ps(script, timeout=40) or "{}")
    except ValueError:
        d = {}
    as_list = lambda v: v if isinstance(v, list) else ([v] if v else [])
    gb = _ram_gb()
    init, mx = pagefile_suggest(gb, free_mb)
    return {"ram_gb": gb, "drive": drive, "free_mb": int(free_mb), "auto": bool(d.get("auto", True)),
            "set": as_list(d.get("set")), "use": as_list(d.get("use")), "suggest": {"initial": init, "maximum": mx}}


def pagefile_apply(initial, maximum):
    """Define tamanho fixo (em MB) no disco do Windows. Vale depois de reiniciar."""
    try:
        initial, maximum = int(initial), int(maximum)
    except (TypeError, ValueError):
        return False, "Valores inválidos."
    drive = os.environ.get("SystemDrive", "C:")
    free_mb = psutil.disk_usage(drive + "\\").free // MB
    if initial < 1024 or maximum < initial or maximum > 131072:
        return False, "O tamanho inicial precisa ser de pelo menos 1024 MB e o máximo não pode ser menor que ele."
    if maximum > free_mb * 0.8:
        return False, f"O disco {drive} só tem {free_mb} MB livres. Escolha um máximo menor."
    name = f"{drive}\\pagefile.sys"
    script = ("try{"
              "$cs=Get-WmiObject Win32_ComputerSystem -EnableAllPrivileges;"
              "if($cs.AutomaticManagedPagefile){$cs.AutomaticManagedPagefile=$false;[void]$cs.Put()};"
              f"$pf=Get-WmiObject Win32_PageFileSetting|Where-Object{{$_.Name -eq '{name}'}};"
              f"if($pf){{$pf.InitialSize={initial};$pf.MaximumSize={maximum};[void]$pf.Put()}}"
              f"else{{[void](Set-WmiInstance -Class Win32_PageFileSetting -Arguments @{{Name='{name}';InitialSize={initial};MaximumSize={maximum}}} -EnableAllPrivileges)}};"
              "'OK'}catch{'FAIL|'+$_.Exception.Message}")
    out = bk.ps(script, timeout=60).strip()
    if out.endswith("OK"):
        return True, f"Arquivo de paginação: {initial} MB a {maximum} MB. Reinicie o PC para valer."
    return False, out.split("|", 1)[-1][:200] or "Falhou."


def pagefile_auto():
    """Volta ao padrão do Windows (ele mesmo escolhe o tamanho)."""
    script = ("try{$cs=Get-WmiObject Win32_ComputerSystem -EnableAllPrivileges;$cs.AutomaticManagedPagefile=$true;[void]$cs.Put();"
              "Get-WmiObject Win32_PageFileSetting -EA SilentlyContinue|ForEach-Object{$_.Delete()};'OK'}catch{'FAIL|'+$_.Exception.Message}")
    out = bk.ps(script, timeout=60).strip()
    if out.endswith("OK"):
        return True, "O Windows volta a escolher o tamanho sozinho. Reinicie o PC para valer."
    return False, out.split("|", 1)[-1][:200] or "Falhou."


# --------------------------------------------------------------- agrupar serviços (SvcHost)
SVC_KEY, SVC_VALUE = r"SYSTEM\CurrentControlSet\Control", "SvcHostSplitThresholdInKB"
SVC_DEFAULT = 0x380000
SVC_TABLE = [(4, 0x400000), (6, 0x600000), (8, 0x800000), (12, 0xC00000), (16, 0x1000000),
             (24, 0x1800000), (32, 0x2000000), (64, 0x4000000)]


def svchost_tier(ram_kb):
    """Maior faixa da tabela que cabe na RAM (o Windows mostra um pouco menos que o instalado, por isso 10% de folga)."""
    gb = ram_kb / 1048576
    best = None
    for tgb, val in SVC_TABLE:
        if gb >= tgb * 0.9:
            best = (tgb, val)
    return best


def svchost_current():
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, SVC_KEY) as k:
            return winreg.QueryValueEx(k, SVC_VALUE)[0]
    except OSError:
        return None


def svchost_info():
    ram_kb = psutil.virtual_memory().total // 1024
    tier = svchost_tier(ram_kb)
    cur = svchost_current()
    return {"ram_kb": ram_kb, "ram_gb": round(ram_kb / 1048576, 1), "current": cur, "current_hex": None if cur is None else f"0x{cur:X}",
            "tier_gb": tier[0] if tier else None, "value": tier[1] if tier else None, "hex": f"0x{tier[1]:X}" if tier else None,
            "default_hex": f"0x{SVC_DEFAULT:X}", "table": [{"gb": g, "hex": f"0x{v:X}"} for g, v in SVC_TABLE]}


def svchost_set(value):
    if value not in [v for _, v in SVC_TABLE] + [SVC_DEFAULT]:
        return False, "Valor fora da tabela."
    try:
        with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, SVC_KEY, 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, SVC_VALUE, 0, winreg.REG_DWORD, value)
    except OSError as e:
        return False, f"O Windows não deixou gravar no registro ({e.strerror or e})."
    return True, f"Gravado {SVC_VALUE} = 0x{value:X}. Reinicie o PC para valer."
