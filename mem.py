"""Memória RAM: uso agora, prioridade e congelamento por programa, arquivo de paginação e o desfazer do SvcHost antigo."""
import ctypes
import json
import os
import threading
import time
import winreg
from ctypes import wintypes

import psutil

import backend as bk

MB = 1024 * 1024
GB = 1024 * MB

_k32 = ctypes.WinDLL("kernel32", use_last_error=True)
_u32 = ctypes.WinDLL("user32")

_k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
_k32.OpenProcess.restype = wintypes.HANDLE
_k32.CloseHandle.argtypes = [wintypes.HANDLE]
_k32.SetProcessInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
_u32.GetForegroundWindow.restype = wintypes.HWND
_u32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]


# ---------------------------------------------------------------------- RAM agora
def ram_info():
    vm = psutil.virtual_memory()
    return {"total": vm.total, "avail": vm.available, "percent": vm.percent}


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
    return {"ram_gb": _ram_gb(), "drive": drive, "free_mb": int(free_mb), "auto": bool(d.get("auto", True)),
            "set": as_list(d.get("set")), "use": as_list(d.get("use"))}


def pagefile_auto():
    """Volta ao padrão do Windows (ele mesmo escolhe o tamanho)."""
    script = ("try{$cs=Get-WmiObject Win32_ComputerSystem -EnableAllPrivileges;$cs.AutomaticManagedPagefile=$true;[void]$cs.Put();"
              "Get-WmiObject Win32_PageFileSetting -EA SilentlyContinue|ForEach-Object{$_.Delete()};'OK'}catch{'FAIL|'+$_.Exception.Message}")
    out = bk.ps(script, timeout=60).strip()
    if out.endswith("OK"):
        return True, "O Windows volta a escolher o tamanho sozinho. Reinicie o PC para valer."
    return False, out.split("|", 1)[-1][:200] or "Falhou."


# ------------------------------------------------- SvcHost: só o desfazer (o ajuste saiu do app)
# Versões antigas subiam o SvcHostSplitThresholdInKB. Não deixava o PC mais rápido (só juntava serviços em menos
# processos), então saiu; quem aplicou pode voltar ao padrão do Windows.
SVC_KEY, SVC_VALUE = r"SYSTEM\CurrentControlSet\Control", "SvcHostSplitThresholdInKB"
SVC_DEFAULT = 0x380000


def svchost_current():
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, SVC_KEY) as k:
            return winreg.QueryValueEx(k, SVC_VALUE)[0]
    except OSError:
        return None


def svchost_changed():
    cur = svchost_current()
    return cur is not None and cur != SVC_DEFAULT


def svchost_reset():
    try:
        with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, SVC_KEY, 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, SVC_VALUE, 0, winreg.REG_DWORD, SVC_DEFAULT)
    except OSError as e:
        return False, f"O Windows não deixou gravar no registro ({e.strerror or e})."
    return True, "Agrupamento de serviços voltou ao padrão do Windows. Reinicie o PC para valer."
