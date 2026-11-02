"""Rede: melhor DNS, adaptadores e Wi-Fi, Otimização de Entrega do Windows, limite de banda por programa,
drivers de rede e comandos de reparo. Só lógica (sem interface)."""
import ctypes
import json
import os
import random
import re
import socket
import statistics
import struct
import subprocess
import time
import winreg
from concurrent.futures import ThreadPoolExecutor

import psutil

import backend as bk
import health
import system

# (nome, DNS principal, DNS reserva, para que serve)
DNS_SERVERS = [
    ("Cloudflare", "1.1.1.1", "1.0.0.1", "Rápido e privado"),
    ("Google", "8.8.8.8", "8.8.4.4", "Estável e muito usado"),
    ("Quad9", "9.9.9.9", "149.112.112.112", "Bloqueia sites perigosos"),
    ("OpenDNS", "208.67.222.222", "208.67.220.220", "Estável, da Cisco"),
    ("AdGuard", "94.140.14.14", "94.140.15.15", "Bloqueia anúncios e rastreadores"),
    ("CleanBrowsing", "185.228.168.9", "185.228.169.9", "Filtro para família"),
]
TEST_NAMES = ["google.com", "youtube.com", "facebook.com", "wikipedia.org", "microsoft.com", "amazon.com", "netflix.com", "instagram.com"]
_IPV4 = re.compile(r"^(\d{1,3}\.){3}\d{1,3}$")


def _as_list(raw):
    raw = (raw or "").strip()
    if not raw:
        return []
    try:
        d = json.loads(raw)
    except ValueError:
        return []
    return d if isinstance(d, list) else [d]


# ------------------------------------------------------------------- DNS
def dns_query_ms(server, name, timeout=1.5):
    """Manda uma pergunta DNS de verdade (UDP, porta 53) e devolve em quantos ms veio a resposta, ou None."""
    qid = random.randrange(65536)
    packet = struct.pack(">HHHHHH", qid, 0x0100, 1, 0, 0, 0)
    packet += b"".join(bytes([len(p)]) + p.encode() for p in name.split(".")) + b"\x00" + struct.pack(">HH", 1, 1)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(timeout)
    try:
        t = time.perf_counter()
        s.sendto(packet, (server, 53))
        data, _ = s.recvfrom(1024)
        ms = (time.perf_counter() - t) * 1000
    except OSError:
        return None
    finally:
        s.close()
    if len(data) < 12 or struct.unpack(">H", data[:2])[0] != qid or (data[3] & 0x0F) != 0:
        return None
    return ms


def _bench_one(ip):
    times = [dns_query_ms(ip, n) for n in TEST_NAMES]
    ok = [t for t in times if t is not None]
    return {"ms": round(statistics.median(ok), 1) if ok else None, "fail": len(times) - len(ok)}


def current_dns():
    """DNS em uso nos adaptadores ligados: [{index, name, servers}]."""
    script = (
        "$up=Get-NetAdapter -Physical -EA SilentlyContinue|?{$_.Status -eq 'Up'}|%{$_.ifIndex};"
        "@(Get-DnsClientServerAddress -AddressFamily IPv4 -EA SilentlyContinue|?{$up -contains $_.InterfaceIndex}|"
        "Select @{n='index';e={$_.InterfaceIndex}},@{n='name';e={$_.InterfaceAlias}},@{n='servers';e={@($_.ServerAddresses)}})|ConvertTo-Json -Compress")
    cur = _as_list(bk.ps(script, timeout=30))
    for c in cur:
        if isinstance(c.get("servers"), str):
            c["servers"] = [c["servers"]]
    return cur


def dns_benchmark(progress=None):
    """Testa os DNS da lista e os que você usa hoje. Devolve do mais rápido pro mais lento."""
    cur = current_dns()
    used = []
    for c in cur:
        for ip in c.get("servers") or []:
            if _IPV4.match(ip) and ip not in used:
                used.append(ip)
    known = {s[1] for s in DNS_SERVERS}
    jobs = [(n, p, s, d, "list") for n, p, s, d in DNS_SERVERS] + [("Atual (" + ip + ")", ip, "", "O que o seu PC usa agora", "current") for ip in used if ip not in known]
    results = []
    with ThreadPoolExecutor(max_workers=len(jobs) or 1) as ex:
        futs = [(j, ex.submit(_bench_one, j[1])) for j in jobs]
        for n, (j, f) in enumerate(futs):
            r = f.result()
            results.append({"name": j[0], "primary": j[1], "secondary": j[2], "note": j[3], "kind": j[4],
                            "ms": r["ms"], "fail": r["fail"], "in_use": j[1] in used})
            if progress:
                progress(n + 1, len(futs))
    results.sort(key=lambda r: (r["ms"] is None, r["ms"] or 0, r["fail"]))
    return {"results": results, "current": cur}


def set_dns(primary, secondary):
    """Troca o DNS dos adaptadores ligados (precisa de administrador). Só aceita IPv4 válido."""
    addrs = [a for a in (primary, secondary) if a]
    if not addrs or not all(_IPV4.match(a) and all(0 <= int(x) <= 255 for x in a.split(".")) for a in addrs):
        return False, "Endereço de DNS inválido."
    out = bk.ps("$up=Get-NetAdapter -Physical|?{$_.Status -eq 'Up'};foreach($a in $up){try{Set-DnsClientServerAddress -InterfaceIndex $a.ifIndex "
                f"-ServerAddresses ({','.join(repr(a) for a in addrs)}) -ErrorAction Stop;'OK'}}catch{{'ERR|'+$_.Exception.Message}}}};ipconfig /flushdns|Out-Null", timeout=60)
    if "ERR|" in out or "OK" not in out:
        return False, (out.split("ERR|", 1)[1].strip()[:160] if "ERR|" in out else "Nenhum adaptador ligado.")
    return True, "DNS trocado."


def reset_dns():
    out = bk.ps("$up=Get-NetAdapter -Physical|?{$_.Status -eq 'Up'};foreach($a in $up){try{Set-DnsClientServerAddress -InterfaceIndex $a.ifIndex "
                "-ResetServerAddresses -ErrorAction Stop;'OK'}catch{'ERR|'+$_.Exception.Message}};ipconfig /flushdns|Out-Null", timeout=60)
    if "ERR|" in out or "OK" not in out:
        return False, (out.split("ERR|", 1)[1].strip()[:160] if "ERR|" in out else "Nenhum adaptador ligado.")
    return True, "DNS voltou ao automático."


# ----------------------------------------------------------- adaptadores e Wi-Fi
_TX = re.compile(r"transmit\s*power|tx\s*power|pot[eê]ncia\s+de\s+(transmiss|tx)", re.I)


def wifi_info():
    """Sinal do Wi-Fi pela API nativa do Windows. -> {"status": "ok"|"blocked"|"none", ...}.
    "blocked" = o Windows só libera o sinal com a Localização ligada (ou como administrador)."""
    from ctypes import POINTER, Structure, byref, c_void_p, c_ubyte, c_ulong, c_wchar, wintypes

    class GUID(Structure):
        _fields_ = [("a", wintypes.DWORD), ("b", wintypes.WORD), ("c", wintypes.WORD), ("d", c_ubyte * 8)]

    class IFACE(Structure):
        _fields_ = [("guid", GUID), ("desc", c_wchar * 256), ("state", wintypes.DWORD)]

    class IFLIST(Structure):
        _fields_ = [("n", wintypes.DWORD), ("idx", wintypes.DWORD), ("items", IFACE * 1)]

    class SSID(Structure):
        _fields_ = [("len", c_ulong), ("ssid", c_ubyte * 32)]

    class ASSOC(Structure):
        _fields_ = [("ssid", SSID), ("bss", c_ulong), ("bssid", c_ubyte * 6), ("phy", c_ulong), ("phyidx", c_ulong),
                    ("quality", c_ulong), ("rx", c_ulong), ("tx", c_ulong)]

    class CONN(Structure):
        _fields_ = [("state", c_ulong), ("mode", c_ulong), ("profile", c_wchar * 256), ("assoc", ASSOC)]

    try:
        w = ctypes.WinDLL("wlanapi")
    except OSError:
        return {"status": "none"}
    h, ver = wintypes.HANDLE(), wintypes.DWORD()
    if w.WlanOpenHandle(2, None, byref(ver), byref(h)) != 0:
        return {"status": "none"}
    lst = c_void_p()
    try:
        if w.WlanEnumInterfaces(h, None, byref(lst)) != 0 or not lst:
            return {"status": "none"}
        il = ctypes.cast(lst, POINTER(IFLIST)).contents
        if il.n < 1:
            return {"status": "none"}
        size, data, op = wintypes.DWORD(), c_void_p(), c_ulong()
        r = w.WlanQueryInterface(h, byref(il.items[0].guid), 7, None, byref(size), byref(data), byref(op))
        if r == 5:
            return {"status": "blocked"}
        if r != 0 or not data:
            return {"status": "none"}
        c = ctypes.cast(data, POINTER(CONN)).contents
        phy = {4: "802.11a", 5: "802.11b", 6: "802.11g", 7: "802.11n (Wi-Fi 4)", 8: "802.11ac (Wi-Fi 5)", 10: "802.11ax (Wi-Fi 6)", 11: "802.11be (Wi-Fi 7)"}
        out = {"status": "ok", "ssid": bytes(c.assoc.ssid.ssid[:c.assoc.ssid.len]).decode("utf-8", errors="replace"), "signal": int(c.assoc.quality),
               "rx": round(c.assoc.rx / 1000), "tx": round(c.assoc.tx / 1000), "radio": phy.get(c.assoc.phy, "")}
        w.WlanFreeMemory(data)
        return out
    finally:
        if lst:
            w.WlanFreeMemory(lst)
        w.WlanCloseHandle(h, None)

def adapters_info():
    """Adaptadores físicos, sinal do Wi-Fi e a opção de potência de transmissão (se o driver tiver)."""
    script = (
        "$a=@(Get-NetAdapter -Physical -EA SilentlyContinue|Select Name,InterfaceDescription,Status,LinkSpeed,PhysicalMediaType);"
        "$t=@(Get-NetAdapterAdvancedProperty -EA SilentlyContinue|?{$_.DisplayName -match 'Transmit Power|Tx Power|Pot.ncia de (Transmiss|Tx)'}|"
        "Select Name,DisplayName,DisplayValue,RegistryKeyword,@{n='valid';e={(@($_.ValidDisplayValues)|%{[string]$_}) -join '|'}});"
        "[pscustomobject]@{adapters=$a;tx=$t}|ConvertTo-Json -Depth 4 -Compress")
    try:
        d = json.loads(bk.ps(script, timeout=40) or "{}")
    except ValueError:
        d = {}
    adapters = d.get("adapters") or []
    adapters = adapters if isinstance(adapters, list) else [adapters]
    tx = d.get("tx") or []
    tx = tx if isinstance(tx, list) else [tx]
    wifi = wifi_info()
    for t in tx:
        t["valid"] = [v for v in str(t.get("valid") or "").split("|") if v]
    return {"adapters": adapters, "wifi": wifi, "txpower": tx}


def set_tx_power(adapter, keyword, value):
    """Muda a potência de transmissão do Wi-Fi para um valor que o próprio driver aceita (precisa de administrador)."""
    cur = [t for t in adapters_info()["txpower"] if t.get("Name") == adapter and t.get("RegistryKeyword") == keyword]
    if not cur or value not in cur[0]["valid"]:
        return False, "Esse valor não existe pro seu driver."
    esc = lambda s: str(s).replace("'", "''")
    out = bk.ps(f"try{{Set-NetAdapterAdvancedProperty -Name '{esc(adapter)}' -RegistryKeyword '{esc(keyword)}' -DisplayValue '{esc(value)}' -ErrorAction Stop;'OK'}}"
                "catch{'ERR|'+$_.Exception.Message}", timeout=60)
    return ("OK" in out and "ERR|" not in out), (out.split("ERR|", 1)[1].strip()[:160] if "ERR|" in out else "Potência alterada. O Wi-Fi pode piscar um instante.")


# ------------------------------------------------- Otimização de Entrega do Windows
DO_POLICY = r"SOFTWARE\Policies\Microsoft\Windows\DeliveryOptimization"


def _reg_get(name):
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, DO_POLICY) as k:
            return winreg.QueryValueEx(k, name)[0]
    except OSError:
        return None


def delivery_state():
    """DODownloadMode: 0 = só da Microsoft (sem repassar pra outros PCs), 99/100 = também sem rede local. Sem valor = padrão do Windows."""
    mode, cap = _reg_get("DODownloadMode"), _reg_get("DOPercentageMaxBackgroundBandwidth")
    return {"p2p_off": mode in (0, 99, 100), "cap": cap if isinstance(cap, int) and 0 < cap < 100 else 0}


def delivery_set(p2p_off=None, cap=None):
    """Liga/desliga o compartilhamento de atualizações com outros PCs e o limite de banda de fundo. Precisa de administrador."""
    try:
        with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, DO_POLICY, 0, winreg.KEY_SET_VALUE) as k:
            if p2p_off is not None:
                if p2p_off:
                    winreg.SetValueEx(k, "DODownloadMode", 0, winreg.REG_DWORD, 0)
                else:
                    _del(k, "DODownloadMode")
            if cap is not None:
                cap = int(cap)
                if 5 <= cap <= 95:
                    winreg.SetValueEx(k, "DOPercentageMaxBackgroundBandwidth", 0, winreg.REG_DWORD, cap)
                else:
                    _del(k, "DOPercentageMaxBackgroundBandwidth")
    except OSError as e:
        return False, str(e)
    return True, "Pronto. Vale a partir do próximo download do Windows."


def _del(key, name):
    try:
        winreg.DeleteValue(key, name)
    except OSError:
        pass


# ---------------------------------------------- limite de banda dos programas (QoS)
QOS_PREFIX = "WebDark - "
_APP = re.compile(r"^[\w .()\-]{1,80}\.exe$", re.I)
_SKIP = {"system", "idle", "registry", "svchost.exe", "system idle process", "lsass.exe", "services.exe", "wininit.exe", "csrss.exe"}


def net_apps():
    """Programas que estão usando a internet agora (conexões abertas), do que tem mais conexões pro que tem menos."""
    me = os.getpid()
    count, hosts = {}, {}
    try:
        conns = psutil.net_connections(kind="inet")
    except (psutil.AccessDenied, OSError):
        conns = []
    for c in conns:
        if c.pid and c.pid not in (me, 0, 4) and c.raddr and c.status == psutil.CONN_ESTABLISHED and not c.raddr.ip.startswith(("127.", "::1")):
            count[c.pid] = count.get(c.pid, 0) + 1
            hosts.setdefault(c.pid, set()).add(c.raddr.ip)
    by_name = {}
    for pid, n in count.items():
        try:
            p = psutil.Process(pid)
            name = p.name()
        except psutil.Error:
            continue
        if name.lower() in _SKIP or not _APP.match(name):
            continue
        a = by_name.setdefault(name, {"name": name, "conns": 0, "hosts": 0, "mem": 0})
        a["conns"] += n
        a["hosts"] += len(hosts[pid])
        try:
            a["mem"] += p.memory_info().rss
        except psutil.Error:
            pass
    return sorted(by_name.values(), key=lambda a: -a["conns"])


def qos_list():
    script = ("@(Get-NetQosPolicy -PolicyStore ActiveStore -EA SilentlyContinue|?{$_.Name -like 'WebDark - *'}|"
              "Select Name,AppPathNameMatchCondition,ThrottleRateActionBitsPerSecond)|ConvertTo-Json -Compress")
    return _as_list(bk.ps(script, timeout=30))


def qos_limit(app, kbytes_per_s):
    """Limita o que o programa ENVIA e marca o tráfego dele como "de fundo". Vale até reiniciar o PC. Precisa de administrador."""
    if not _APP.match(app or ""):
        return False, "Nome de programa inválido."
    bps = int(kbytes_per_s) * 8 * 1024
    if not 8 * 1024 <= bps <= 8 * 1024 * 1024 * 100:
        return False, "Limite fora do permitido."
    name = (QOS_PREFIX + app).replace("'", "''")
    out = bk.ps(f"try{{Get-NetQosPolicy -PolicyStore ActiveStore -Name '{name}' -EA SilentlyContinue|Remove-NetQosPolicy -PolicyStore ActiveStore -Confirm:$false;"
                f"New-NetQosPolicy -Name '{name}' -AppPathNameMatchCondition '{app.replace(chr(39), chr(39) * 2)}' -ThrottleRateActionBitsPerSecond {bps} "
                "-DSCPAction 8 -PolicyStore ActiveStore -ErrorAction Stop|Out-Null;'OK'}catch{'ERR|'+$_.Exception.Message}", timeout=60)
    return ("OK" in out and "ERR|" not in out), (out.split("ERR|", 1)[1].strip()[:160] if "ERR|" in out else "Limite aplicado.")


def qos_remove(name):
    if not name.startswith(QOS_PREFIX) or name not in {p.get("Name") for p in qos_list()}:
        return False, "Limite não encontrado."
    out = bk.ps(f"try{{Remove-NetQosPolicy -Name '{name.replace(chr(39), chr(39) * 2)}' -PolicyStore ActiveStore -Confirm:$false -ErrorAction Stop;'OK'}}"
                "catch{'ERR|'+$_.Exception.Message}", timeout=60)
    return ("OK" in out and "ERR|" not in out), "Limite removido."


# ---------------------------------------------------------------- drivers de rede
def net_drivers():
    """Drivers de placa de rede (Wi-Fi, cabo) que não são da Microsoft, com a idade deles."""
    script = ("@(Get-CimInstance Win32_PnPSignedDriver|?{$_.DeviceClass -eq 'NET' -and $_.DeviceName -and $_.DriverDate -and $_.Manufacturer -notmatch 'Microsoft'}|"
              "Select DeviceName,Manufacturer,DriverVersion,@{n='date';e={$_.DriverDate.ToString('yyyy-MM-dd')}})|ConvertTo-Json -Compress")
    out, seen = [], set()
    for d in _as_list(bk.ps(script, timeout=60)):
        if d.get("DeviceName") in seen or re.search(r"virtual|vpn|tunnel|miniport|tap-|vmware|hyper-v|bluetooth", d.get("DeviceName", ""), re.I):
            continue
        seen.add(d.get("DeviceName"))
        try:
            age = (time.time() - time.mktime(time.strptime(d["date"], "%Y-%m-%d"))) / (365.25 * 86400)
        except (ValueError, KeyError):
            age = 0
        d["age"] = round(age, 1)
        out.append(d)
    return sorted(out, key=lambda d: -d["age"])


def driver_updates():
    """Procura no Windows Update o que é driver (ou parece de rede). Só procura, não instala. Leva de 20 s a 1 min."""
    ups, err = system.pending_updates()
    pick = [u for u in ups if u.get("Driver") or re.search(r"wi-?fi|wireless|ethernet|network|realtek|intel\(r\).*(wi|lan)|qualcomm|atheros|mediatek|broadcom", u.get("Title", ""), re.I)]
    return {"updates": pick, "error": err, "total": len(ups)}


# ------------------------------------------------------------- comandos de reparo
def repair_renew():
    """Renova a conexão: solta o IP, pede outro e limpa o cache de nomes."""
    yield "▶ ipconfig /release  (a internet cai por um instante)"
    yield from health.stream_cmd(["ipconfig", "/release"])
    yield "▶ ipconfig /renew"
    yield from health.stream_cmd(["ipconfig", "/renew"])
    yield "▶ ipconfig /flushdns"
    yield from health.stream_cmd(["ipconfig", "/flushdns"])


def repair_reset():
    """Zera a pilha de rede do Windows. Precisa reiniciar o PC depois."""
    yield "▶ netsh int ip reset"
    yield from health.stream_cmd(["netsh", "int", "ip", "reset"])
    yield "▶ netsh winsock reset"
    yield from health.stream_cmd(["netsh", "winsock", "reset"])
    yield "✅ Pronto. REINICIE o PC para valer."


def repair_all():
    """Renova a conexão e depois zera a pilha de rede (os 5 comandos)."""
    yield from repair_renew()
    yield from repair_reset()
