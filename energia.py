import re
import subprocess
import tkinter as tk
import winreg
from tkinter import messagebox

import tema as t

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


class Energia(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=t.BG)
        t.cabecalho(self, "Plano de energia",
                    "Para jogos e trabalho pesado, use um plano de alto desempenho.")
        self.cartao = t.Cartao(self, pad=0)
        self.cartao.pack(fill="x", padx=28)
        self.extra = tk.Frame(self, bg=t.BG)
        self.extra.pack(fill="x", padx=28, pady=14)
        self.carregar()

    def ao_mostrar(self):
        self.carregar()

    def carregar(self):
        for w in (*self.cartao.winfo_children(), *self.extra.winfo_children()):
            w.destroy()
        lista = planos()
        for i, (guid, nome, ativo) in enumerate(lista):
            if i:
                tk.Frame(self.cartao, bg=t.BORDA, height=1).pack(fill="x")
            linha = tk.Frame(self.cartao, bg=t.CARTAO, padx=18, pady=12)
            linha.pack(fill="x")
            ponto = tk.Canvas(linha, width=14, height=14, bg=t.CARTAO, highlightthickness=0)
            ponto.create_oval(2, 2, 12, 12, fill=t.VERDE if ativo else t.BORDA, outline="")
            ponto.pack(side="left")
            txt = tk.Frame(linha, bg=t.CARTAO)
            txt.pack(side="left", padx=14, fill="x", expand=True)
            tk.Label(txt, text=nome, font=t.fonte(11, "bold"), bg=t.CARTAO, fg=t.TEXTO, anchor="w").pack(fill="x")
            desc = DESCRICOES.get(guid, "Plano criado pelo fabricante ou por si.")
            tk.Label(txt, text=desc, font=t.fonte(9), bg=t.CARTAO, fg=t.SUAVE, anchor="w").pack(fill="x")
            if ativo:
                tk.Label(linha, text="Ativo", font=t.fonte(9, "bold"), bg=t.CARTAO, fg=t.VERDE).pack(side="right")
            else:
                t.Botao(linha, "Ativar", lambda g=guid: self._ativar(g), tipo="secundario").pack(side="right")
        if not any(g == ALTO_DESEMPENHO for g, _, _ in lista):
            tk.Label(self.extra, text="O plano Alto desempenho está escondido neste PC.", font=t.fonte(9),
                     bg=t.BG, fg=t.SUAVE).pack(side="left")
            t.Botao(self.extra, "Adicionar Alto desempenho", self._adicionar, tipo="secundario").pack(side="right")

    def _ativar(self, guid):
        ok, msg = ativar(guid)
        if not ok:
            messagebox.showerror("Erro", msg or "Não foi possível mudar o plano.")
        self.carregar()

    def _adicionar(self):
        if messagebox.askyesno("Adicionar plano", "Criar o plano 'Alto desempenho' a partir do modelo do Windows?"):
            ok, msg = _powercfg("/duplicatescheme", ALTO_DESEMPENHO)
            if not ok:
                messagebox.showerror("Erro", msg)
            self.carregar()
