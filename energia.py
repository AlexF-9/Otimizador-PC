import re
import subprocess
import winreg

CREATE_NO_WINDOW = 0x08000000
ALTO_DESEMPENHO = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
TRADUCOES = {
    "balanced": "Equilibrado", "high performance": "Alto desempenho",
    "power saver": "Poupança de energia", "ultimate performance": "Desempenho máximo",
}
DESCRICOES = {
    "381b4222-f694-41f0-9685-ff5bb260df2e": "Desempenho quando é preciso, poupa energia quando o PC está parado.",
    ALTO_DESEMPENHO: "Processador sempre pronto. Mais rápido a reagir, mas gasta mais energia.",
    "a1841308-3541-4fab-bc81-f71556f20b4a": "Reduz o desempenho para gastar menos energia.",
    "e9a42b02-d5df-448d-aa00-03f14749eb61": "O máximo de desempenho, sem nenhuma poupança.",
}


def _powercfg(*args):
    r = subprocess.run(["powercfg", *args], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", creationflags=CREATE_NO_WINDOW)
    return r.returncode == 0, (r.stdout or r.stderr).strip()


def _nome_registo(guid):
    # sem consola o powercfg troca o ™ por T, por isso lê-se do registo
    chave = rf"SYSTEM\CurrentControlSet\Control\Power\User\PowerSchemes\{guid}"
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, chave) as k:
            nome, _ = winreg.QueryValueEx(k, "FriendlyName")
            return None if str(nome).startswith("@") else str(nome)  # "@..." = texto de sistema
    except OSError:
        return None


def planos():
    _, out = _powercfg("/list")
    res = []
    for m in re.finditer(r"([0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})\s+\((.+?)\)\s*(\*)?\s*$", out, re.I | re.M):
        guid, nome, ativo = m.group(1).lower(), m.group(2).strip(), bool(m.group(3))
        nome = TRADUCOES.get(nome.lower()) or _nome_registo(guid) or nome
        res.append((guid, nome, ativo))
    return res


def plano_ativo():
    return next((n for _, n, a in planos() if a), "—")


def ativar(guid):
    return _powercfg("/setactive", guid)
