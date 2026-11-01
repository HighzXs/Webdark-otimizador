"""Ponte entre a interface HTML e o resto do programa.

O JavaScript chama os métodos públicos desta classe (window.pywebview.api.<nome>). Tarefas longas rodam numa
thread e avisam o JavaScript com _emit(evento, dados), que chega em window.__emit(evento, dados).
Atributos e métodos com "_" no começo não ficam visíveis para o JavaScript.
"""
import json
import os
import re
import sys
import threading
import time
import webbrowser
import winsound
from dataclasses import asdict

import psutil
import webview

import backend as bk
import cpu
import health
import overlay
import risk
import settings
import startup
import system
import thermal
import tweaks
import updater
from tray import Tray
from version import REPO, VERSION

TITLE = "WebDark Otimizador"

OVERLAY_HTML = """<!doctype html><meta charset="utf-8"><style>
html,body{margin:0;height:100%;overflow:hidden;user-select:none;font:700 15px 'Segoe UI',sans-serif;color:#fff}
#b{height:100%;display:flex;align-items:center;justify-content:center;padding:0 14px;background:#16a34a;white-space:nowrap}
</style><div id="b"></div><script>function setBox(t,c){var b=document.getElementById('b');b.textContent=t;b.style.background=c}</script>"""


class _Direct:
    """Faz de conta de 'janela principal' para a bandeja: executa direto, sem fila."""

    @staticmethod
    def post(fn):
        fn()


def icon_path():
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "icon.png")


class Api:
    def __init__(self):
        self._window = None
        self._prefs = settings.load()
        self._cancel = threading.Event()
        self._found = {}          # caminho -> nível de risco do último escaneamento (só esses podem ir pra lixeira)
        self._appx, self._progs, self._starts, self._procs = {}, {}, {}, {}   # o que a última busca achou, por id
        self._cleaners, self._dups, self._tweaks = {}, {}, {}
        self._disk_kind, self._restore_done = "", False
        # vigia de temperatura (desligado até o usuário ativar na aba Segurança)
        self._cfg = thermal.load_config()
        self._sensor = thermal.Sensor()
        self._guard = thermal.Guard(self._sensor, self._cfg)
        self._guard.recover()
        self._sec_open, self._quitting, self._blink = False, False, False
        self._overlay, self._ov_visible, self._ov_last = None, False, None
        self._tray, self._bg_stop, self._update = None, threading.Event(), None
        threading.Thread(target=self._guard_loop, daemon=True).start()

    # ------------------------------------------------------------------ infra
    def _emit(self, event, payload=None):
        if self._window is None:
            return
        try:
            self._window.evaluate_js(f"window.__emit({json.dumps(event)},{json.dumps(payload)})")
        except Exception:
            pass

    def _throttled(self, event, gap=0.25):
        """Devolve uma função que só avisa a tela a cada `gap` segundos (senão a janela engasga com milhares de avisos)."""
        last = [0.0]

        def emit(payload):
            now = time.monotonic()
            if now - last[0] >= gap:
                last[0] = now
                self._emit(event, payload)

        return emit

    def _thread(self, fn):
        def run():
            try:
                fn()
            except Exception as e:
                self._emit("error", str(e))

        threading.Thread(target=run, daemon=True).start()

    # ------------------------------------------------------------------ geral
    def info(self):
        return {"name": TITLE, "version": VERSION, "admin": bk.is_admin(), "drives": bk.fixed_drives(),
                "theme": self._prefs.get("theme", {}), "history_total": bk.history_total()}

    def set_theme(self, theme):
        self._prefs["theme"] = theme
        settings.save(self._prefs)
        return True

    def relaunch_admin(self):
        if bk.relaunch_as_admin() and self._window is not None:
            self._window.destroy()

    def reveal(self, path):
        bk.open_in_explorer(path)

    # ----------------------------------------------------------------- início
    def summary(self):
        def with_ram(d):
            vm = psutil.virtual_memory()
            return {**d, "ram_pct": vm.percent, "ram_used": vm.used, "ram_total": vm.total}

        def work():
            d = bk.quick_summary(lambda part: self._emit("summary", with_ram(part)))
            self._emit("summary", {**with_ram(d), "done": True})

        self._thread(work)

    def quick_clean(self):
        def work():
            cleaners = [c for c in bk.make_cleaners() if c.default and (bk.is_admin() or not c.admin)]
            before = bk.disk_usage("C:\\")[2]
            total = 0
            for i, c in enumerate(cleaners):
                self._emit("clean:step", {"i": i, "n": len(cleaners), "name": c.name})
                freed = bk.run_cleaner(c)
                total += freed
                self._emit("clean:freed", {"name": c.name, "freed": freed})
            bk.history_add("Faxina rápida", total)
            self._emit("clean:done", {"freed": total, "before": before, "after": bk.disk_usage("C:\\")[2]})

        self._thread(work)

    # ------------------------------------------------------------ segurança (temperatura)
    def _sec_cfg(self):
        c = self._cfg
        return {**asdict(c), "limit": c.limit, "crit": c.crit,
                "modes": {"gamer": "🎮 Gamer", "careful": "🛡 Cuidadoso", "very": "🧯 Bem cuidadoso"}}

    def sec_state(self):
        return self._sec_cfg()

    def sec_open(self, flag):
        self._sec_open = bool(flag)
        return True

    def sec_save(self, patch):
        c = self._cfg
        if "curve" in patch:
            curve = thermal.valid_curve(patch["curve"])
            if not curve:
                return {"ok": False, **self._sec_cfg()}
            c.curve[:] = curve
            c.curve_set = True
        if "enabled" in patch:
            c.enabled = bool(patch["enabled"])
        if "sound" in patch:
            c.sound = bool(patch["sound"])
        if patch.get("overlay") in ("always", "hot", "never"):
            c.overlay = patch["overlay"]
        if "warn" in patch:
            c.warn = int(patch["warn"])
        if c.warn >= c.limit:
            c.warn = c.limit - 1
        thermal.save_config(c)
        self._overlay_hide_if_needed()
        return {"ok": True, **self._sec_cfg()}

    def sec_preset(self, mode):
        if mode not in thermal.CURVE_MODES:
            return {"ok": False}
        curve, warn = thermal.make_curve(self._cfg.tj, mode)
        return self.sec_save({"curve": curve, "warn": warn})

    def sec_suggest(self):
        def work():
            name = cpu.info()[0]
            self._cfg.cpu_name, self._cfg.tj = name, thermal.guess_tjmax(name)
            curve, warn = thermal.make_curve(self._cfg.tj, "gamer")
            self._emit("sec:cfg", self.sec_save({"curve": curve, "warn": warn}))

        self._thread(work)

    def sec_import(self, text):
        try:
            data = json.loads(str(text).strip())
            curve = thermal.valid_curve(data["curve"])
            warn = int(data.get("warn", 80))
        except (ValueError, KeyError, TypeError):
            curve = None
        if not curve:
            return {"ok": False}
        return self.sec_save({"curve": curve, "warn": min(warn, curve[0][0] - 1)})

    def sec_events(self):
        return {"events": [list(e) for e in thermal.recent_events(30)], "hot7": thermal.hot_events_last_days(7)}

    def sec_procs(self):
        groups = sorted(system.process_groups(), key=lambda g: -g.cpu)[:5]
        return [{"name": g.name, "cpu": round(g.cpu, 1)} for g in groups]

    def _sec_payload(self):
        g = self._guard
        r = g.reading or {}
        return {"cpu": r.get("cpu"), "gpu": r.get("gpu"), "mhz": r.get("mhz"), "util": r.get("util"), "state": g.state,
                "throttled": g.throttled, "cur_max": g.cur_max, "enabled": self._cfg.enabled,
                "history": [[h[1], h[2], h[3]] for h in g.history]}

    # --- vigia (roda sozinho; só liga o sensor se a proteção estiver ativada ou a aba aberta)
    def _guard_loop(self):
        while not self._quitting:
            time.sleep(2)
            try:
                self._guard_step()
            except Exception as e:
                print("vigia:", e)

    def _guard_step(self):
        cfg, g = self._cfg, self._guard
        if not (cfg.enabled or self._sec_open):
            if g.throttled:
                g.restore()
            self._sensor.stop()
            g.reading, g.state = None, thermal.NOSENSOR
            self._overlay_hide()
            return
        self._sensor.start()
        g.tick()
        if cfg.enabled:
            self._guard_ui()
        else:
            g.alert = None
            self._overlay_hide()
        if self._sec_open:
            self._emit("sec:tick", self._sec_payload())

    def _guard_ui(self):
        g, cfg = self._guard, self._cfg
        if g.alert:
            if cfg.sound:
                try:
                    winsound.MessageBeep(winsound.MB_ICONHAND if g.alert in (thermal.HOT, thermal.CRIT) else winsound.MB_ICONEXCLAMATION)
                except Exception:
                    pass
            g.alert = None
        hot = thermal.RANK[g.state] >= thermal.RANK[thermal.WARN] or g.throttled
        if cfg.overlay == "always" or (cfg.overlay == "hot" and hot):
            level = thermal.WARN if (g.state == thermal.OK and g.throttled) else g.state
            color = overlay.COLORS.get(level, overlay.COLORS[thermal.OK])
            if level == thermal.CRIT:
                self._blink = not self._blink
                color = overlay.BLINK if self._blink else color
            self._overlay_update(overlay.describe(g.reading, g.state, g.throttled, g.cur_max), color)
        else:
            self._overlay_hide()

    def _overlay_hide_if_needed(self):
        if not self._cfg.enabled or self._cfg.overlay == "never":
            self._overlay_hide()

    def make_overlay(self):
        """Cria a janelinha da temperatura (escondida, sempre por cima)."""
        try:
            scr = webview.screens[0]
            kw = dict(x=scr.width - 396, y=16)
        except Exception:
            kw = {}
        try:
            self._overlay = webview.create_window("WebDark temperatura", html=OVERLAY_HTML, width=380, height=48, frameless=True,
                                                  on_top=True, hidden=True, easy_drag=True, resizable=False, focus=False,
                                                  background_color="#111111", **kw)
        except TypeError:
            self._overlay = webview.create_window("WebDark temperatura", html=OVERLAY_HTML, width=380, height=48, frameless=True,
                                                  on_top=True, hidden=True, easy_drag=True, resizable=False, **kw)

    def _overlay_update(self, text, color):
        ov = self._overlay
        if ov is None:
            return
        if (text, color) != self._ov_last:
            self._ov_last = (text, color)
            try:
                ov.evaluate_js(f"setBox({json.dumps(text)},{json.dumps(color)})")
            except Exception:
                return
        if not self._ov_visible:
            self._ov_visible = True
            ov.show()

    def _overlay_hide(self):
        if self._overlay is not None and self._ov_visible:
            self._ov_visible = False
            try:
                self._overlay.hide()
            except Exception:
                pass

    # --------------------------------------------------- bandeja, segundo plano, janela
    def attach(self, window):
        self._window = window
        window.events.closing += self._on_closing

    def _on_closing(self):
        if self._quitting:
            return True
        if self._prefs.get("background") and self._tray is not None:
            self._window.hide()
            return False
        g = self._guard
        temp = (g.reading or {}).get("cpu")
        if g.throttled and temp is not None and temp >= self._cfg.warn:
            self._emit("confirm_close", True)       # a tela pergunta e chama quit() se o usuário confirmar
            return False
        self._shutdown()
        return True

    def _shutdown(self):
        self._quitting = True
        try:
            self._guard.restore()
            self._sensor.stop()
            if self._tray:
                self._tray.stop()
        finally:
            self._bg_stop.set()
            if self._overlay is not None:          # a janelinha escondida manteria o programa vivo
                try:
                    self._overlay.destroy()
                except Exception:
                    pass
                self._overlay = None

    def quit(self):
        self._shutdown()
        try:
            self._window.destroy()
        finally:
            threading.Timer(2.0, lambda: os._exit(0)).start()

    def _show_window(self):
        try:
            self._window.show()
            self._window.restore()
        except Exception:
            pass

    def bg_get(self):
        return {"on": bool(self._prefs.get("background")), "minutes": int(self._prefs.get("scan_minutes", 60))}

    def bg_set(self, on, minutes):
        self._prefs["scan_minutes"] = int(minutes)
        if on:
            if not self._tray_start():
                return {"ok": False}
        else:
            self._tray_stop()
        self._prefs["background"] = bool(on)
        settings.save(self._prefs)
        return {"ok": True}

    def _tray_start(self):
        if self._tray is not None:
            return True
        try:
            self._tray = Tray(_Direct(), icon_path(), TITLE, self._show_window, lambda: self._quiet_scan(True), self.quit)
            self._tray.start()
        except Exception:
            self._tray = None
            return False
        self._bg_stop = stop = threading.Event()

        def loop():
            if stop.wait(60):
                return
            while not stop.is_set():
                self._quiet_scan(False)
                if stop.wait(max(5, int(self._prefs.get("scan_minutes", 60))) * 60):
                    return

        threading.Thread(target=loop, daemon=True).start()
        return True

    def _tray_stop(self):
        self._bg_stop.set()
        if self._tray:
            self._tray.stop()
            self._tray = None

    def _quiet_scan(self, force):
        def work():
            d = bk.quick_summary()
            msgs = []
            if d["free"] / d["total"] < 0.15:
                msgs.append(f"Só {bk.fmt_size(d['free'])} livres no C:.")
            if d.get("junk", 0) > 2 * 1024 ** 3:
                msgs.append(f"Dá pra limpar {bk.fmt_size(d['junk'])} de lixo seguro.")
            now = time.time()
            if msgs and (force or now - self._prefs.get("last_notice", 0) > 12 * 3600):
                self._prefs["last_notice"] = now
                settings.save(self._prefs)
                if self._tray:
                    self._tray.notify(TITLE, " ".join(msgs) + " Abra o programa para limpar.")
            elif force and self._tray:
                self._tray.notify(TITLE, "Tudo certo por aqui. Nada importante para limpar.")

        self._thread(work)

    # ------------------------------------------------------------ atualização
    def update_check(self):
        def work():
            up = updater.check()
            if up:
                self._update = up
                self._emit("update:available", {"version": up.version, "size": up.size, "notes": up.notes[:600],
                                                 "can_self": updater.can_self_update()})

        self._thread(work)

    def update_apply(self):
        up = self._update
        if up is None:
            return False
        if not updater.can_self_update():
            webbrowser.open(f"https://github.com/{REPO}/releases/latest")
            return True

        def work():
            tick = self._throttled("update:progress", 0.15)
            path = updater.download(up, lambda f: tick({"frac": f}))
            updater.apply(path)
            self._emit("update:progress", {"frac": 1.0, "restart": True})
            time.sleep(0.8)
            self.quit()

        self._thread(work)
        return True

    # ------------------------------------------------------------------ saúde
    def health_scan(self):
        def work():
            try:
                self._emit("health:disks", [asdict(d) for d in health.disk_health()])
            except Exception:
                self._emit("health:disks", [])
            self._emit("health:diag", health.diagnose())

        self._thread(work)

    def updates_check(self):
        self._thread(lambda: self._emit("health:upd", system.check_updates_and_drivers()))

    def repair(self, kind):
        gens = {"sfc": health.sfc, "dism": health.dism_restore, "chkdsk": health.chkdsk_scan, "dns": health.flush_dns}
        if kind not in gens:
            return False
        if kind != "dns" and not bk.is_admin():
            return False
        self._stream(gens[kind], "health:log", "health:repair_done")
        return True

    # ------------------------------------------------------------ desempenho
    def power_info(self):
        return {"plans": [{"guid": g, "name": n, "active": a} for g, n, a in health.power_plans()], "battery": health.has_battery()}

    def power_set(self, guid):
        return health.set_power_plan(guid)

    def power_quick(self, kind):
        guid = health.ensure_plan(kind)
        return bool(guid and health.set_power_plan(guid))

    def power_timeouts(self, monitor_min, sleep_min):
        health.set_timeouts(int(monitor_min), int(sleep_min))
        return True

    def tweaks_list(self):
        self._tweaks = {t.key: t for t in tweaks.make_tweaks()}
        out = []
        for t in self._tweaks.values():
            try:
                on = bool(t.is_on())
            except Exception:
                on = False
            out.append({"key": t.key, "name": t.name, "desc": t.desc, "on": on})
        return out

    def tweak_set(self, key, on):
        t = self._tweaks.get(key)
        if t is None:
            return False
        try:
            t.apply(bool(on))
            return True
        except Exception:
            return False

    def systweaks_scan(self):
        def work():
            states = system.service_states()
            kind = system.system_disk_kind()
            self._disk_kind = kind
            items = []
            for t in system.SYS_TWEAKS:
                on = system.tweak_state(t, states)
                items.append({"key": t.key, "name": t.name, "desc": t.desc, "on": bool(on), "available": on is not None,
                              "warning": system.warning_text(t, kind)})
            self._emit("sys:state", {"items": items, "kind": kind, "trim": system.trim_status()})

        self._thread(work)

    def systweak_set(self, key, on):
        t = next((x for x in system.SYS_TWEAKS if x.key == key), None)
        if t is None or not bk.is_admin():
            return False

        def work():
            note = ""
            if on and not self._restore_done:
                ok, note = bk.create_restore_point("WebDark - antes de ajustes de sistema")
                self._restore_done = ok
            ok, msg = system.apply_tweak(t, bool(on))
            self._emit("sys:applied", {"key": key, "on": bool(on), "ok": ok, "msg": msg, "note": note})

        self._thread(work)
        return True

    def trim_enable(self):
        return bk.is_admin() and system.enable_trim()

    def optimize_disk(self):
        if not bk.is_admin():
            return False
        kind = self._disk_kind
        self._stream(lambda: system.optimize_drive(kind), "perf:log", "perf:opt_done")
        return True

    def clock_info(self):
        def work():
            name, base, threads = cpu.info()
            self._emit("perf:clock", {"name": name, "base": base, "threads": threads, "snap": cpu.snapshot_unlocked(),
                                      "presets": {k: list(v) for k, v in cpu.PRESETS.items()}, "boost_modes": cpu.BOOST_MODES})

        self._thread(work)

    def clock_apply(self, mn, mx, boost, mhz):
        self._thread(lambda: cpu.apply(int(mn), int(mx), None if boost is None else int(boost), None if mhz is None else int(mhz)))
        return True

    def clock_live(self):
        try:
            r = cpu.live()
        except Exception:
            r = None
        return {"mhz": r[0], "util": r[1]} if r else None

    # --------------------------------------------------------------- limpeza
    def clean_list(self):
        def work():
            cleaners = bk.make_cleaners()
            self._cleaners = {c.key: c for c in cleaners}
            self._emit("cl:list", [{"key": c.key, "name": c.name, "desc": c.desc, "admin": c.admin, "default": c.default,
                                    "warn": c.warn} for c in cleaners])
            for c in cleaners:
                self._emit("cl:size", {"key": c.key, "size": bk.measure(c)})
            self._emit("cl:sized", True)

        self._thread(work)

    def clean_run(self, keys):
        def work():
            admin = bk.is_admin()
            chosen = [self._cleaners[k] for k in keys if k in self._cleaners and (admin or not self._cleaners[k].admin)]
            total = 0
            for i, c in enumerate(chosen):
                self._emit("cl:step", {"i": i, "n": len(chosen), "name": c.name})
                freed = bk.run_cleaner(c)
                total += freed
                self._emit("cl:size", {"key": c.key, "size": c.size})
                self._emit("cl:log", f"{c.name}: {bk.fmt_size(freed)}")
            bk.history_add("Limpeza", total)
            self._emit("cl:done", {"freed": total})

        self._thread(work)

    def extras_info(self):
        return {"hiber": bk.hiberfil_size(), "admin": bk.is_admin()}

    def hibernate_off(self):
        return bk.is_admin() and bk.hibernate_off()

    def open_cleanmgr(self):
        bk.open_windows_cleanmgr()

    def _stream(self, gen_fn, event, end_event):
        """Joga a saída de um comando longo na tela: progresso de 10 em 10% e um aviso a cada 30s."""
        stop = threading.Event()
        t0 = time.monotonic()

        def beat():
            while not stop.wait(30):
                s = int(time.monotonic() - t0)
                self._emit(event, f"⏳ ainda trabalhando… {s // 60}min{s % 60:02d}s")

        def work():
            threading.Thread(target=beat, daemon=True).start()
            last = -1
            try:
                for line in gen_fn():
                    m = re.search(r"(\d+(?:[.,]\d+)?)\s*%", line)
                    if m:
                        bucket = int(float(m.group(1).replace(",", "."))) // 10
                        if bucket == last:
                            continue
                        last = bucket
                    self._emit(event, line)
            except Exception as e:
                self._emit(event, f"✖ erro: {e}")
            finally:
                stop.set()
                self._emit(end_event, True)

        self._thread(work)

    def dism_cleanup(self):
        if not bk.is_admin():
            return False
        self._stream(health.dism_cleanup, "cl:log", "cl:dism_done")
        return True

    def restore_point(self):
        if not bk.is_admin():
            return {"ok": False, "msg": "Precisa de administrador."}
        ok, msg = bk.create_restore_point("WebDark")
        return {"ok": ok, "msg": msg}

    # --------------------------------------------------------- pastas / duplicados / downloads
    def dirs_scan(self, path):
        self._cancel.set()
        self._cancel = ev = threading.Event()

        def work():
            items = bk.scan_children(path, ev)
            if not ev.is_set():
                self._emit("dirs:list", {"path": path, "items": [{"name": n, "path": p, "size": s, "dir": d}
                                                                  for n, p, s, d in items[:300]]})

        self._thread(work)

    def dups_scan(self, where, min_mb):
        self._cancel.set()
        self._cancel = ev = threading.Event()

        def work():
            roots = bk.user_folders() if where == "mine" else [where]
            tick = self._throttled("dups:progress")
            groups = bk.find_duplicates(roots, int(min_mb) * 1024 * 1024, ev, lambda t: tick(t))
            if ev.is_set():
                return
            out, self._dups = [], {}
            for i, g in enumerate(groups[:200]):
                files = sorted(g["files"], key=lambda f: ("\\downloads\\" in f[0].lower(), f[1]))
                self._dups[i] = [f[0] for f in files]
                out.append({"id": i, "size": g["size"], "files": [{"path": p, "date": time.strftime("%d/%m/%Y", time.localtime(mt))}
                                                                   for p, mt in files]})
            self._emit("dups:done", {"groups": out, "total": len(groups)})

        self._thread(work)

    def dups_trash(self, paths):
        """Manda cópias para a lixeira, mas nunca todas as cópias de um mesmo grupo."""
        asked = set(paths)
        for gid, files in self._dups.items():
            if files and all(f in asked for f in files):
                return {"done": [], "failed": [{"path": files[0], "err": "Isso apagaria todas as cópias de um arquivo."}], "freed": 0}
        known = {f for files in self._dups.values() for f in files}
        done, failed, freed = [], [], 0
        for p in paths:
            if p not in known:
                failed.append({"path": p, "err": "Esse arquivo não veio da busca."})
                continue
            try:
                size = os.path.getsize(p)
                bk.send_to_trash(p)
                done.append(p)
                freed += size
            except Exception as e:
                failed.append({"path": p, "err": str(e)})
        bk.history_add("Duplicados", freed)
        return {"done": done, "failed": failed, "freed": freed}

    def dl_scan(self, days):
        self._cancel.set()
        self._cancel = ev = threading.Event()

        def work():
            base = system.downloads_dir()
            rows = []
            for i, (size, p) in enumerate(system.old_downloads(int(days), ev, top=200)):
                r = risk.assess(p)
                self._found[p] = r.level
                rows.append({"id": i, "path": p, "rel": os.path.relpath(p, base), "size": size, "level": r.level,
                             "label": risk.LABEL[r.level], "reason": r.text})
            if not ev.is_set():
                self._emit("dl:done", rows)

        self._thread(work)

    # --------------------------------------------------------------- bloatware
    def bloat_scan(self):
        def work():
            items = bk.list_appx()
            self._appx = {str(i): it for i, it in enumerate(items)}
            self._emit("bloat:list", [{"id": str(i), "name": it.name, "friendly": it.friendly, "desc": it.desc, "level": it.level}
                                      for i, it in enumerate(items)])

        self._thread(work)

    def bloat_remove(self, ids):
        chosen = [self._appx[i] for i in ids if i in self._appx]

        def work():
            admin = bk.is_admin()
            if admin:
                self._emit("bloat:log", "🛟 Criando ponto de restauração antes…")
                self._emit("bloat:log", "   " + bk.create_restore_point("WebDark - antes de remover apps")[1])
            else:
                self._emit("bloat:log", "⚠ Sem admin: sem ponto de restauração (os apps voltam pela Store).")
            ok = 0
            for line in bk.remove_appx(chosen, admin):
                if line.startswith("OK|"):
                    ok += 1
                    self._emit("bloat:log", "✔ removido: " + line[3:])
                elif line.startswith("FAIL|"):
                    self._emit("bloat:log", "✖ falhou: " + line[5:])
            self._emit("bloat:done", ok)

        self._thread(work)

    # ------------------------------------------------------------- programas
    def progs_scan(self):
        def work():
            progs = bk.list_programs()
            self._progs = {str(i): p for i, p in enumerate(progs)}
            self._emit("progs:list", [{"id": str(i), "name": p.name, "publisher": p.publisher, "size": p.size, "suspect": p.suspect}
                                      for i, p in enumerate(progs)])

        self._thread(work)

    def prog_uninstall(self, pid):
        p = self._progs.get(pid)
        if p is None:
            return False
        bk.run_uninstaller(p.uninstall)
        return True

    # ----------------------------------------------------------- inicialização
    def start_scan(self):
        def work():
            items = startup.list_startup()
            self._starts = {str(i): it for i, it in enumerate(items)}
            self._emit("start:list", [{"id": str(i), "kind": it.kind, "name": it.name, "command": it.command, "where": it.where,
                                       "enabled": it.enabled, "advice": it.advice, "note": it.note, "admin": it.admin}
                                      for i, it in enumerate(items)])

        self._thread(work)

    def start_set(self, sid, on):
        it = self._starts.get(sid)
        if it is None:
            return {"ok": False, "msg": "Item não encontrado."}
        if it.admin and not bk.is_admin():
            return {"ok": False, "msg": "Esse item precisa de administrador."}
        try:
            ok, msg = startup.set_enabled(it, bool(on))
        except Exception as e:
            ok, msg = False, str(e)
        if ok:
            it.enabled = bool(on)
        return {"ok": ok, "msg": msg}

    def start_disable_recommended(self):
        def work():
            targets = [(k, it) for k, it in self._starts.items()
                       if it.advice == "off" and it.enabled and (bk.is_admin() or not it.admin)]
            failed = []
            for k, it in targets:
                try:
                    ok, _ = startup.set_enabled(it, False)
                except Exception:
                    ok = False
                if ok:
                    it.enabled = False
                else:
                    failed.append(it.name)
            self._emit("start:bulk", {"done": len(targets) - len(failed), "failed": failed})

        self._thread(work)

    # -------------------------------------------------------------- processos
    def proc_list(self):
        groups = system.process_groups()
        self._procs = {g.name.lower(): g for g in groups}
        vm = psutil.virtual_memory()
        return {"rows": [{"key": g.name.lower(), "name": g.name, "count": g.count, "ram": g.ram, "cpu": round(g.cpu, 1),
                          "protected": g.protected} for g in groups],
                "ram_pct": vm.percent, "ram_used": vm.used, "ram_total": vm.total, "cpu_total": psutil.cpu_percent(None)}

    def proc_close(self, key):
        g = self._procs.get(key)
        if g is None:
            return {"closed": 0, "errors": ["Programa não encontrado."]}
        closed, errors = system.close_group(g)
        return {"closed": closed, "errors": errors}

    # --------------------------------------------------------- arquivos grandes
    def scan_files(self, root, min_mb):
        self._cancel.set()
        self._cancel = ev = threading.Event()

        def work():
            tick = self._throttled("scan:progress")
            res = bk.find_big_files(root, int(min_mb) * 1024 * 1024, ev, lambda n, d: tick({"n": n}))
            if ev.is_set():
                return
            self._emit("scan:progress", {"n": -1})                 # -1 = avaliando o risco
            rows, found = [], {}
            for i, (size, p) in enumerate(res):
                r = risk.assess(p)
                found[p] = r.level
                rows.append({"id": i, "path": p, "size": size, "level": r.level, "label": risk.LABEL[r.level],
                             "reason": r.text, "in_use": r.in_use})
            self._found.update(found)
            self._emit("scan:done", rows)

        self._thread(work)

    def cancel_scan(self):
        self._cancel.set()

    def trash(self, paths):
        """Manda para a lixeira. Só aceita caminhos da última busca e nunca os marcados NÃO APAGUE."""
        done, failed, freed = [], [], 0
        for p in paths:
            if p not in self._found:
                failed.append({"path": p, "err": "Esse arquivo não veio da busca."})
                continue
            if risk.assess(p).level == risk.DANGER:
                failed.append({"path": p, "err": "Arquivo protegido (NÃO APAGUE)."})
                continue
            try:
                size = os.path.getsize(p)
                bk.send_to_trash(p)
                done.append(p)
                freed += size
            except Exception as e:
                failed.append({"path": p, "err": str(e)})
        bk.history_add("Arquivos grandes", freed)
        return {"done": done, "failed": failed, "freed": freed}
