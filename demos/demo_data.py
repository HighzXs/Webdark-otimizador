"""Dados falsos iguais nos 3 demos, para a comparação ser justa."""
import random

RISK = {
    "ok": ("SEGURO", "Cache ou arquivo temporário. O programa recria sozinho."),
    "care": ("CUIDADO", "Arquivo pessoal. Só você sabe se ainda precisa."),
    "danger": ("NÃO APAGUE", "Parte de programa instalado. Desinstale pela aba Programas."),
}
FOLDERS = [
    r"C:\Users\User\AppData\Local\Temp", r"C:\Users\User\AppData\Local\Google\Chrome\User Data\Default\Cache",
    r"C:\Users\User\Videos", r"C:\Users\User\Downloads", r"C:\Program Files\Adobe\Reader", r"C:\Windows\System32",
    r"C:\Users\User\AppData\Roaming\Discord\Cache", r"C:\Users\User\Documents\Projetos",
]
FILES = ["f_0004e1", "instalador.exe", "ferias_2024.mp4", "cache.db", "shader.bin", "relatorio.pdf", "setup.msi",
         "kernel32.dll", "thumbs.db", "update.cab", "dump.dmp", "foto_0231.jpg"]


def make_rows(n=300):
    rng = random.Random(7)
    rows = []
    for i in range(n):
        level = rng.choices(["ok", "care", "danger"], [5, 4, 2])[0]
        label, reason = RISK[level]
        path = rng.choice(FOLDERS) + "\\" + rng.choice(FILES).replace("_", f"_{i:03d}_", 1)
        rows.append({"level": level, "label": label, "path": path, "reason": reason,
                     "size": rng.randint(2, 4000) * 1024 * 1024 // rng.choice([1, 4, 16])})
    rows.sort(key=lambda r: -r["size"])
    return rows


SETTINGS = [
    ("Limpeza automática de lixo", "O Windows apaga temporários e esvazia a lixeira de tempos em tempos.", True),
    ("Parar propagandas do Windows", "Tira sugestões do menu Iniciar e apps patrocinados.", False),
    ("Impedir apps em segundo plano", "Economiza memória e bateria. Apps abertos por você continuam normais.", False),
    ("Desligar gravação de jogos", "Deixa os jogos mais leves. Win+G continua funcionando.", True),
    ("Desligar transparência do Windows", "Menos trabalho para a placa de vídeo.", False),
    ("Desligar animações de janelas", "Janelas abrem e fecham na hora.", False),
    ("Desligar ID de propaganda", "O Windows para de usar seu perfil para escolher anúncios.", True),
    ("Mostrar extensão dos arquivos", "Ajuda a perceber vírus disfarçado de foto.", True),
    ("Reduzir telemetria", "DiagTrack e dmwappushservice em Manual.", False),
    ("Desligar SysMain (Superfetch)", "Útil em SSD. Em HD pode deixar o PC mais lento.", False),
    ("Pausar indexação do Windows Search", "A busca do menu Iniciar fica mais lenta.", False),
    ("Modo segundo plano", "Fecha na bandeja e confere o PC em silêncio.", False),
    ("Avisar de atualizações", "Mostra um aviso quando sair versão nova do app.", True),
    ("Criar ponto de restauração antes de mexer", "Rede de segurança antes de cada ajuste de sistema.", True),
    ("Vigia de temperatura", "Baixa o clock sozinho se o PC esquentar demais.", False),
    ("Apitar ao esquentar", "Toca um som quando a CPU passar do aviso.", False),
]
ACCENTS = ["#8b5cf6", "#4fd1e6", "#b043d1", "#22c55e", "#f59e0b", "#ef4444"]


def fmt_size(n):
    n = float(n)
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024 or u == "GB":
            return f"{n:.0f} {u}" if u == "B" else f"{n:.1f} {u}"
        n /= 1024
