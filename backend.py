"""Faxina Várzea - lógica (sem interface)."""
import ctypes
import glob
import heapq
import json
import os
import shutil
import subprocess
import winreg
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

CREATE_NO_WINDOW = 0x08000000
FILE_ATTRIBUTE_REPARSE_POINT = 0x400


# ----------------------------------------------------------------- utilidades
def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_as_admin():
    """Reabre o programa pedindo UAC. Retorna True se o pedido foi enviado."""
    import sys
    if getattr(sys, "frozen", False):
        exe, params = sys.executable, "--elevated"
    else:
        exe = sys.executable
        params = f'"{os.path.abspath(sys.argv[0])}" --elevated'
    r = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
    return r > 32


def fmt_size(n):
    n = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


def fixed_drives():
    out = []
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    for i in range(26):
        if bitmask & (1 << i):
            root = f"{chr(65 + i)}:\\"
            if ctypes.windll.kernel32.GetDriveTypeW(root) == 3:  # DRIVE_FIXED
                out.append(root)
    return out


def disk_usage(root):
    total, used, free = shutil.disk_usage(root)
    return total, used, free


def ps(script, timeout=120):
    """Roda PowerShell e devolve stdout (utf-8)."""
    full = "[Console]::OutputEncoding=[Text.Encoding]::UTF8;" + script
    r = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", full],
        capture_output=True, timeout=timeout, creationflags=CREATE_NO_WINDOW,
    )
    return r.stdout.decode("utf-8", errors="replace")


def ps_stream(script):
    """Roda PowerShell e entrega linha a linha."""
    full = "[Console]::OutputEncoding=[Text.Encoding]::UTF8;" + script
    p = subprocess.Popen(
        ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", full],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=CREATE_NO_WINDOW,
    )
    for raw in p.stdout:
        yield raw.decode("utf-8", errors="replace").rstrip()
    p.wait()


def open_in_explorer(path):
    if os.path.isfile(path):
        subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
    else:
        os.startfile(path)


# ------------------------------------------------------------------- tamanhos
def dir_size(path, cancel=None):
    total = 0
    stack = [path]
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
                            if st.st_file_attributes & FILE_ATTRIBUTE_REPARSE_POINT:
                                continue
                            stack.append(e.path)
                        else:
                            total += st.st_size
                    except OSError:
                        pass
        except OSError:
            pass
    return total


def path_size(p, cancel=None):
    try:
        if os.path.isfile(p):
            return os.path.getsize(p)
        if os.path.isdir(p):
            return dir_size(p, cancel)
    except OSError:
        pass
    return 0


def scan_children(path, cancel=None):
    """Tamanho de cada item direto de `path`. -> [(nome, caminho, tamanho, é_pasta)]"""
    items = []
    try:
        with os.scandir(path) as it:
            entries = list(it)
    except OSError:
        return items

    def one(e):
        try:
            if e.is_symlink():
                return None
            st = e.stat(follow_symlinks=False)
            if e.is_dir(follow_symlinks=False):
                if st.st_file_attributes & FILE_ATTRIBUTE_REPARSE_POINT:
                    return None
                return (e.name, e.path, dir_size(e.path, cancel), True)
            return (e.name, e.path, st.st_size, False)
        except OSError:
            return None

    with ThreadPoolExecutor(max_workers=8) as ex:
        for r in ex.map(one, entries):
            if r:
                items.append(r)
    items.sort(key=lambda x: x[2], reverse=True)
    return items


def find_big_files(root, min_bytes, cancel=None, progress=None, top=100):
    heap = []  # (tamanho, caminho)
    seen = 0
    stack = [root]
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
                            if not st.st_file_attributes & FILE_ATTRIBUTE_REPARSE_POINT:
                                stack.append(e.path)
                        else:
                            seen += 1
                            if st.st_size >= min_bytes:
                                if len(heap) < top:
                                    heapq.heappush(heap, (st.st_size, e.path))
                                elif st.st_size > heap[0][0]:
                                    heapq.heapreplace(heap, (st.st_size, e.path))
                    except OSError:
                        pass
        except OSError:
            pass
        if progress and seen % 500 < 50:
            progress(seen, d)
    return sorted(heap, reverse=True)


def send_to_trash(path):
    from send2trash import send2trash
    send2trash(os.path.normpath(path))


# -------------------------------------------------------------------- limpeza
def _env(name):
    return os.environ.get(name, "")


def _expand(patterns):
    out = []
    for p in patterns:
        if not p:
            continue
        if any(ch in p for ch in "*?["):
            out.extend(glob.glob(p))
        elif os.path.exists(p):
            out.append(p)
    return out


def _browser_caches():
    local = _env("LOCALAPPDATA")
    roaming_roots = [
        os.path.join(local, r"Google\Chrome\User Data"),
        os.path.join(local, r"Microsoft\Edge\User Data"),
        os.path.join(local, r"BraveSoftware\Brave-Browser\User Data"),
        os.path.join(local, r"Vivaldi\User Data"),
        os.path.join(_env("APPDATA"), r"Opera Software\Opera Stable"),
    ]
    subs = ["Cache", "Code Cache", "GPUCache", r"Service Worker\CacheStorage"]
    pats = []
    for root in roaming_roots:
        for prof in ("Default", "Profile *"):
            for s in subs:
                pats.append(os.path.join(root, prof, s))
        pats.append(os.path.join(root, "ShaderCache"))
        pats.append(os.path.join(root, "GrShaderCache"))
    pats.append(os.path.join(local, r"Mozilla\Firefox\Profiles\*\cache2"))
    return _expand(pats)


def _steam_path():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as k:
            return os.path.normpath(winreg.QueryValueEx(k, "SteamPath")[0])
    except OSError:
        return ""


def _app_caches():
    ap, lo = _env("APPDATA"), _env("LOCALAPPDATA")
    pats = []
    if ap:
        for sub in (r"discord\Cache", r"discord\Code Cache", r"discord\GPUCache",
                    r"Code\Cache", r"Code\CachedData", r"Code\Code Cache", r"Code\GPUCache",
                    r"Code\CachedExtensionVSIXs",
                    r"Microsoft\Teams\Cache", r"Microsoft\Teams\Code Cache", r"Microsoft\Teams\GPUCache",
                    r"Microsoft\Teams\Service Worker\CacheStorage",
                    r"Adobe\Common\Media Cache Files", r"Adobe\Common\Media Cache"):
            pats.append(os.path.join(ap, sub))
    if lo:
        for sub in (r"Spotify\Data", r"Steam\htmlcache", "npm-cache", r"pip\Cache"):
            pats.append(os.path.join(lo, sub))
    steam = _steam_path()
    if steam:
        pats += [os.path.join(steam, r"steamapps\shadercache"), os.path.join(steam, r"appcache\httpcache")]
    return _expand(pats)


@dataclass
class Cleaner:
    key: str
    name: str
    desc: str
    default: bool = True
    admin: bool = False
    special: str = ""        # "recycle" tem tratamento próprio
    getter: object = None    # função -> lista de caminhos
    warn: str = ""           # aviso mostrado antes de limpar (itens que mexem em algo do sistema)
    size: int = 0
    freed: int = 0

    def targets(self):
        return self.getter() if self.getter else []


def make_cleaners():
    win = _env("SystemRoot") or r"C:\Windows"
    local = _env("LOCALAPPDATA")
    return [
        Cleaner("temp_user", "Arquivos temporários do usuário",
                "Sobras de programas na pasta Temp. Seguro.",
                getter=lambda: _expand([_env("TEMP")])),
        Cleaner("temp_win", "Arquivos temporários do Windows",
                "Pasta Windows\\Temp. Precisa de administrador.", admin=True,
                getter=lambda: _expand([os.path.join(win, "Temp")])),
        Cleaner("recycle", "Lixeira",
                "Tudo que você já apagou e ainda está na lixeira.", special="recycle"),
        Cleaner("browsers", "Cache dos navegadores",
                "Chrome, Edge, Brave, Opera e Firefox. Feche os navegadores antes. Não apaga senhas nem histórico.",
                getter=_browser_caches),
        Cleaner("appcache", "Cache de apps (Discord, Spotify, Steam, Teams, VS Code, Adobe)",
                "Só cache, não apaga contas nem músicas baixadas. Feche esses apps antes.",
                getter=_app_caches),
        Cleaner("thumbs", "Miniaturas e ícones em cache",
                "O Windows recria sozinho quando precisar.",
                getter=lambda: _expand([
                    os.path.join(local, r"Microsoft\Windows\Explorer\thumbcache_*.db"),
                    os.path.join(local, r"Microsoft\Windows\Explorer\iconcache_*.db"),
                ])),
        Cleaner("wu", "Downloads do Windows Update",
                "Instaladores de atualização já baixados. Precisa de administrador.", admin=True,
                getter=lambda: _expand([os.path.join(win, r"SoftwareDistribution\Download")])),
        Cleaner("do", "Cache de entrega do Windows (Delivery Optimization)",
                "Cache de atualizações compartilhadas. Precisa de administrador.", admin=True,
                getter=lambda: _expand([os.path.join(win, r"ServiceProfiles\NetworkService\AppData\Local\Microsoft\Windows\DeliveryOptimization\Cache")])),
        Cleaner("wer", "Relatórios de erro e dumps de travamento",
                "Arquivos de diagnóstico que o Windows guarda quando algo trava.",
                getter=lambda: _expand([
                    os.path.join(local, r"Microsoft\Windows\WER"),
                    os.path.join(_env("ProgramData"), r"Microsoft\Windows\WER"),
                    os.path.join(local, "CrashDumps"),
                    os.path.join(win, "Minidump"),
                    os.path.join(win, "MEMORY.DMP"),
                ])),
        Cleaner("evtlogs", "Histórico de eventos do Windows (Visualizador de Eventos)",
                "Apaga os registros antigos que o Windows guarda sobre erros e avisos. Precisa de administrador.",
                default=False, admin=True, special="eventlogs",
                warn="Apaga o histórico do Visualizador de Eventos. Depois disso fica mais difícil descobrir a causa "
                     "de travamentos e telas azuis que já aconteceram. Não afeta o funcionamento do Windows e "
                     "não dá pra desfazer."),
        Cleaner("logs", "Logs antigos do Windows",
                "Registros de instalação (CBS). Precisa de administrador.", default=False, admin=True,
                getter=lambda: _expand([os.path.join(win, r"Logs\CBS")])),
    ]


class _RBInfo(ctypes.Structure):
    _pack_ = 1
    _fields_ = [("cbSize", ctypes.c_ulong), ("i64Size", ctypes.c_longlong), ("i64NumItems", ctypes.c_longlong)]


def recycle_size():
    info = _RBInfo()
    info.cbSize = ctypes.sizeof(_RBInfo)
    try:
        if ctypes.windll.shell32.SHQueryRecycleBinW(None, ctypes.byref(info)) == 0:
            return info.i64Size
    except Exception:
        pass
    return 0


def measure(c, cancel=None):
    if c.special == "recycle":
        c.size = recycle_size()
    elif c.special == "eventlogs":
        c.size = path_size(os.path.join(_env("SystemRoot") or r"C:\Windows", r"System32\winevt\Logs"), cancel)
    else:
        c.size = sum(path_size(p, cancel) for p in c.targets())
    return c.size


def low_priority():
    """Põe a thread atual em modo 'segundo plano' do Windows: pouca CPU, pouco disco, não atrapalha o PC."""
    try:
        ctypes.windll.kernel32.SetThreadPriority(ctypes.c_void_p(-2), 0x00010000)  # THREAD_MODE_BACKGROUND_BEGIN
    except Exception:
        pass


def quick_summary(progress=None):
    """Resumo rápido do PC, sem pedir administrador. `progress(dict)` recebe o que já foi calculado."""
    import startup
    low_priority()
    out = {}
    total, _, free = disk_usage("C:\\")
    out["free"], out["total"] = free, total
    if progress:
        progress(dict(out))
    try:
        out["startup"] = sum(1 for i in startup._list_run() + startup._list_folders() if i.enabled)
    except Exception:
        out["startup"] = 0
    if progress:
        progress(dict(out))
    out["junk"] = sum(measure(c) for c in make_cleaners() if c.default and not c.admin)
    if progress:
        progress(dict(out))
    return out


def _stop_services(names):
    """Para os serviços que estão rodando e devolve quais eram."""
    lst = ",".join(f"'{n}'" for n in names)
    out = ps("$r=@(); foreach ($n in @(" + lst + ")) { $s = Get-Service $n -ErrorAction SilentlyContinue; "
             "if ($s -and $s.Status -eq 'Running') { $r += $n; Stop-Service $n -Force -ErrorAction SilentlyContinue } }; "
             "$r -join ','", timeout=90)
    return [n for n in out.strip().split(",") if n]


def _start_services(names):
    for n in names:
        ps(f"Start-Service -Name '{n}' -ErrorAction SilentlyContinue", timeout=60)


def _wipe(p):
    try:
        if os.path.isfile(p) or os.path.islink(p):
            os.chmod(p, 0o666)
            os.remove(p)
        elif os.path.isdir(p):
            shutil.rmtree(p, ignore_errors=True)
    except OSError:
        pass


def run_cleaner(c):
    before = measure(c)
    stopped = []
    if c.key == "wu":
        # o Windows Update trava os arquivos baixados: para os serviços, limpa e religa
        stopped = _stop_services(["wuauserv", "bits"])
    try:
        if c.special == "recycle":
            # SHERB_NOCONFIRMATION | NOPROGRESSUI | NOSOUND
            ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 7)
        elif c.special == "eventlogs":
            ps('wevtutil el | ForEach-Object { wevtutil cl "$_" 2>$null }', timeout=240)
        else:
            for p in c.targets():
                if os.path.isdir(p):
                    try:
                        with os.scandir(p) as it:
                            children = [e.path for e in it]
                    except OSError:
                        continue
                    for ch in children:
                        # pasta _MEI* = arquivos do próprio programa (e de outros .exe do PyInstaller) em uso
                        if os.path.basename(ch).startswith("_MEI"):
                            continue
                        _wipe(ch)
                else:
                    _wipe(p)
    finally:
        _start_services(stopped)
    after = measure(c)
    c.freed = max(0, before - after)
    return c.freed


# --------------------------------------------------------------------- extras
def hiberfil_size():
    try:
        return os.path.getsize(r"C:\hiberfil.sys")
    except OSError:
        return 0


def windows_old_size():
    p = r"C:\Windows.old"
    return dir_size(p) if os.path.isdir(p) else 0


def hibernate_off():
    r = subprocess.run(["powercfg", "/h", "off"], capture_output=True, creationflags=CREATE_NO_WINDOW)
    return r.returncode == 0


def component_cleanup():
    """Gera linhas de saída do DISM."""
    p = subprocess.Popen(
        ["Dism.exe", "/Online", "/Cleanup-Image", "/StartComponentCleanup"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=CREATE_NO_WINDOW,
    )
    for raw in p.stdout:
        yield raw.decode("cp850", errors="replace").rstrip()
    p.wait()


def open_windows_cleanmgr():
    subprocess.Popen(["cleanmgr", "/d", "C"])


# ------------------------------------------------------------------- bloatware
# (trecho do nome em minúsculas, nome amigável, descrição, nível)
# nível: "lixo" = marcado por padrão | "opcional" = você decide
BLOAT_RULES = [
    ("candycrush", "Candy Crush", "Jogo patrocinado que vem instalado.", "lixo"),
    ("king.com", "Jogos da King", "Jogos patrocinados que vêm instalados.", "lixo"),
    ("bingnews", "Notícias (Bing)", "App de notícias da Microsoft.", "lixo"),
    ("bingweather", "Clima (Bing)", "App de clima da Microsoft.", "opcional"),
    ("bingfinance", "Finanças (Bing)", "App de finanças da Microsoft.", "lixo"),
    ("bingsports", "Esportes (Bing)", "App de esportes da Microsoft.", "lixo"),
    ("microsoft.news", "Notícias", "App de notícias da Microsoft.", "lixo"),
    ("getstarted", "Dicas", "Dicas do Windows.", "lixo"),
    ("gethelp", "Obter Ajuda", "Suporte da Microsoft.", "lixo"),
    ("officehub", "Office (hub)", "Atalho de propaganda do Office.", "lixo"),
    ("solitairecollection", "Microsoft Solitaire", "Pacote de jogos de paciência.", "lixo"),
    ("mixedreality", "Portal de Realidade Mista", "Só serve para óculos VR.", "lixo"),
    ("3dbuilder", "3D Builder", "Modelagem 3D que quase ninguém usa.", "lixo"),
    ("3dviewer", "Visualizador 3D", "Visualizador de modelos 3D.", "lixo"),
    ("print3d", "Print 3D", "Impressão 3D.", "lixo"),
    ("oneconnect", "Planos móveis", "Compra de plano de celular.", "lixo"),
    ("microsoft.people", "Pessoas", "Agenda de contatos da Microsoft.", "lixo"),
    ("skypeapp", "Skype", "Versão pré-instalada do Skype.", "lixo"),
    ("microsoft.wallet", "Carteira", "Carteira da Microsoft.", "lixo"),
    ("feedbackhub", "Central de Feedback", "Envia opiniões para a Microsoft.", "lixo"),
    ("windowsmaps", "Mapas", "Mapas offline do Windows.", "opcional"),
    ("zunemusic", "Groove Música", "Player de música antigo.", "lixo"),
    ("zunevideo", "Filmes e TV", "Player de vídeo/loja da Microsoft.", "lixo"),
    ("549981c3f5f10", "Cortana", "Assistente de voz da Microsoft.", "lixo"),
    ("powerautomate", "Power Automate", "Automação para empresas.", "lixo"),
    ("messaging", "Mensagens", "App de mensagens antigo.", "lixo"),
    ("networkspeedtest", "Teste de velocidade", "Teste de rede da Microsoft.", "lixo"),
    ("advertising", "Biblioteca de anúncios", "Usada para mostrar anúncios em apps.", "lixo"),
    ("msteams", "Microsoft Teams (pessoal)", "Chat pré-instalado.", "lixo"),
    ("microsoftteams", "Microsoft Teams (pessoal)", "Chat pré-instalado.", "lixo"),
    ("clipchamp", "Clipchamp", "Editor de vídeo da Microsoft.", "opcional"),
    ("yourphone", "Seu Telefone", "Liga o PC ao celular.", "opcional"),
    ("windowscommunicationsapps", "Email e Calendário", "Apps Email e Calendário do Windows.", "opcional"),
    ("stickynotes", "Notas Autoadesivas", "Post-its na tela.", "opcional"),
    ("todos", "Microsoft To Do", "Lista de tarefas.", "opcional"),
    ("office.onenote", "OneNote", "Anotações da Microsoft.", "opcional"),
    ("windowsalarms", "Alarmes e Relógio", "Alarmes e cronômetro.", "opcional"),
    ("soundrecorder", "Gravador de Voz", "Gravador de áudio.", "opcional"),
    ("windowscamera", "Câmera", "App da webcam. Mantenha se usa webcam.", "opcional"),
    ("windows.photos", "Fotos", "Visualizador de fotos padrão.", "opcional"),
    ("screensketch", "Recorte e Esboço", "Capturas de tela.", "opcional"),
    ("mspaint", "Paint 3D", "Paint novo (o Paint clássico continua).", "opcional"),
    ("gamingapp", "Xbox (app)", "App do Xbox/Game Pass.", "opcional"),
    ("xboxapp", "Xbox (app antigo)", "App antigo do Xbox.", "opcional"),
    ("xboxgamingoverlay", "Xbox Game Bar", "Barra de jogos (Win+G).", "opcional"),
    ("xboxgameoverlay", "Xbox Game Overlay", "Sobreposição do Xbox.", "opcional"),
    ("xboxspeechtotextoverlay", "Xbox fala-para-texto", "Recurso do Xbox.", "opcional"),
    ("xbox.tcui", "Xbox TCUI", "Interface do Xbox. Alguns jogos da Store usam.", "opcional"),
    ("xboxidentityprovider", "Xbox Identity", "Login Xbox. Alguns jogos da Store usam.", "opcional"),
    # terceiros patrocinados
    ("spotify", "Spotify", "Reinstale pelo site se usar.", "opcional"),
    ("twitter", "Twitter / X", "App patrocinado.", "lixo"),
    ("facebook", "Facebook", "App patrocinado.", "lixo"),
    ("instagram", "Instagram", "App patrocinado.", "lixo"),
    ("tiktok", "TikTok", "App patrocinado.", "lixo"),
    ("disney", "Disney+", "App patrocinado.", "lixo"),
    ("netflix", "Netflix", "App patrocinado.", "opcional"),
    ("primevideo", "Prime Video", "App patrocinado.", "opcional"),
    ("amazon", "Amazon", "App patrocinado.", "lixo"),
    ("linkedin", "LinkedIn", "App patrocinado.", "lixo"),
    ("flipboard", "Flipboard", "App patrocinado.", "lixo"),
    ("duolingo", "Duolingo", "App patrocinado.", "lixo"),
    ("hulu", "Hulu", "App patrocinado.", "lixo"),
    ("pandora", "Pandora", "App patrocinado.", "lixo"),
    ("shazam", "Shazam", "App patrocinado.", "lixo"),
    ("photoshopexpress", "Photoshop Express", "App patrocinado.", "lixo"),
    ("roblox", "Roblox", "Jogo patrocinado.", "opcional"),
    ("hiddencity", "Hidden City", "Jogo patrocinado.", "lixo"),
    ("magickingdoms", "Disney Magic Kingdoms", "Jogo patrocinado.", "lixo"),
    ("bubblewitch", "Bubble Witch", "Jogo patrocinado.", "lixo"),
    ("mcafee", "McAfee", "Antivírus de teste que vem instalado.", "lixo"),
    ("wildtangent", "WildTangent Games", "Jogos de teste.", "lixo"),
]

# Nunca aparecem na lista: sem eles o Windows ou o hardware quebra.
PROTECTED = (
    "windowsstore", "storepurchaseapp", "desktopappinstaller", "windowscalculator", "sechealthui",
    "vclibs", "net.native", "ui.xaml", "services.store", "extension", "codec",
    "microsoft.windows.", "microsoftwindows.", "windows.", "microsoft.aad", "accountscontrol",
    "lockapp", "win32webviewhost", "asynctextservice", "creddialoghost", "ecapp", "bioenrollment",
    "microsoftedge", "notepad", "windowsterminal", "intel", "nvidia", "realtek", "amd", "dolby",
    "waves", "synaptics", "elan", "dts", "microsoft.directx", "microsoft.winget", "webview2",
    "runtime", "languageexperience", "handwriting", "applicationcompat", "startexperiences",
    "onedrivesync", "shellex", "winapp",
)
# Apps "Microsoft.*" que não estão na lista de bloat são do sistema ou do próprio usuário: escondidos.
HIDE_PREFIX = ("microsoft.", "microsoftcorporation", "microsoftwindows")


@dataclass
class AppxItem:
    name: str
    full: str
    friendly: str
    desc: str
    level: str  # lixo | opcional | outro


def list_appx():
    script = (
        "Get-AppxPackage | Where-Object { -not $_.IsFramework -and -not $_.NonRemovable } | "
        "Select-Object Name,PackageFullName,@{n='Sig';e={\"$($_.SignatureKind)\"}} | ConvertTo-Json -Compress"
    )
    raw = ps(script, timeout=180).strip()
    if not raw:
        return []
    data = json.loads(raw)
    if isinstance(data, dict):
        data = [data]
    items = {}
    for d in data:
        name, full = d["Name"], d["PackageFullName"]
        if d.get("Sig") == "System":
            continue
        low = name.lower()
        rule = next((r for r in BLOAT_RULES if r[0] in low), None)
        if rule is None and (any(p in low for p in PROTECTED) or low.startswith(HIDE_PREFIX)):
            continue
        if rule is not None and any(p in low for p in ("windowscalculator", "storepurchase", "windowsstore")):
            continue
        if rule:
            item = AppxItem(name, full, rule[1], rule[2], rule[3])
        else:
            item = AppxItem(name, full, name, "App que não conheço. Só remova se souber o que é.", "outro")
        items[full] = item
    order = {"lixo": 0, "opcional": 1, "outro": 2}
    return sorted(items.values(), key=lambda i: (order[i.level], i.friendly.lower()))


def remove_appx(items, admin):
    """Gera linhas de progresso."""
    lines = []
    for it in items:
        n = it.name.replace("'", "''")
        f = it.full.replace("'", "''")
        lines.append(
            f"try {{ Remove-AppxPackage -Package '{f}' -ErrorAction Stop; Write-Output 'OK|{n}' }} "
            f"catch {{ Write-Output ('FAIL|{n}|' + $_.Exception.Message.Split([char]10)[0]) }}"
        )
        if admin:
            lines.append(
                f"try {{ Get-AppxProvisionedPackage -Online | Where-Object {{ $_.DisplayName -eq '{n}' }} | "
                f"Remove-AppxProvisionedPackage -Online -ErrorAction Stop | Out-Null }} catch {{}}"
            )
    yield from ps_stream("\n".join(lines))


# ------------------------------------------------------ programas instalados
SUSPECT = ("mcafee", "norton", "wildtangent", "toolbar", "livesafe", "driver booster", "pc optimizer",
           "wise care", "ccleaner pro", "ask.com", "yahoo", "babylon", "conduit", "opera gx browser promo",
           "candy", "booking.com", "hp support", "dell supportassist", "mcafee")


@dataclass
class Program:
    name: str
    publisher: str
    size: int
    uninstall: str
    location: str = ""
    suspect: bool = False


def list_programs():
    roots = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]
    found = {}
    for hive, sub in roots:
        try:
            key = winreg.OpenKey(hive, sub)
        except OSError:
            continue
        for i in range(winreg.QueryInfoKey(key)[0]):
            try:
                sk = winreg.OpenKey(key, winreg.EnumKey(key, i))
            except OSError:
                continue

            def val(n, default=""):
                try:
                    return winreg.QueryValueEx(sk, n)[0]
                except OSError:
                    return default

            name = str(val("DisplayName")).strip()
            if not name or val("SystemComponent", 0) == 1 or val("ParentKeyName"):
                continue
            low = name.lower()
            if low.startswith(("update for", "security update", "hotfix", "microsoft visual c++", "microsoft .net",
                               "microsoft edge", "microsoft update health", "windows ")):
                continue
            uninst = val("QuietUninstallString") or val("UninstallString")
            if not uninst:
                continue
            uninst = str(val("UninstallString") or uninst)
            try:
                size = int(val("EstimatedSize", 0)) * 1024
            except (TypeError, ValueError):
                size = 0
            found[low] = Program(
                name, str(val("Publisher")), size, uninst, str(val("InstallLocation")),
                any(s in low for s in SUSPECT),
            )
    return sorted(found.values(), key=lambda p: (not p.suspect, -p.size, p.name.lower()))


def run_uninstaller(cmd):
    subprocess.Popen(cmd, shell=True)


# ------------------------------------------------------------------ histórico
def _hist_file():
    base = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "FaxinaVarzea")
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "history.json")


def history_load():
    try:
        with open(_hist_file(), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


def history_add(what, nbytes):
    if nbytes <= 0:
        return
    import time
    data = history_load()
    data.append({"t": time.strftime("%d/%m/%Y %H:%M"), "what": what, "bytes": int(nbytes)})
    try:
        with open(_hist_file(), "w", encoding="utf-8") as f:
            json.dump(data[-200:], f, ensure_ascii=False)
    except OSError:
        pass


def history_total():
    return sum(h.get("bytes", 0) for h in history_load())


# ---------------------------------------------------- ponto de restauração
def create_restore_point(desc="Faxina Várzea"):
    """-> (ok, mensagem). Precisa de administrador."""
    script = (
        "try { Enable-ComputerRestore -Drive 'C:\\' -ErrorAction SilentlyContinue; "
        f"Checkpoint-Computer -Description '{desc}' -RestorePointType MODIFY_SETTINGS "
        "-ErrorAction Stop -WarningVariable w -WarningAction SilentlyContinue; "
        "if ($w) { 'WARN|' + ($w -join ' ') } else { 'OK' } } catch { 'FAIL|' + $_.Exception.Message }"
    )
    out = ps(script, timeout=240).strip()
    if out == "OK":
        return True, "Ponto de restauração criado."
    if "1440" in out:
        return True, "Já existe um ponto de restauração de menos de 24h."
    return False, out.split("|", 1)[-1][:200] or "Não consegui criar."


# --------------------------------------------------------------- duplicados
_DUP_SKIP = ("\\windows\\", "\\program files", "\\programdata\\", "\\appdata\\", "$recycle.bin",
             "\\node_modules\\", "\\.git\\", "\\windowsapps\\", "\\steamapps\\", "system volume information")


def user_folders():
    home = os.path.expanduser("~")
    names = ("Desktop", "Documents", "Downloads", "Pictures", "Videos", "Music")
    return [p for p in (os.path.join(home, n) for n in names) if os.path.isdir(p)]


def _hash_file(path, limit=None):
    import hashlib
    h = hashlib.blake2b(digest_size=16)
    with open(path, "rb") as f:
        if limit:
            h.update(f.read(limit))
        else:
            while True:
                chunk = f.read(1 << 20)
                if not chunk:
                    break
                h.update(chunk)
    return h.digest()


def find_duplicates(roots, min_bytes=1 << 20, cancel=None, progress=None):
    """-> [{'size': n, 'files': [(caminho, mtime), ...]}] ordenado pelo desperdício."""
    by_size = {}
    seen = 0
    stack = list(roots)
    while stack:
        if cancel is not None and cancel.is_set():
            return []
        d = stack.pop()
        if any(s in d.lower() + "\\" for s in _DUP_SKIP):
            continue
        try:
            with os.scandir(d) as it:
                for e in it:
                    try:
                        if e.is_symlink():
                            continue
                        st = e.stat(follow_symlinks=False)
                        if e.is_dir(follow_symlinks=False):
                            if not st.st_file_attributes & FILE_ATTRIBUTE_REPARSE_POINT:
                                stack.append(e.path)
                        elif st.st_size >= min_bytes:
                            by_size.setdefault(st.st_size, []).append((e.path, st.st_mtime))
                            seen += 1
                    except OSError:
                        pass
        except OSError:
            pass
        if progress:
            progress(f"Listando arquivos… {seen} candidatos")

    groups = []
    cands = [(s, fs) for s, fs in by_size.items() if len(fs) > 1]
    for i, (size, files) in enumerate(cands):
        if cancel is not None and cancel.is_set():
            return []
        if progress and i % 5 == 0:
            progress(f"Comparando {i + 1}/{len(cands)}…")
        partial = {}
        for p, mt in files:
            try:
                partial.setdefault(_hash_file(p, 65536), []).append((p, mt))
            except OSError:
                pass
        for pg in partial.values():
            if len(pg) < 2:
                continue
            full = {}
            for p, mt in pg:
                try:
                    full.setdefault(_hash_file(p), []).append((p, mt))
                except OSError:
                    pass
            for fg in full.values():
                if len(fg) > 1:
                    groups.append({"size": size, "files": fg})
    groups.sort(key=lambda g: g["size"] * (len(g["files"]) - 1), reverse=True)
    return groups
