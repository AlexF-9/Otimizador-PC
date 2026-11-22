"""Modo Boost: fecha programas escolhidos antes de jogar e volta a abri-los no fim.

Fecha primeiro de forma educada (como carregar no X). Só força o fecho em programas que ficam
no tabuleiro do sistema e não têm documentos por guardar, ou quando o utilizador autoriza.
"""
import ctypes
import json
import os
import subprocess
import time
from ctypes import wintypes

import energia
import monitor

CREATE_NO_WINDOW = 0x08000000
WM_CLOSE = 0x0010
GW_OWNER = 4
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

PASTA = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "OtimizadorPC")
FICHEIRO_ESTADO = os.path.join(PASTA, "boost.json")
DESEMPENHO_MAXIMO = "e9a42b02-d5df-448d-aa00-03f14749eb61"

# exe -> (nome, categoria, ligado por defeito, pode ser forçado sem perder trabalho, argumentos para fechar bem)
CONHECIDOS = {
    "chrome.exe": ("Google Chrome", "Browser", True, False, None),
    "msedge.exe": ("Microsoft Edge", "Browser", True, False, None),
    "firefox.exe": ("Firefox", "Browser", True, False, None),
    "opera.exe": ("Opera", "Browser", True, False, None),
    "opera_gx.exe": ("Opera GX", "Browser", True, False, None),
    "brave.exe": ("Brave", "Browser", True, False, None),
    "onedrive.exe": ("OneDrive", "Sincronização", True, True, ["/shutdown"]),
    "dropbox.exe": ("Dropbox", "Sincronização", True, True, None),
    "googledrivefs.exe": ("Google Drive", "Sincronização", True, True, None),
    "ms-teams.exe": ("Microsoft Teams", "Comunicação", True, True, None),
    "slack.exe": ("Slack", "Comunicação", True, True, None),
    "whatsapp.exe": ("WhatsApp", "Comunicação", True, True, None),
    "telegram.exe": ("Telegram", "Comunicação", True, True, None),
    "discord.exe": ("Discord", "Comunicação", False, True, None),
    "spotify.exe": ("Spotify", "Música", False, True, None),
    "steam.exe": ("Steam", "Launcher", False, True, ["-shutdown"]),
    "epicgameslauncher.exe": ("Epic Games Launcher", "Launcher", True, True, None),
    "eadesktop.exe": ("EA app", "Launcher", True, True, None),
    "upc.exe": ("Ubisoft Connect", "Launcher", True, True, None),
    "battle.net.exe": ("Battle.net", "Launcher", False, True, None),
    "creative cloud.exe": ("Adobe Creative Cloud", "Outros", True, True, None),
}

# nunca se fecham, mesmo que tenham janela
PROTEGIDOS = {
    "explorer.exe", "msedgewebview2.exe", "python.exe", "pythonw.exe", "py.exe", "otimizadorpc.exe",
    "applicationframehost.exe", "textinputhost.exe", "systemsettings.exe", "shellexperiencehost.exe",
    "startmenuexperiencehost.exe", "searchhost.exe", "lockapp.exe", "taskmgr.exe", "conhost.exe",
    "windowsterminal.exe", "openconsole.exe", "dwm.exe", "csrss.exe", "winlogon.exe", "ctfmon.exe",
}

k32 = ctypes.windll.kernel32
u32 = ctypes.windll.user32
k32.OpenProcess.restype = wintypes.HANDLE
k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
k32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
k32.CloseHandle.argtypes = [wintypes.HANDLE]
k32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
_ENUM = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
u32.EnumWindows.argtypes = [_ENUM, wintypes.LPARAM]
u32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]


# --- processos e janelas ----------------------------------------------------

def caminho(pid):
    h = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return None
    try:
        buf = ctypes.create_unicode_buffer(1024)
        n = wintypes.DWORD(len(buf))
        return buf.value if k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n)) else None
    finally:
        k32.CloseHandle(h)


def janelas_visiveis():
    """pid -> janelas principais visíveis com título."""
    res = {}

    def cb(hwnd, _):
        if u32.IsWindowVisible(hwnd) and u32.GetWindowTextLengthW(hwnd) and not u32.GetWindow(hwnd, GW_OWNER):
            pid = wintypes.DWORD()
            u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            res.setdefault(pid.value, []).append(hwnd)
        return True

    u32.EnumWindows(_ENUM(cb), 0)
    return res


def _por_exe():
    """exe (minúsculas) -> {"nome": nome real, "pids": [...], "mem": bytes}."""
    res = {}
    for nome, pid, mem in monitor.processos():
        g = res.setdefault(nome.lower(), {"nome": nome, "pids": [], "mem": 0})
        g["pids"].append(pid)
        g["mem"] += mem
    return res


def _meu_arvore():
    """O próprio processo e o pai (o exe do PyInstaller arranca um processo filho)."""
    return {os.getpid(), os.getppid()}


def _do_windows(p):
    windir = (os.environ.get("WINDIR") or r"C:\Windows").lower()
    return bool(p) and p.lower().startswith(windir + "\\")


PASTAS_JOGOS = tuple(f"\\{p}\\" for p in (
    "steamapps", "epic games", "riot games", "ea games", r"ubisoft game launcher\games", r"gog galaxy\games", "xboxgames"))


def e_jogo(exe, p):
    """Nunca oferecer para fechar o próprio jogo."""
    p = (p or "").lower()
    return exe.endswith("-shipping.exe") or any(x in p for x in PASTAS_JOGOS)


def candidatos(selecao=None):
    """Programas que o Boost pode fechar: os conhecidos e outros programas abertos com janela."""
    selecao = None if selecao is None else {s.lower() for s in selecao}
    abertos = _por_exe()
    meus = _meu_arvore()
    res = []
    for exe, (nome, cat, defeito, _, _) in CONHECIDOS.items():
        g = abertos.get(exe)
        res.append({"exe": exe, "nome": nome, "categoria": cat, "conhecido": True,
                    "aberto": bool(g), "mem": g["mem"] if g else 0,
                    "ligado": defeito if selecao is None else exe in selecao})
    vistos = set()
    for pid, _ in janelas_visiveis().items():
        if pid in meus:
            continue
        exe = next((e for e, g in abertos.items() if pid in g["pids"]), None)
        if not exe or exe in CONHECIDOS or exe in PROTEGIDOS or exe in vistos:
            continue
        p = caminho(pid)
        if not p or _do_windows(p) or "\\windowsapps\\" in p.lower() or e_jogo(exe, p):
            continue
        vistos.add(exe)
        g = abertos[exe]
        res.append({"exe": exe, "nome": _nome_ficheiro(p, g["nome"]), "categoria": "Aberto agora", "conhecido": False,
                    "aberto": True, "mem": g["mem"], "ligado": bool(selecao) and exe in selecao})
    # abertos primeiro, depois por memória
    res.sort(key=lambda c: (not c["aberto"], not c["conhecido"], -c["mem"], c["nome"].lower()))
    return res


def _nome_ficheiro(p, padrao):
    """Nome do produto a partir da descrição do ficheiro; se falhar, o nome do exe sem extensão."""
    try:
        ver = ctypes.windll.version
        tam = ver.GetFileVersionInfoSizeW(p, None)
        if tam:
            buf = ctypes.create_string_buffer(tam)
            if ver.GetFileVersionInfoW(p, 0, tam, buf):
                ptr, n = ctypes.c_void_p(), wintypes.UINT()
                if ver.VerQueryValueW(buf, r"\VarFileInfo\Translation", ctypes.byref(ptr), ctypes.byref(n)) and n.value >= 4:
                    lang = ctypes.cast(ptr, ctypes.POINTER(wintypes.WORD * 2)).contents
                    for campo in ("FileDescription", "ProductName"):
                        q = rf"\StringFileInfo\{lang[0]:04x}{lang[1]:04x}\{campo}"
                        if ver.VerQueryValueW(buf, q, ctypes.byref(ptr), ctypes.byref(n)) and n.value > 1:
                            texto = ctypes.wstring_at(ptr, n.value - 1).strip()
                            if texto:
                                return texto
    except (OSError, AttributeError):
        pass
    return os.path.splitext(padrao)[0]


# --- fechar -----------------------------------------------------------------

def _vivos(pids):
    vivos = []
    for pid in pids:
        h = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if h:
            codigo = wintypes.DWORD()
            k32.GetExitCodeProcess(h, ctypes.byref(codigo))
            k32.CloseHandle(h)
            if codigo.value == 259:  # STILL_ACTIVE
                vivos.append(pid)
    return vivos


def fechar_educado(pids, args=None, exe_caminho=None):
    """Pede às janelas para fecharem (como carregar no X). Não espera."""
    if args and exe_caminho:
        try:
            subprocess.Popen([exe_caminho, *args], creationflags=CREATE_NO_WINDOW)
            return
        except OSError:
            pass
    jan = janelas_visiveis()
    for pid in pids:
        for hwnd in jan.get(pid, []):
            u32.PostMessageW(hwnd, WM_CLOSE, 0, 0)


def forcar(exe):
    r = subprocess.run(["taskkill", "/IM", exe, "/T", "/F"], capture_output=True, text=True,
                       encoding="oem", errors="replace", creationflags=CREATE_NO_WINDOW)
    return r.returncode == 0


def esperar(grupos, segundos):
    """grupos: exe -> pids. Devolve o conjunto de exe que ainda têm processos vivos."""
    fim = time.monotonic() + segundos
    restantes = set(grupos)
    while restantes and time.monotonic() < fim:
        time.sleep(0.25)
        restantes = {e for e in restantes if _vivos(grupos[e])}
    return restantes


# --- estado guardado --------------------------------------------------------

def ler_estado():
    try:
        with open(FICHEIRO_ESTADO, encoding="utf-8") as f:
            d = json.load(f)
            return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def guardar_estado(d):
    os.makedirs(PASTA, exist_ok=True)
    tmp = FICHEIRO_ESTADO + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, FICHEIRO_ESTADO)


# --- ativar / desativar -----------------------------------------------------

def ativar(selecao, plano_alto, progresso=lambda i, n, nome: None):
    """Fecha os programas selecionados que estão abertos. Devolve o resultado e guarda o estado."""
    selecao = {s.lower() for s in selecao} - PROTEGIDOS
    abertos = _por_exe()
    meus = _meu_arvore()
    alvos = {}
    for exe in selecao:
        g = abertos.get(exe)
        if not g:
            continue
        pids = [p for p in g["pids"] if p not in meus]
        p = next((c for c in map(caminho, pids) if c), None)
        if not pids or _do_windows(p):
            continue
        nome = CONHECIDOS[exe][0] if exe in CONHECIDOS else (_nome_ficheiro(p, g["nome"]) if p else g["nome"])
        alvos[exe] = {"pids": pids, "mem": g["mem"], "caminho": p, "nome": nome}

    for i, (exe, a) in enumerate(alvos.items()):
        progresso(i, len(alvos), a["nome"])
        info = CONHECIDOS.get(exe)
        fechar_educado(a["pids"], info[4] if info else None, a["caminho"])

    restantes = esperar({e: a["pids"] for e, a in alvos.items()}, 6)
    # programas de tabuleiro sem documentos: pode-se forçar sem perder trabalho
    for exe in [e for e in restantes if CONHECIDOS.get(e, (0, 0, 0, False))[3]]:
        forcar(exe)
    restantes = esperar({e: alvos[e]["pids"] for e in restantes}, 3)

    fechados = [{"exe": e, "nome": a["nome"], "caminho": a["caminho"], "mem": a["mem"]}
                for e, a in alvos.items() if e not in restantes]
    resistentes = [{"exe": e, "nome": alvos[e]["nome"], "caminho": alvos[e]["caminho"], "mem": alvos[e]["mem"]}
                   for e in restantes]

    plano = _plano_boost() if plano_alto else None
    estado = {"ativo": True, "desde": time.time(), "fechados": fechados, "selecao": sorted(selecao),
              "plano_alto": bool(plano_alto), "plano_anterior": None, "plano_boost": None}
    if plano:
        anterior = next((g for g, _, a in energia.planos() if a), None)
        if anterior and anterior != plano[0]:
            ok, _ = energia.ativar(plano[0])
            if ok:
                estado["plano_anterior"], estado["plano_boost"] = anterior, plano[1]
    guardar_estado(estado)
    return {"fechados": fechados, "resistentes": resistentes, "plano": estado["plano_boost"],
            "sem_plano_alto": bool(plano_alto) and not plano}


def forcar_resistentes(lista):
    """O utilizador aceitou forçar o fecho destes programas."""
    estado = ler_estado()
    if not estado.get("ativo"):
        return {"fechados": [], "falhas": [x.get("nome") for x in lista]}
    fechados, falhas = [], []
    for x in lista:
        exe = (x.get("exe") or "").lower()
        if not exe or exe in PROTEGIDOS:
            continue
        forcar(exe)
        g = _por_exe().get(exe)
        if g and _vivos(g["pids"]):
            falhas.append(x.get("nome") or exe)
        else:
            fechados.append({"exe": exe, "nome": x.get("nome") or exe, "caminho": x.get("caminho"), "mem": x.get("mem") or 0})
    estado["fechados"] = estado.get("fechados", []) + fechados
    guardar_estado(estado)
    return {"fechados": fechados, "falhas": falhas}


def _plano_boost():
    planos = {g: n for g, n, _ in energia.planos()}
    for guid in (energia.ALTO_DESEMPENHO, DESEMPENHO_MAXIMO):
        if guid in planos:
            return guid, planos[guid]
    return None


def abrir_sem_admin(caminho_exe):
    """Abre através do Explorador para o programa não herdar os privilégios de administrador da app."""
    subprocess.Popen(["explorer.exe", caminho_exe], creationflags=CREATE_NO_WINDOW)


def desativar():
    estado = ler_estado()
    if not estado.get("ativo"):
        return {"reabertos": [], "falhas": [], "plano": None}
    abertos = _por_exe()
    reabertos, falhas = [], []
    for x in estado.get("fechados", []):
        if x["exe"] in abertos:  # o utilizador já o voltou a abrir
            continue
        c = x.get("caminho")
        try:
            if not c or not os.path.isfile(c):
                raise OSError
            abrir_sem_admin(c)
            reabertos.append(x["nome"])
        except OSError:
            falhas.append(x["nome"])
    plano = None
    anterior = estado.get("plano_anterior")
    if anterior and anterior in {g for g, _, _ in energia.planos()}:
        ok, _ = energia.ativar(anterior)
        if ok:
            plano = energia.plano_ativo()
    guardar_estado({"ativo": False, "selecao": estado.get("selecao", []), "plano_alto": estado.get("plano_alto", True)})
    return {"reabertos": reabertos, "falhas": falhas, "plano": plano}


def guardar_preferencias(selecao, plano_alto):
    estado = ler_estado()
    if estado.get("ativo"):
        return
    estado.update({"selecao": sorted({s.lower() for s in selecao}), "plano_alto": bool(plano_alto)})
    guardar_estado(estado)
