"""Desfazer dos serviços que versões antigas do WebDark desligavam.

Desligar serviço parado em Manual não ganha desempenho e pode quebrar impressora, VPN, Xbox etc., então a função saiu.
O que sobrou: achar os serviços que o app desligou (ficaram guardados em services.json) e voltar ao que eram."""
import json
import os
import subprocess
import winreg

import backend as bk

SVC_ROOT = r"SYSTEM\CurrentControlSet\Services"

# nome do serviço -> título que aparecia no app
TITLES = {
    "Spooler": "Fila de impressão",
    "Fax": "Fax",
    "RemoteRegistry": "Registro remoto",
    "TermService": "Área de Trabalho Remota",
    "RasMan": "Conexões de acesso remoto (VPN)",
    "Bowser": "Navegador de computadores (SMB antigo)",
    "SensrSvc": "Monitor de sensores",
    "TabletInputService": "Teclado de toque e caneta",
    "DiagTrack": "Telemetria (Experiências do Usuário)",
    "diagsvc": "Serviço de diagnóstico",
    "WdiServiceHost": "Host do serviço de diagnóstico",
    "MapsBroker": "Mapas baixados",
    "SCardSvr": "Cartão inteligente",
    "WerSvc": "Relatório de erros do Windows",
    "XblAuthManager": "Xbox Live: autenticação",
    "XblGameSave": "Xbox Live: jogos salvos",
    "XboxNetApiSvc": "Xbox Live: rede",
    "PhoneSvc": "Serviço de telefone",
    "TrkWks": "Rastreamento de links",
    "WpcMonSvc": "Controle dos pais",
    "icssvc": "Ponto de acesso móvel",
    "WMPNetworkSvc": "Compartilhamento do Media Player",
    "RetailDemo": "Modo demonstração de loja",
    "wisvc": "Windows Insider",
}

_START_TO_SC = {0: "boot", 1: "system", 2: "auto", 3: "demand", 4: "disabled"}
_START_LABEL = {0: "Boot", 1: "Sistema", 2: "Automático", 3: "Manual", 4: "Desativado"}


def _store_file():
    base = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "FaxinaVarzea")
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "services.json")


def _load_orig():
    try:
        with open(_store_file(), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save_orig(d):
    try:
        with open(_store_file(), "w", encoding="utf-8") as f:
            json.dump(d, f)
    except OSError:
        pass


def _read(name):
    """(start, atrasado) do registro, ou None se o serviço não existe neste Windows."""
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, SVC_ROOT + "\\" + name) as k:
            start = winreg.QueryValueEx(k, "Start")[0]
            try:
                delayed = bool(winreg.QueryValueEx(k, "DelayedAutostart")[0])
            except OSError:
                delayed = False
            return start, delayed
    except OSError:
        return None


def disabled_by_app():
    """Serviços que o WebDark desligou e ainda estão desligados: [{name, title, was}]."""
    out = []
    for name, prev in _load_orig().items():
        cur = _read(name)
        if cur and cur[0] == 4:
            out.append({"name": name, "title": TITLES.get(name, name),
                        "was": _START_LABEL.get(prev.get("start"), "Manual")})
    return out


def _sc_config(name, mode):
    r = subprocess.run(["sc.exe", "config", name, "start=", mode], capture_output=True, stdin=subprocess.DEVNULL,
                       creationflags=bk.CREATE_NO_WINDOW)
    return r.returncode == 0, r.stdout.decode("cp850", errors="replace").strip()


def restore_all():
    """Volta cada serviço desligado pelo app ao tipo de início que tinha. -> (quantos voltaram, quantos eram)."""
    orig, todo = _load_orig(), disabled_by_app()
    done = 0
    for s in todo:
        prev = orig[s["name"]]
        mode = "delayed-auto" if prev["start"] == 2 and prev.get("delayed") else _START_TO_SC.get(prev["start"], "demand")
        if _sc_config(s["name"], mode)[0]:
            orig.pop(s["name"], None)
            done += 1
    _save_orig(orig)
    return done, len(todo)
