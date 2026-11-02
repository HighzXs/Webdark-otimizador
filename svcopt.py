"""Serviços do Windows que dá pra desligar (libera CPU e RAM). Só os da lista SERVICES; guarda como estava pra desfazer."""
import json
import os
import subprocess
import winreg

import psutil

import backend as bk

SVC_ROOT = r"SYSTEM\CurrentControlSet\Services"

# risco: low = quase ninguém usa; mid = depende do que você usa; high = pode quebrar algo comum
SERVICES = [
    dict(name="Spooler", title="Fila de impressão", risk="mid", sug=False,
         desc="Gerencia a impressão.", breaks="Você não consegue imprimir nem salvar em PDF pela impressora virtual."),
    dict(name="Fax", title="Fax", risk="low", sug=False,
         desc="Enviar e receber fax pelo PC.", breaks="Nada, quase ninguém usa."),
    dict(name="RemoteRegistry", title="Registro remoto", risk="low", sug=False,
         desc="Deixa outro computador da rede mexer no registro deste.", breaks="Administração remota do PC. Desligado também é mais seguro."),
    dict(name="TermService", title="Área de Trabalho Remota", risk="low", sug=False,
         desc="Permite que outro PC controle este.", breaks="Acesso remoto pelo Windows (RDP) a este PC."),
    dict(name="RasMan", title="Conexões de acesso remoto (VPN)", risk="high", sug=False,
         desc="Gerencia VPN e conexão discada/PPPoE.", breaks="VPNs (inclusive a do Windows) e internet por PPPoE deixam de conectar."),
    dict(name="Bowser", title="Navegador de computadores (SMB antigo)", risk="low", sug=False,
         desc="Parte antiga da rede local do Windows.", breaks="Ver computadores da rede por nome em redes antigas."),
    dict(name="SensrSvc", title="Monitor de sensores", risk="low", sug=False,
         desc="Lê sensores do PC, como o de brilho automático.", breaks="Brilho e rotação automáticos da tela."),
    dict(name="TabletInputService", title="Teclado de toque e caneta", risk="mid", sug=False,
         desc="Teclado na tela, escrita à mão e caneta.", breaks="Teclado virtual, caneta e tela sensível ao toque."),
    dict(name="DiagTrack", title="Telemetria (Experiências do Usuário)", risk="low", sug=False,
         desc="Envia dados de uso para a Microsoft.", breaks="Quase nada: relatórios de uso."),
    dict(name="diagsvc", title="Serviço de diagnóstico", risk="low", sug=False,
         desc="Executa diagnósticos automáticos do Windows.", breaks="Os 'solucionadores de problemas' automáticos."),
    dict(name="WdiServiceHost", title="Host do serviço de diagnóstico", risk="low", sug=False,
         desc="Parte dos diagnósticos do Windows.", breaks="Diagnóstico automático de problemas."),
    dict(name="MapsBroker", title="Mapas baixados", risk="low", sug=False,
         desc="Baixa mapas para uso sem internet.", breaks="Mapas offline do Windows."),
    dict(name="SCardSvr", title="Cartão inteligente", risk="mid", sug=False,
         desc="Lê cartões e tokens de certificado.", breaks="Certificado digital em cartão ou token (e-CPF, e-CNPJ A3) e alguns logins corporativos."),
    dict(name="WerSvc", title="Relatório de erros do Windows", risk="low", sug=False,
         desc="Envia relatórios quando um programa trava.", breaks="Os relatórios de erro. Útil só pra quem investiga travamentos."),
    dict(name="XblAuthManager", title="Xbox Live: autenticação", risk="mid", sug=False,
         desc="Login na conta Xbox.", breaks="Jogos da Microsoft Store e Game Pass, Minecraft Bedrock e login Xbox."),
    dict(name="XblGameSave", title="Xbox Live: jogos salvos", risk="mid", sug=False,
         desc="Salva o progresso dos jogos Xbox na nuvem.", breaks="Salvamento na nuvem de jogos da Microsoft Store e Game Pass."),
    # sugeridos além da sua lista
    dict(name="XboxNetApiSvc", title="Xbox Live: rede", risk="mid", sug=True,
         desc="Rede dos jogos Xbox.", breaks="Multiplayer de jogos da Microsoft Store e Game Pass."),
    dict(name="PhoneSvc", title="Serviço de telefone", risk="low", sug=True,
         desc="Liga o PC ao celular (Vincular ao Celular).", breaks="O recurso 'Vincular ao Celular'."),
    dict(name="TrkWks", title="Rastreamento de links", risk="low", sug=True,
         desc="Acompanha atalhos de arquivos que mudaram de lugar.", breaks="Atalhos para arquivos movidos entre discos de rede."),
    dict(name="WpcMonSvc", title="Controle dos pais", risk="low", sug=True,
         desc="Filtros e limites da Segurança da Família.", breaks="Controle dos pais do Windows."),
    dict(name="icssvc", title="Ponto de acesso móvel", risk="low", sug=True,
         desc="Compartilha a internet do PC por Wi-Fi.", breaks="O 'Ponto de acesso móvel' do Windows."),
    dict(name="WMPNetworkSvc", title="Compartilhamento do Media Player", risk="low", sug=True,
         desc="Compartilha músicas e vídeos pela rede.", breaks="Transmitir mídia do Windows Media Player para outros aparelhos."),
    dict(name="RetailDemo", title="Modo demonstração de loja", risk="low", sug=True,
         desc="Serve só para PCs de vitrine.", breaks="Nada."),
    dict(name="wisvc", title="Windows Insider", risk="low", sug=True,
         desc="Versões de teste do Windows.", breaks="Receber versões de teste (Insider)."),
]
BY_NAME = {s["name"]: s for s in SERVICES}

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


def _running(name):
    try:
        return psutil.win_service_get(name).status() == "running"
    except Exception:
        return False


def list_state():
    orig, rows = _load_orig(), []
    for s in SERVICES:
        r = _read(s["name"])
        if r is None:
            continue
        start, delayed = r
        rows.append({**s, "start": start, "start_label": _START_LABEL.get(start, str(start)), "off": start == 4,
                     "running": _running(s["name"]), "was": _START_LABEL.get(orig.get(s["name"], {}).get("start")) or None,
                     "can_restore": start != 4 or s["name"] in orig})   # já desligado de fábrica: não há o que voltar
    return rows


def _sc_config(name, mode):
    r = subprocess.run(["sc.exe", "config", name, "start=", mode], capture_output=True, stdin=subprocess.DEVNULL,
                       creationflags=bk.CREATE_NO_WINDOW)
    return r.returncode == 0, r.stdout.decode("cp850", errors="replace").strip()


def set_off(name, off):
    """Desliga (desativa e para) ou volta ao que era. -> (ok, mensagem). Precisa de administrador."""
    s = BY_NAME.get(name)
    if s is None:
        return False, "Esse serviço não está na lista."
    cur = _read(name)
    if cur is None:
        return False, "Esse serviço não existe neste Windows."
    orig = _load_orig()
    if off:
        if cur[0] != 4:
            orig[name] = {"start": cur[0], "delayed": cur[1]}
            _save_orig(orig)
        ok, out = _sc_config(name, "disabled")
        if not ok:
            return False, "O Windows recusou: " + (out.splitlines()[-1] if out else "sem detalhes")
        subprocess.run(["net.exe", "stop", name, "/y"], capture_output=True, stdin=subprocess.DEVNULL,
                       creationflags=bk.CREATE_NO_WINDOW, timeout=60)
        return True, f"{s['title']} desligado."
    prev = orig.get(name) or {"start": 3, "delayed": False}
    mode = "delayed-auto" if prev["start"] == 2 and prev.get("delayed") else _START_TO_SC.get(prev["start"], "demand")
    ok, out = _sc_config(name, mode)
    if not ok:
        return False, "O Windows recusou: " + (out.splitlines()[-1] if out else "sem detalhes")
    orig.pop(name, None)
    _save_orig(orig)
    return True, f"{s['title']} voltou ao que era ({_START_LABEL.get(prev['start'], 'Manual')})."
