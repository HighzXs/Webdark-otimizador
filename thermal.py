"""Vigia de temperatura: lê os sensores, avisa e baixa o clock antes de estourar."""
import base64
import collections
import json
import os
import subprocess
import threading
import time
from dataclasses import asdict, dataclass, field, fields

import backend as bk
import cpu

# Lê, a cada 2s: zona térmica do Windows (sem admin), GPU NVIDIA (nvidia-smi) e clock/uso da CPU.
SENSOR_SCRIPT = r'''
$ErrorActionPreference = 'SilentlyContinue'
while ($true) {
  $z = Get-CimInstance Win32_PerfFormattedData_Counters_ThermalZoneInformation
  $t = ($z | Measure-Object -Property HighPrecisionTemperature -Maximum).Maximum
  $p = Get-CimInstance Win32_PerfFormattedData_Counters_ProcessorInformation -Filter "Name='_Total'"
  $g = ''
  $o = & nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits 2>$null
  if ($o) { $g = ($o | Select-Object -First 1).ToString().Trim() }
  "T|$t|$g|$($p.ProcessorFrequency)|$($p.PercentProcessorPerformance)|$($p.PercentProcessorUtility)"
  Start-Sleep -Seconds 2
}
'''

OK, WARN, HOT, CRIT, NOSENSOR = "ok", "warn", "hot", "crit", "nosensor"
RANK = {NOSENSOR: -1, OK: 0, WARN: 1, HOT: 2, CRIT: 3}


def app_dir():
    base = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "FaxinaVarzea")
    os.makedirs(base, exist_ok=True)
    return base


# ------------------------------------------------------------------ configuração
# Curva: lista de [temperatura °C, clock máximo %]. Entre dois pontos, o programa calcula o meio do caminho.
# Abaixo do primeiro ponto vale o % do primeiro; acima do último, o % do último.
DEFAULT_CURVE = [[84, 100], [88, 90], [92, 70], [96, 50], [100, 40]]

# (quantos °C abaixo do limite do chip, % de clock) por perfil, e quantos °C abaixo do limite começa o aviso
CURVE_MODES = {
    "gamer": ([(16, 100), (12, 90), (8, 70), (4, 50), (0, 40)], 20),
    "careful": ([(22, 100), (17, 90), (12, 75), (7, 60), (2, 45)], 26),
    "very": ([(30, 100), (24, 85), (18, 70), (12, 55), (6, 45)], 34),
}


def guess_tjmax(cpu_name):
    """Temperatura máxima típica do chip, pelo fabricante. Na dúvida, o valor mais conservador."""
    n = (cpu_name or "").lower()
    if "intel" in n:
        return 100
    return 95  # AMD Ryzen (Tctl) e desconhecidos


def make_curve(tj, mode):
    offsets, warn_off = CURVE_MODES[mode]
    return [[tj - o, p] for o, p in offsets], tj - warn_off


def curve_target(curve, t):
    """Clock máximo (%) que a curva manda para a temperatura `t`."""
    pts = sorted(curve)
    if t <= pts[0][0]:
        return pts[0][1]
    if t >= pts[-1][0]:
        return pts[-1][1]
    for (t0, p0), (t1, p1) in zip(pts, pts[1:]):
        if t0 <= t <= t1:
            return round(p0 + (p1 - p0) * (t - t0) / (t1 - t0))
    return pts[-1][1]


def valid_curve(curve):
    try:
        pts = sorted([int(t), int(p)] for t, p in curve)
    except (TypeError, ValueError):
        return None
    if not 2 <= len(pts) <= 8:
        return None
    if any(not (40 <= t <= 110 and 10 <= p <= 100) for t, p in pts):
        return None
    if len({t for t, _ in pts}) != len(pts):
        return None
    if any(a[1] < b[1] for a, b in zip(pts, pts[1:])):   # o clock não pode subir quando esquenta
        return None
    return pts


@dataclass
class Config:
    enabled: bool = False          # tudo desligado até o usuário ativar na aba Segurança
    warn: int = 80                 # °C: amarelo + apito
    curve: list = field(default_factory=lambda: [list(p) for p in DEFAULT_CURVE])
    tj: int = 100                  # limite estimado do chip deste PC
    cpu_name: str = ""
    curve_set: bool = False        # True depois que o usuário mexeu: aí não sugerimos mais sozinho
    overlay: str = "never"         # always | hot | never
    sound: bool = False

    @property
    def limit(self):
        """Temperatura em que o clock começa a ser limitado (último ponto com 100%)."""
        pts = sorted(self.curve)
        full = [p for p in pts if p[1] >= 100]
        return full[-1][0] if full else pts[0][0]

    @property
    def crit(self):
        """Temperatura de perigo: primeiro ponto com 50% ou menos (ou o fim da curva)."""
        pts = sorted(self.curve)
        low = [p for p in pts if p[1] <= 50]
        return low[0][0] if low else pts[-1][0]


def load_config():
    cfg = Config()
    names = {f.name for f in fields(Config)}
    try:
        with open(os.path.join(app_dir(), "settings.json"), encoding="utf-8") as f:
            data = json.load(f).get("thermal", {})
        for k, v in data.items():
            if k in names and k != "curve":
                setattr(cfg, k, v)
        curve = valid_curve(data.get("curve", []))
        if curve:
            cfg.curve = curve
    except (OSError, ValueError):
        pass
    return cfg


def save_config(cfg):
    path = os.path.join(app_dir(), "settings.json")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = {}
    data["thermal"] = asdict(cfg)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except OSError:
        pass


# ----------------------------------------------------------------- registro de eventos
def log_event(kind, text):
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')}|{kind}|{text}\n"
    try:
        with open(os.path.join(app_dir(), "thermal.log"), "a", encoding="utf-8") as f:
            f.write(line)
    except OSError:
        pass


def recent_events(n=40):
    try:
        with open(os.path.join(app_dir(), "thermal.log"), encoding="utf-8") as f:
            lines = f.readlines()[-n:]
    except OSError:
        return []
    out = []
    for ln in lines:
        parts = ln.rstrip("\n").split("|", 2)
        if len(parts) == 3:
            out.append(tuple(parts))
    return out


def hot_events_last_days(days=7):
    cutoff = time.time() - days * 86400
    n = 0
    try:
        with open(os.path.join(app_dir(), "thermal.log"), encoding="utf-8") as f:
            for ln in f:
                parts = ln.rstrip("\n").split("|", 2)
                if len(parts) == 3 and parts[1] in (HOT, CRIT):
                    if time.mktime(time.strptime(parts[0], "%Y-%m-%d %H:%M:%S")) >= cutoff:
                        n += 1
    except (OSError, ValueError):
        pass
    return n


# -------------------------------------------------------------------------- sensor
def parse_line(line):
    p = line.strip().split("|")
    if len(p) < 6 or p[0] != "T":
        return None

    def num(x):
        try:
            return float(x.replace(",", "."))
        except ValueError:
            return None

    t = num(p[1])
    cpu_c = round(t / 10 - 273.15, 1) if t and 2931 < t < 3981 else None  # décimos de Kelvin -> °C
    freq, perf = num(p[3]), num(p[4])
    return {
        "cpu": cpu_c,
        "gpu": num(p[2]),
        "mhz": freq * perf / 100 if freq is not None and perf is not None else None,
        "util": num(p[5]),
    }


class Sensor:
    """Um PowerShell que fica rodando e manda uma linha a cada 2s (bem mais leve que abrir um por leitura)."""

    def __init__(self):
        self.proc = None
        self.last = None
        self.stamp = 0.0

    def start(self):
        if self.proc and self.proc.poll() is None:
            return
        enc = base64.b64encode(SENSOR_SCRIPT.encode("utf-16-le")).decode()
        self.proc = subprocess.Popen(
            ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-EncodedCommand", enc],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
            creationflags=bk.CREATE_NO_WINDOW)
        threading.Thread(target=self._read, args=(self.proc,), daemon=True).start()

    def _read(self, proc):
        for raw in proc.stdout:
            d = parse_line(raw.decode("utf-8", errors="replace"))
            if d:
                self.last, self.stamp = d, time.time()

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()

    def get(self):
        """Última leitura, ou None se o sensor parou de responder (>8s)."""
        return self.last if self.last and time.time() - self.stamp < 8 else None


# --------------------------------------------------------------------------- vigia
class Guard:
    def __init__(self, sensor, cfg):
        self.sensor, self.cfg = sensor, cfg
        self.state = NOSENSOR       # pior entre CPU e GPU
        self.cpu_state = NOSENSOR
        self.reading = None
        self.throttled = False
        self.cur_max = None
        self.orig = None
        self.last_change = 0.0
        self.alert = None           # nível novo (para a interface apitar uma vez)
        self._recent = collections.deque(maxlen=3)     # últimas leituras de CPU (para a mediana)
        self.history = collections.deque(maxlen=150)   # (hora, cpu, gpu, clock máx %)
        self.events = collections.deque(maxlen=60)     # (hora, tipo, texto)
        self._state_file = os.path.join(app_dir(), "guard_state.json")

    # --- eventos
    def _event(self, kind, text):
        self.events.append((time.strftime("%H:%M:%S"), kind, text))
        log_event(kind, text)

    # --- níveis
    def level(self, t):
        if t is None:
            return NOSENSOR
        c = self.cfg
        return CRIT if t >= c.crit else HOT if t >= c.limit else WARN if t >= c.warn else OK

    def target(self, t):
        """Clock máximo (%) que a curva manda para a temperatura `t`."""
        return curve_target(self.cfg.curve, t)

    # --- clock
    def _snap(self):
        return {"min": list(cpu.read("min") or (5, 5)), "max": list(cpu.read("max") or (100, 100))}

    def _set(self, pct):
        o = self.orig
        cpu.write_pair("min", min(o["min"][0], pct), min(o["min"][1], pct))
        cpu.write_pair("max", pct, pct)
        cpu.activate()
        self.cur_max = pct
        self.last_change = time.time()

    def restore(self):
        """Devolve os valores originais do plano de energia."""
        if self.orig:
            o = self.orig
            cpu.write_pair("min", *o["min"])
            cpu.write_pair("max", *o["max"])
            cpu.activate()
        self.throttled, self.cur_max, self.orig = False, None, None
        try:
            os.remove(self._state_file)
        except OSError:
            pass

    def recover(self):
        """Se o programa fechou à força enquanto limitava o clock, devolve o original agora."""
        try:
            with open(self._state_file, encoding="utf-8") as f:
                self.orig = json.load(f)
        except (OSError, ValueError):
            return False
        self.restore()
        self._event("info", "Restaurei o clock original (o programa tinha fechado enquanto limitava).")
        return True

    def _follow(self, t, now):
        """Segue a curva: baixa rápido, sobe devagar e só depois de esfriar uns graus (evita sobe-e-desce)."""
        level = self.level(t)
        want = self.target(t)
        if not self.throttled:
            if want >= 100:
                return
            snap = self._snap()
            if want >= snap["max"][0]:
                return                      # o plano de energia já limita mais do que a curva pede
            self.orig, self.cur_max, self.throttled = snap, snap["max"][0], True
            try:
                with open(self._state_file, "w", encoding="utf-8") as f:
                    json.dump(snap, f)
            except OSError:
                pass
        top = self.orig["max"][0]
        want = min(want, top)
        if want < self.cur_max:
            if now - self.last_change >= (2 if level == CRIT else 3):
                new = max(want, self.cur_max - (25 if level == CRIT else 15))
                self._set(new)
                self._event("clock", f"CPU a {t:.0f}°C: clock máximo em {new}%")
        else:
            up = min(self.target(t + 3), top)   # só sobe se a CPU esfriou 3°C
            if up > self.cur_max and now - self.last_change >= 8:
                new = min(up, self.cur_max + 5)
                if new >= top:
                    self.restore()
                    self._event(OK, f"CPU esfriou ({t:.0f}°C): clock de volta ao normal")
                else:
                    self._set(new)

    # --- ciclo principal (chamar de uma thread, a cada ~2s)
    def tick(self):
        try:
            self._tick()
        except Exception as e:
            self._event("info", f"erro no vigia: {e}")

    def _tick(self):
        d = self.sensor.get()
        self.reading = d
        if not d:
            self.state = self.cpu_state = NOSENSOR
            return
        raw_t, g = d["cpu"], d["gpu"]
        self.history.append((time.time(), raw_t, g, self.cur_max or 100))
        # o sensor do Windows dá picos de 1 leitura: decide pela mediana das últimas 3 (~6s)
        if raw_t is not None:
            self._recent.append(raw_t)
        t = sorted(self._recent)[len(self._recent) // 2] if self._recent else None
        cpu_lvl, gpu_lvl = self.level(t), self.level(g)
        worst = max((cpu_lvl, gpu_lvl), key=lambda s: RANK[s])
        prev = self.state
        self.state, self.cpu_state = worst, cpu_lvl
        if RANK[worst] > RANK.get(prev, 0) and RANK[worst] >= RANK[WARN]:
            self.alert = worst
            who = "GPU" if RANK[gpu_lvl] > RANK[cpu_lvl] else "CPU"
            val = g if who == "GPU" else t
            self._event(worst, f"{who} chegou a {val:.0f}°C ({'aviso' if worst == WARN else 'quente'})")
        if not self.cfg.enabled:
            if self.throttled:
                self.restore()
            return
        if t is not None:
            self._follow(t, time.time())
