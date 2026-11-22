"""Informação de hardware e definições do Windows. Só lê, nunca altera nada."""
import base64
import ctypes
import json
import re
import subprocess
import winreg
from ctypes import wintypes

CREATE_NO_WINDOW = 0x08000000
HKLM, HKCU = winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER

_PS = r"""
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$ErrorActionPreference = 'SilentlyContinue'
$r = [ordered]@{}
$r.cpu = Get-CimInstance Win32_Processor | Select-Object -First 1 Name, NumberOfCores, NumberOfLogicalProcessors, MaxClockSpeed
$r.ram = @(Get-CimInstance Win32_PhysicalMemory | Select-Object Capacity, Speed, ConfiguredClockSpeed, SMBIOSMemoryType, Manufacturer, PartNumber, DeviceLocator)
$r.gpu = @(Get-CimInstance Win32_VideoController | Select-Object Name, DriverVersion, CurrentHorizontalResolution, CurrentVerticalResolution, CurrentRefreshRate)
$r.placa = Get-CimInstance Win32_BaseBoard | Select-Object -First 1 Manufacturer, Product
$r.so = Get-CimInstance Win32_OperatingSystem | Select-Object -First 1 Caption, Version, BuildNumber
$r.discos = @(Get-PhysicalDisk | ForEach-Object {
  $c = $_ | Get-StorageReliabilityCounter
  [ordered]@{ nome = $_.FriendlyName; tipo = [string]$_.MediaType; bus = [string]$_.BusType
              saude = [string]$_.HealthStatus; tamanho = $_.Size
              temp = $c.Temperature; desgaste = $c.Wear; horas = $c.PowerOnHours }
})
$r | ConvertTo-Json -Depth 4 -Compress
"""

TIPOS_RAM = {20: "DDR", 21: "DDR2", 24: "DDR3", 26: "DDR4", 34: "DDR5"}
# velocidade "de fábrica" sem perfil EXPO/XMP (o que a RAM usa se o perfil estiver desligado)
JEDEC = {"DDR4": 2666, "DDR5": 4800}


def _powershell():
    cod = base64.b64encode(_PS.encode("utf-16-le")).decode()
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-EncodedCommand", cod],
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           creationflags=CREATE_NO_WINDOW, timeout=60)
        return json.loads(r.stdout.strip() or "{}")
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return {}


def _lista(v):
    return v if isinstance(v, list) else ([v] if v else [])


def _reg(raiz, chave, valor, padrao=None):
    try:
        with winreg.OpenKey(raiz, chave) as k:
            return winreg.QueryValueEx(k, valor)[0]
    except OSError:
        return padrao


def vram_por_gpu():
    """O Win32_VideoController limita a VRAM a 4 GB, por isso lê-se do registo do controlador."""
    base = r"SYSTEM\ControlSet001\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
    res = {}
    try:
        with winreg.OpenKey(HKLM, base) as k:
            i = 0
            while True:
                try:
                    sub = winreg.EnumKey(k, i)
                except OSError:
                    break
                i += 1
                if not sub.isdigit():
                    continue
                nome = _reg(HKLM, rf"{base}\{sub}", "DriverDesc")
                mem = _reg(HKLM, rf"{base}\{sub}", "HardwareInformation.qwMemorySize")
                if mem is None:
                    m = _reg(HKLM, rf"{base}\{sub}", "HardwareInformation.MemorySize")
                    mem = int.from_bytes(m, "little") if isinstance(m, bytes) else m
                if nome and mem:
                    res[nome] = int(mem)
    except OSError:
        pass
    return res


class _DEVMODEW(ctypes.Structure):
    _fields_ = [("dmDeviceName", wintypes.WCHAR * 32), ("dmSpecVersion", wintypes.WORD),
                ("dmDriverVersion", wintypes.WORD), ("dmSize", wintypes.WORD), ("dmDriverExtra", wintypes.WORD),
                ("dmFields", wintypes.DWORD), ("dmPositionX", ctypes.c_long), ("dmPositionY", ctypes.c_long),
                ("dmDisplayOrientation", wintypes.DWORD), ("dmDisplayFixedOutput", wintypes.DWORD),
                ("dmColor", ctypes.c_short), ("dmDuplex", ctypes.c_short), ("dmYResolution", ctypes.c_short),
                ("dmTTOption", ctypes.c_short), ("dmCollate", ctypes.c_short), ("dmFormName", wintypes.WCHAR * 32),
                ("dmLogPixels", wintypes.WORD), ("dmBitsPerPel", wintypes.DWORD), ("dmPelsWidth", wintypes.DWORD),
                ("dmPelsHeight", wintypes.DWORD), ("dmDisplayFlags", wintypes.DWORD),
                ("dmDisplayFrequency", wintypes.DWORD), ("dmICMMethod", wintypes.DWORD),
                ("dmICMIntent", wintypes.DWORD), ("dmMediaType", wintypes.DWORD), ("dmDitherType", wintypes.DWORD),
                ("dmReserved1", wintypes.DWORD), ("dmReserved2", wintypes.DWORD),
                ("dmPanningWidth", wintypes.DWORD), ("dmPanningHeight", wintypes.DWORD)]


def ecra():
    """Resolução e taxa de atualização do ecrã principal, e a taxa máxima que ele aceita."""
    enum = ctypes.windll.user32.EnumDisplaySettingsW
    atual = _DEVMODEW()
    atual.dmSize = ctypes.sizeof(_DEVMODEW)
    if not enum(None, -1, ctypes.byref(atual)):  # ENUM_CURRENT_SETTINGS
        return None
    maximo, i, m = atual.dmDisplayFrequency, 0, _DEVMODEW()
    m.dmSize = ctypes.sizeof(_DEVMODEW)
    while enum(None, i, ctypes.byref(m)):
        if m.dmPelsWidth == atual.dmPelsWidth and m.dmPelsHeight == atual.dmPelsHeight:
            maximo = max(maximo, m.dmDisplayFrequency)
        i += 1
    return {"largura": atual.dmPelsWidth, "altura": atual.dmPelsHeight,
            "hz": atual.dmDisplayFrequency, "hz_max": maximo}


def tempo_ligado():
    return ctypes.windll.kernel32.GetTickCount64() // 1000


def modo_jogo():
    v = _reg(HKCU, r"Software\Microsoft\GameBar", "AutoGameModeEnabled")
    return v is None or bool(v)  # ligado por defeito no Windows 10/11


def agendamento_gpu():
    v = _reg(HKLM, r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers", "HwSchMode")
    return {2: True, 1: False}.get(v)  # None = a placa ou o driver não suportam


def _velocidade_nominal(modulos):
    """Procura a velocidade anunciada no código do módulo (ex.: F5-6000J3038F16G, CMK32GX4M2E3200C16)."""
    for m in modulos:
        for n in re.findall(r"(?<!\d)(\d{4})(?!\d)", m.get("PartNumber") or ""):
            if 2400 <= int(n) <= 9000 and int(n) % 100 in (0, 33, 66):
                return int(n)
    return None


def _ram(modulos):
    if not modulos:
        return None
    tipo = TIPOS_RAM.get(modulos[0].get("SMBIOSMemoryType"))
    atual = max((m.get("ConfiguredClockSpeed") or 0) for m in modulos) or None
    suportada = max((m.get("Speed") or 0) for m in modulos) or None
    return {
        "modulos": [{"capacidade": m.get("Capacity") or 0,
                     "fabricante": "" if (m.get("Manufacturer") or "").strip().lower() in ("unknown", "undefined")
                     else (m.get("Manufacturer") or "").strip(),
                     "codigo": (m.get("PartNumber") or "").strip(), "ranhura": m.get("DeviceLocator") or "",
                     "velocidade": m.get("ConfiguredClockSpeed")} for m in modulos],
        "total": sum(m.get("Capacity") or 0 for m in modulos),
        "tipo": tipo, "velocidade": atual, "suportada": suportada,
        "nominal": _velocidade_nominal(modulos),
    }


def dicas(info):
    """Recomendações a partir do que foi detetado. Cada dica: nivel (ok/aviso/info), titulo, texto."""
    res = []
    ram = info.get("ram")
    if ram and ram["velocidade"]:
        nominal, atual, base = ram["nominal"], ram["velocidade"], JEDEC.get(ram["tipo"])
        if nominal and nominal > atual + 150:
            res.append(("aviso", "A RAM está abaixo da velocidade anunciada",
                        f"Os módulos são de {nominal} MT/s mas estão a {atual} MT/s. Ative o perfil de memória "
                        "na BIOS (chama-se XMP, DOCP ou EXPO, conforme a marca da placa). "
                        "Em jogos pode dar 10 a 20% mais FPS."))
        elif base and atual <= base:
            res.append(("aviso", "O perfil EXPO/XMP parece estar desligado",
                        f"A RAM {ram['tipo']} está a {atual} MT/s, a velocidade base. Se os módulos forem mais "
                        "rápidos, ative o EXPO/XMP na BIOS."))
        else:
            res.append(("ok", "RAM à velocidade certa", f"{ram['tipo'] or 'RAM'} a {atual} MT/s."))
        if len(ram["modulos"]) == 1:
            res.append(("aviso", "Só tem um módulo de RAM",
                        "Com um módulo a memória funciona em single channel. Dois módulos iguais "
                        "(dual channel) dão bastante mais desempenho em jogos."))
    e = info.get("ecra")
    if e and e["hz_max"] > e["hz"] + 1:
        res.append(("aviso", f"O ecrã está a {e['hz']} Hz, mas aceita {e['hz_max']} Hz",
                    "Mude em Definições > Sistema > Ecrã > Ecrã avançado > Taxa de atualização."))
    elif e:
        res.append(("ok", "Taxa de atualização no máximo", f"{e['hz']} Hz a {e['largura']}x{e['altura']}."))
    if not info.get("modo_jogo"):
        res.append(("aviso", "O Modo de Jogo está desligado",
                    "Ligue-o em Definições > Jogos > Modo de Jogo. Dá prioridade ao jogo que está aberto."))
    if info.get("agendamento_gpu") is False:
        res.append(("info", "Agendamento de GPU acelerado por hardware desligado",
                    "Pode ligá-lo em Definições > Sistema > Ecrã > Gráficos. Ajuda em algumas placas recentes "
                    "e é necessário para a Geração de Frames da NVIDIA."))
    for d in info.get("discos_fisicos", []):
        if d["saude"] and d["saude"] not in ("Healthy", "0"):
            res.append(("aviso", f"O disco {d['nome']} reporta problemas",
                        f"Estado: {d['saude']}. Faça cópia de segurança dos ficheiros importantes."))
        if d.get("desgaste") and d["desgaste"] >= 80:
            res.append(("aviso", f"O SSD {d['nome']} está gasto", f"Desgaste de {d['desgaste']}%."))
    dias = info.get("ligado_segundos", 0) / 86400
    if dias >= 7:
        res.append(("info", f"O PC está ligado há {int(dias)} dias",
                    "Reiniciar de vez em quando liberta memória e acaba atualizações pendentes."))
    return [{"nivel": n, "titulo": t, "texto": x} for n, t, x in res]


def informacao():
    d = _powershell()
    vram = vram_por_gpu()
    gpus = []
    for g in _lista(d.get("gpu")):
        nome = (g.get("Name") or "").strip()
        if not nome or "basic display" in nome.lower() or "virtual" in nome.lower():
            continue
        gpus.append({"nome": nome, "driver": g.get("DriverVersion") or "", "vram": vram.get(nome)})
    cpu = d.get("cpu") or {}
    info = {
        "cpu": {"nome": (cpu.get("Name") or "").strip(), "nucleos": cpu.get("NumberOfCores"),
                "threads": cpu.get("NumberOfLogicalProcessors"), "mhz": cpu.get("MaxClockSpeed")},
        "gpus": gpus,
        "ram": _ram(_lista(d.get("ram"))),
        "placa": " ".join(x for x in ((d.get("placa") or {}).get("Manufacturer"), (d.get("placa") or {}).get("Product")) if x),
        "so": (d.get("so") or {}).get("Caption", "").replace("Microsoft ", ""),
        "build": (d.get("so") or {}).get("BuildNumber", ""),
        "ecra": ecra(),
        "modo_jogo": modo_jogo(),
        "agendamento_gpu": agendamento_gpu(),
        "ligado_segundos": tempo_ligado(),
        "discos_fisicos": [{
            "nome": (x.get("nome") or "").strip(), "tipo": x.get("tipo") or "", "bus": x.get("bus") or "",
            "saude": x.get("saude") or "", "tamanho": x.get("tamanho") or 0,
            "temp": x.get("temp") or None, "desgaste": x.get("desgaste"), "horas": x.get("horas"),
        } for x in _lista(d.get("discos"))],
    }
    info["dicas"] = dicas(info)
    return info
