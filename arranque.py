import os
import struct
import time
import tkinter as tk
import winreg
from dataclasses import dataclass
from tkinter import messagebox

import tema as t

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


class Arranque(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=t.BG)
        t.cabecalho(self, "Programas de arranque",
                    "Desligue o que não precisa de abrir com o Windows. Nada é apagado e pode voltar a ligar.")
        topo = t.Cartao(self, pad=20)
        topo.pack(fill="x", padx=28, pady=(0, 14))
        self.lbl_resumo = tk.Label(topo, text="—", font=t.fonte(20, "bold"), bg=t.CARTAO, fg=t.TEXTO)
        self.lbl_resumo.pack(side="left")
        self.lbl_sub = tk.Label(topo, text="", font=t.fonte(10), bg=t.CARTAO, fg=t.SUAVE)
        self.lbl_sub.pack(side="left", padx=12, pady=(8, 0))
        t.Botao(topo, "Atualizar", self.carregar, tipo="secundario").pack(side="right")

        cartao = t.Cartao(self, pad=0)
        cartao.pack(fill="both", expand=True, padx=28, pady=(0, 24))
        self.lista = t.Rolavel(cartao)
        self.lista.pack(fill="both", expand=True)
        self.progs = []
        self.carregar()

    def ao_mostrar(self):
        self.carregar()

    def carregar(self):
        for w in self.lista.interior.winfo_children():
            w.destroy()
        self.progs = listar()
        if not self.progs:
            tk.Label(self.lista.interior, text="Nenhum programa de arranque encontrado.", font=t.fonte(10),
                     bg=t.CARTAO, fg=t.SUAVE, pady=30).pack()
        for i, p in enumerate(self.progs):
            if i:
                tk.Frame(self.lista.interior, bg=t.BORDA, height=1).pack(fill="x")
            linha = tk.Frame(self.lista.interior, bg=t.CARTAO, padx=18, pady=8)
            linha.pack(fill="x")
            v = tk.BooleanVar(value=p.ativo)
            tog = t.Toggle(linha, v)
            tog.comando = lambda p=p, v=v, tog=tog: self._alternar(p, v, tog)
            tog.pack(side="left")
            txt = tk.Frame(linha, bg=t.CARTAO)
            txt.pack(side="left", padx=14, fill="x", expand=True)
            tk.Label(txt, text=nome_bonito(p), font=t.fonte(10, "bold"), bg=t.CARTAO, fg=t.TEXTO,
                     anchor="w").pack(fill="x")
            cmd = p.comando if len(p.comando) <= 90 else p.comando[:87] + "…"
            tk.Label(txt, text=cmd, font=t.fonte(8), bg=t.CARTAO, fg=t.SUAVE, anchor="w").pack(fill="x")
            tk.Label(linha, text=p.origem, font=t.fonte(8, "bold"), bg=t.CARTAO2, fg=t.SUAVE,
                     padx=8, pady=3).pack(side="right")
        self._resumo()

    def _resumo(self):
        ativos = sum(p.ativo for p in self.progs)
        self.lbl_resumo.config(text=f"{ativos} ativos")
        self.lbl_sub.config(text=f"de {len(self.progs)} programas que podem abrir com o Windows")

    def _alternar(self, prog, var, tog):
        try:
            definir(prog, var.get())
        except PermissionError:
            var.set(prog.ativo)
            tog.redesenhar()
            messagebox.showwarning("Precisa de administrador",
                                   f"'{nome_bonito(prog)}' está configurado para todos os utilizadores.\n"
                                   "Abra o Otimizador como administrador para o alterar.")
        except OSError as e:
            var.set(prog.ativo)
            tog.redesenhar()
            messagebox.showerror("Erro", str(e))
        self._resumo()
