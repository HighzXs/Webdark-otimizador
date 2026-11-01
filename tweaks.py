"""Ajustes de desempenho/privacidade do usuário (HKCU, sem admin, todos reversíveis)."""
import ctypes
import winreg
from dataclasses import dataclass, field

HKCU = winreg.HKEY_CURRENT_USER
CDM = r"Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"


@dataclass
class Tweak:
    key: str
    name: str
    desc: str
    regs: list = field(default_factory=list)   # (caminho, valor, otimizado, padrão)
    getter: object = None
    setter: object = None

    def is_on(self):
        """True se a otimização está aplicada."""
        if self.getter:
            return self.getter()
        return all(_read(p, n, d) == o for p, n, o, d in self.regs)

    def apply(self, on):
        if self.setter:
            self.setter(on)
        else:
            for p, n, o, d in self.regs:
                _write(p, n, o if on else d)
        ctypes.windll.user32.SendMessageTimeoutW(0xFFFF, 0x1A, 0, "ImmersiveColorSet", 2, 2000, None)


def _read(path, name, default):
    try:
        with winreg.OpenKey(HKCU, path) as k:
            return winreg.QueryValueEx(k, name)[0]
    except OSError:
        return default


def _write(path, name, value):
    with winreg.CreateKeyEx(HKCU, path, 0, winreg.KEY_SET_VALUE) as k:
        winreg.SetValueEx(k, name, 0, winreg.REG_DWORD, int(value))


class _AnimInfo(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("iMinAnimate", ctypes.c_int)]


def _anim_off():
    i = _AnimInfo(ctypes.sizeof(_AnimInfo), 0)
    ctypes.windll.user32.SystemParametersInfoW(0x0048, i.cbSize, ctypes.byref(i), 0)
    return i.iMinAnimate == 0


def _set_anim(off):
    i = _AnimInfo(ctypes.sizeof(_AnimInfo), 0 if off else 1)
    ctypes.windll.user32.SystemParametersInfoW(0x0049, i.cbSize, ctypes.byref(i), 3)


def make_tweaks():
    cdm_vals = ["SubscribedContent-338388Enabled", "SubscribedContent-338389Enabled", "SubscribedContent-353694Enabled",
                "SubscribedContent-353696Enabled", "SubscribedContent-310093Enabled", "SystemPaneSuggestionsEnabled",
                "SilentInstalledAppsEnabled", "ContentDeliveryAllowed", "OemPreInstalledAppsEnabled",
                "PreInstalledAppsEnabled", "PreInstalledAppsEverEnabled"]
    return [
        Tweak("sensor", "Limpeza automática de lixo (Sensor de Armazenamento)",
              "O próprio Windows apaga temporários e esvazia a lixeira de tempos em tempos.",
              [(r"Software\Microsoft\Windows\CurrentVersion\StorageSense\Parameters\StoragePolicy", "01", 1, 0)]),
        Tweak("ads", "Parar propagandas e apps patrocinados do Windows",
              "Tira sugestões do menu Iniciar e impede o Windows de reinstalar Candy Crush e cia.",
              [(CDM, v, 0, 1) for v in cdm_vals]),
        Tweak("bg", "Impedir apps de rodar escondidos em segundo plano",
              "Economiza memória e bateria. Apps abertos por você continuam normais.",
              [(r"Software\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications", "GlobalUserDisabled", 1, 0)]),
        Tweak("gamedvr", "Desligar gravação de jogos em segundo plano (Game Bar)",
              "Deixa os jogos mais leves. Você ainda pode abrir a Game Bar com Win+G.",
              [(r"System\GameConfigStore", "GameDVR_Enabled", 0, 1),
               (r"Software\Microsoft\Windows\CurrentVersion\GameDVR", "AppCaptureEnabled", 0, 1)]),
        Tweak("transp", "Desligar efeitos de transparência",
              "Menos trabalho para a placa de vídeo. Ajuda em PC fraco.",
              [(r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", "EnableTransparency", 0, 1)]),
        Tweak("anim", "Desligar animações de janelas",
              "Janelas abrem e fecham na hora, sem efeito. Dá sensação de PC mais rápido.",
              getter=_anim_off, setter=_set_anim),
        Tweak("adid", "Desligar ID de propaganda personalizada",
              "O Windows para de usar seu perfil para escolher anúncios.",
              [(r"Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo", "Enabled", 0, 1)]),
        Tweak("ext", "Mostrar a extensão dos arquivos (.exe, .jpg, .pdf…)",
              "Ajuda a perceber vírus disfarçado de foto. Reabra as pastas para ver.",
              [(r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "HideFileExt", 0, 1)]),
    ]
