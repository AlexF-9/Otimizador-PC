import os
import struct
import time
import winreg
from dataclasses import dataclass

RUN = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN32 = r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run"
APROVADO = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved"
HKCU, HKLM = winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE
LER = winreg.KEY_READ | winreg.KEY_WOW64_64KEY


@dataclass
class Programa:
    nome: str
    comando: str
    origem: str
    raiz: int
    sub: str
    ativo: bool = True


def _aprovado(raiz, sub, nome):
    try:
        with winreg.OpenKey(raiz, f"{APROVADO}\\{sub}", 0, LER) as k:
            dados, _ = winreg.QueryValueEx(k, nome)
            return not dados or dados[0] & 1 == 0  # 02/06 = ligado, 03/07 = desligado
    except OSError:
        return True


def listar():
    progs = []
    for raiz, chave, sub, origem in ((HKCU, RUN, "Run", "Utilizador"),
                                     (HKLM, RUN, "Run", "Todos os utilizadores"),
                                     (HKLM, RUN32, "Run32", "Todos (32 bits)")):
        try:
            with winreg.OpenKey(raiz, chave, 0, LER) as k:
                i = 0
                while True:
                    try:
                        nome, valor, _ = winreg.EnumValue(k, i)
                    except OSError:
                        break
                    i += 1
                    if nome:
                        progs.append(Programa(nome, str(valor), origem, raiz, sub))
        except OSError:
            pass
    pastas = ((HKCU, os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup"),
               "Pasta Arranque"),
              (HKLM, os.path.join(os.environ.get("PROGRAMDATA", ""), r"Microsoft\Windows\Start Menu\Programs\StartUp"),
               "Pasta Arranque (todos)"))
    for raiz, pasta, origem in pastas:
        if os.path.isdir(pasta):
            for f in os.listdir(pasta):
                if f.lower() != "desktop.ini":
                    progs.append(Programa(f, os.path.join(pasta, f), origem, raiz, "StartupFolder"))
    for p in progs:
        p.ativo = _aprovado(p.raiz, p.sub, p.nome)
    return sorted(progs, key=lambda p: p.nome.lower())


def definir(prog, ativo):
    if ativo:
        dados = b"\x02" + b"\x00" * 11
    else:
        ft = int((time.time() + 11644473600) * 10_000_000)  # data em formato FILETIME
        dados = b"\x03\x00\x00\x00" + struct.pack("<Q", ft)
    acesso = winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY
    with winreg.CreateKeyEx(prog.raiz, f"{APROVADO}\\{prog.sub}", 0, acesso) as k:
        winreg.SetValueEx(k, prog.nome, 0, winreg.REG_BINARY, dados)
    prog.ativo = ativo


def nome_bonito(prog):
    n = prog.nome
    return n[:-4] if n.lower().endswith((".lnk", ".url", ".bat", ".exe")) else n
