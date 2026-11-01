"""Atualização pelo GitHub Releases: procura versão nova, baixa o .exe e troca o arquivo."""
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from urllib.parse import urlparse

from version import REPO, VERSION

API = f"https://api.github.com/repos/{REPO}/releases/latest"
_HOSTS = ("github.com", "githubusercontent.com")
_HEADERS = {"User-Agent": "FaxinaVarzea-updater", "Accept": "application/vnd.github+json"}


@dataclass
class Update:
    version: str
    notes: str
    url: str
    size: int
    sha256: str


def _ver(text):
    return tuple(int(n) for n in re.findall(r"\d+", text)[:4]) or (0,)


def _trusted(url):
    p = urlparse(url)
    return p.scheme == "https" and any(p.hostname == h or p.hostname.endswith("." + h) for h in _HOSTS)


def check():
    """-> Update se existir versão mais nova, senão None. Erros de rede viram None."""
    try:
        req = urllib.request.Request(API, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.load(r)
    except (urllib.error.URLError, OSError, ValueError):
        return None
    tag = str(data.get("tag_name", ""))
    if _ver(tag) <= _ver(VERSION):
        return None
    for a in data.get("assets", []):
        url = a.get("browser_download_url", "")
        if a.get("name", "").lower().endswith(".exe") and _trusted(url):
            digest = str(a.get("digest") or "").lower().removeprefix("sha256:")
            return Update(tag.lstrip("vV"), str(data.get("body") or ""), url, int(a.get("size") or 0), digest)
    return None


def download(up, progress=None):
    """Baixa o .exe novo para a pasta temporária e confere o SHA-256 quando o GitHub informa. -> caminho"""
    folder = tempfile.mkdtemp(prefix="FaxinaVarzea-update-")
    dest = os.path.join(folder, "FaxinaVarzea.exe.novo")
    h = hashlib.sha256()
    req = urllib.request.Request(up.url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r, open(dest, "wb") as f:
        total = int(r.headers.get("Content-Length") or up.size or 0)
        got = 0
        while True:
            chunk = r.read(1 << 16)
            if not chunk:
                break
            f.write(chunk)
            h.update(chunk)
            got += len(chunk)
            if progress and total:
                progress(got / total)
    if up.sha256 and h.hexdigest() != up.sha256:
        os.remove(dest)
        raise ValueError("O arquivo baixado não bate com o SHA-256 do GitHub. Não vou instalar.")
    if os.path.getsize(dest) < 1_000_000:
        os.remove(dest)
        raise ValueError("Arquivo baixado pequeno demais. Não vou instalar.")
    return dest


def can_self_update():
    return bool(getattr(sys, "frozen", False))


def apply(new_path):
    """Troca o .exe em uso pelo novo depois que este programa fechar, e abre de novo. Quem chamou deve fechar o app."""
    exe = sys.executable
    bat = os.path.join(os.path.dirname(new_path), "atualizar.bat")
    script = (
        "@echo off\r\n"
        "set n=0\r\n"
        ":retry\r\n"
        "set /a n+=1\r\n"
        "ping 127.0.0.1 -n 2 >nul\r\n"
        f'move /y "{new_path}" "{exe}" >nul 2>&1 && goto ok\r\n'
        "if %n% lss 40 goto retry\r\n"
        "exit /b 1\r\n"
        ":ok\r\n"
        f'start "" "{exe}"\r\n'
        "ping 127.0.0.1 -n 9 >nul\r\n"                      # o app novo confere quem o abriu: este script não pode sumir antes
        '(goto) 2>nul & del "%~f0"\r\n'
    )
    with open(bat, "w", encoding="cp850", errors="replace") as f:
        f.write(script)
    subprocess.Popen(["cmd", "/c", bat], creationflags=0x08000000, stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
