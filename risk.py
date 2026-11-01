"""Avalia o risco de apagar um arquivo."""
import ctypes
import os
import time
from dataclasses import dataclass

OK, CARE, DANGER = "ok", "care", "danger"
LABEL = {OK: "SEGURO", CARE: "CUIDADO", DANGER: "NÃO APAGUE"}

PERSONAL = {
    ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".mp3", ".wav", ".flac", ".m4a",
    ".jpg", ".jpeg", ".png", ".raw", ".cr2", ".nef", ".heic", ".psd", ".ai", ".blend",
    ".docx", ".doc", ".pdf", ".xlsx", ".xls", ".pptx", ".odt", ".txt", ".kdbx", ".sql",
    ".fbx", ".obj", ".prproj", ".aep", ".dwg", ".skp",
}
CACHE_FRAGS = (
    "\\cache\\", "\\cache2\\", "\\code cache\\", "\\gpucache\\", "\\shadercache\\", "\\crashdumps\\",
    "\\npm-cache\\", "\\pip\\cache\\", "\\htmlcache\\", "\\cachestorage\\", "\\media cache files\\",
    "\\inetcache\\", "\\appdata\\local\\temp\\",
)

_k32 = ctypes.WinDLL("kernel32", use_last_error=True)
_k32.CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p,
                             ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p]
_k32.CreateFileW.restype = ctypes.c_void_p
_k32.CloseHandle.argtypes = [ctypes.c_void_p]
_INVALID = ctypes.c_void_p(-1).value


@dataclass
class Risk:
    level: str
    text: str
    in_use: bool = False
    age_days: int = 0


def is_in_use(path):
    """True se outro programa está com o arquivo aberto agora."""
    h = _k32.CreateFileW(path, 0x80000000, 0, None, 3, 0, None)  # leitura, sem compartilhar
    if h is None or h == _INVALID:
        return ctypes.get_last_error() in (32, 33)
    _k32.CloseHandle(h)
    return False


def _classify(low, name, ext, age, win):
    in_app = "\\appdata\\" in low or "\\programdata\\" in low
    downloads = "\\downloads\\" in low

    if name in ("pagefile.sys", "swapfile.sys"):
        return DANGER, "Memória virtual do Windows. Não dá pra apagar; ajuste em Configurações > Desempenho."
    if name == "hiberfil.sys":
        return CARE, "Arquivo de hibernação. Desligue a hibernação na aba Limpeza em vez de apagar."
    if name.startswith("ntuser.dat"):
        return DANGER, "Perfil do seu usuário no Windows. Apagar quebra o login."

    if low.startswith(win + "\\"):
        if any(x in low for x in ("\\temp\\", "\\softwaredistribution\\download", "\\logs\\", "\\minidump\\",
                                  "\\prefetch\\")) or ext in (".dmp", ".log", ".etl"):
            return OK, "Arquivo temporário ou de registro do Windows. Ele recria o que precisar."
        if "\\installer\\" in low:
            return DANGER, "Cache do instalador do Windows. Apagar impede desinstalar ou reparar programas."
        if "\\winsxs\\" in low:
            return DANGER, "Componentes do Windows. Use 'Limpar componentes' na aba Limpeza."
        return DANGER, "Arquivo do sistema Windows. Apagar pode impedir o PC de ligar."

    if "\\windows.old" in low:
        return OK, "Restos da versão anterior do Windows. Apague pela Limpeza de Disco do Windows."
    if "$recycle.bin" in low:
        return OK, "Já está na lixeira. Esvazie pela aba Limpeza."
    if "\\$windows.~bt" in low or "\\$windows.~ws" in low:
        return OK, "Sobras de atualização do Windows."

    if (in_app and any(f in low for f in CACHE_FRAGS)) or "\\steamapps\\shadercache\\" in low:
        return OK, "Cache ou arquivo temporário. O programa recria sozinho."
    if ext in (".tmp", ".temp", ".dmp", ".etl", ".chk"):
        return OK, "Arquivo temporário ou de diagnóstico. Pode apagar."
    if ext == ".log":
        return OK, "Arquivo de registro (log). Pode apagar."

    if low.endswith("ext4.vhdx"):
        return DANGER, "Disco do Linux (WSL). Apagar perde tudo que está no Linux."
    if "\\program files" in low or "\\programdata\\" in low or "\\windowsapps\\" in low:
        return DANGER, "Parte de programa instalado. Desinstale pela aba Programas."
    if "\\appdata\\local\\microsoft\\" in low or "\\appdata\\roaming\\microsoft\\" in low:
        return DANGER, "Dados do Windows ou do Office. Não mexa."
    if "\\appdata\\" in low:
        return CARE, "Dados de um programa (contas, configurações). Apagar pode deslogar ou perder configurações."

    if ext in (".dll", ".sys", ".drv", ".ocx", ".cpl"):
        return DANGER, "Peça de programa ou driver. Apagar pode quebrar algo."
    if ext in (".pst", ".ost"):
        return DANGER, "E-mails do Outlook. Apagar perde mensagens."
    if ext in (".mdf", ".ldf", ".sqlite", ".sqlite3", ".db", ".accdb"):
        return DANGER, "Banco de dados. Apagar pode perder dados de algum programa."
    if ext in (".vhd", ".vhdx", ".vmdk", ".vdi", ".qcow2", ".vmem"):
        return CARE, "Disco de máquina virtual. Apagar perde tudo que está dentro dela."
    if "\\steamapps\\common\\" in low or "\\epic games\\" in low or "\\games\\" in low:
        return CARE, "Arquivo de jogo. Desinstale o jogo pela Steam/Epic ou pela aba Programas."
    if ext in (".bak", ".old"):
        return CARE, "Cópia de segurança antiga. Confira se não é a única cópia."
    if ext in (".exe", ".msi", ".msix", ".appx"):
        if downloads and age >= 30:
            return OK, f"Instalador antigo ({age} dias) em Downloads. Se precisar, baixe de novo."
        if downloads:
            return CARE, "Instalador baixado há pouco tempo. Confirme se já instalou."
        return CARE, "Programa executável. Pode ser um programa portátil que você usa."
    if ext in (".iso", ".img"):
        if downloads and age >= 30:
            return OK, f"Imagem de disco antiga ({age} dias) em Downloads. Dá pra baixar de novo."
        return CARE, "Imagem de disco (ISO). Confira se ainda precisa."
    if ext in (".zip", ".rar", ".7z", ".tar", ".gz"):
        return CARE, "Arquivo compactado. Abra e confira o conteúdo antes."
    if ext in PERSONAL:
        return CARE, f"Arquivo pessoal, modificado há {age} dias. Só você sabe se ainda precisa."
    return CARE, "Não reconheço esse tipo de arquivo. Confira antes de apagar."


def assess(path):
    p = os.path.normpath(path)
    low = p.lower()
    name = os.path.basename(low)
    ext = os.path.splitext(name)[1]
    win = (os.environ.get("SystemRoot") or r"C:\Windows").lower()
    try:
        age = max(0, int((time.time() - os.stat(p).st_mtime) // 86400))
    except OSError:
        age = 0
    level, text = _classify(low, name, ext, age, win)
    used = is_in_use(p)
    if used:
        text += " Está aberto agora por algum programa."
        if level == OK:
            level = CARE
    return Risk(level, text, used, age)
