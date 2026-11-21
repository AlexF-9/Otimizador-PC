import ctypes
import os
import queue
import threading
import tkinter as tk
from tkinter import messagebox

import tema as t

LOCAL = os.environ.get("LOCALAPPDATA", "")
WINDIR = os.environ.get("WINDIR", r"C:\Windows")
TEMP = os.environ.get("TEMP", "")
RECICLAGEM = "Reciclagem"
MINIATURAS = "Cache de miniaturas"

CATEGORIAS = {
    "Temporários do utilizador": ([TEMP], "Ficheiros temporários deixados pelas aplicações"),
    "Temporários do Windows": ([os.path.join(WINDIR, "Temp")], "Requer administrador"),
    "Cache do Chrome": ([
        os.path.join(LOCAL, r"Google\Chrome\User Data\Default\Cache"),
        os.path.join(LOCAL, r"Google\Chrome\User Data\Default\Code Cache"),
    ], "Feche o Chrome antes de limpar"),
    "Cache do Edge": ([
        os.path.join(LOCAL, r"Microsoft\Edge\User Data\Default\Cache"),
        os.path.join(LOCAL, r"Microsoft\Edge\User Data\Default\Code Cache"),
    ], "Feche o Edge antes de limpar"),
    MINIATURAS: ([os.path.join(LOCAL, r"Microsoft\Windows\Explorer")], "Pré-visualizações de imagens no Explorador"),
    "Relatórios de erros": ([os.path.join(LOCAL, r"Microsoft\Windows\WER")], "Relatórios de falhas antigos"),
    "Cache do Windows Update": ([os.path.join(WINDIR, r"SoftwareDistribution\Download")], "Requer administrador"),
}
ITENS = [(n, d) for n, (_, d) in CATEGORIAS.items()] + [(RECICLAGEM, "Esvazia a Reciclagem (desligado por defeito)")]


def _e_ligacao(p):
    # nunca seguir symlinks/junctions
    try:
        return os.path.islink(p) or os.path.isjunction(p)
    except OSError:
        return True


def ficheiros(pasta, so_miniaturas=False):
    if not pasta or not os.path.isdir(pasta):
        return
    for raiz, dirs, nomes in os.walk(pasta):
        dirs[:] = [d for d in dirs if not _e_ligacao(os.path.join(raiz, d))]
        for nome in nomes:
            if so_miniaturas and not nome.lower().startswith(("thumbcache_", "iconcache_")):
                continue
            p = os.path.join(raiz, nome)
            try:
                if not os.path.islink(p):
                    yield p, os.path.getsize(p)
            except OSError:
                pass


def tamanho_categoria(nome):
    if nome == RECICLAGEM:
        return tamanho_reciclagem()
    return sum(s for p in CATEGORIAS[nome][0] for _, s in ficheiros(p, nome == MINIATURAS))


def tamanho_reciclagem():
    class QUERY(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_ulong), ("i64Size", ctypes.c_longlong),
                    ("i64NumItems", ctypes.c_longlong)]
    q = QUERY(ctypes.sizeof(QUERY), 0, 0)
    try:
        ctypes.windll.shell32.SHQueryRecycleBinW(None, ctypes.byref(q))
        return q.i64Size
    except Exception:
        return 0


def limpar_categoria(nome):
    if nome == RECICLAGEM:
        antes = tamanho_reciclagem()
        ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 0x7)
        return antes - tamanho_reciclagem(), 0
    libertado = falhas = 0
    for pasta in CATEGORIAS[nome][0]:
        for p, s in list(ficheiros(pasta, nome == MINIATURAS)):
            try:
                os.remove(p)
                libertado += s
            except OSError:
                falhas += 1
        if os.path.isdir(pasta):
            for raiz, dirs, _ in os.walk(pasta, topdown=False):
                for d in dirs:
                    sub = os.path.join(raiz, d)
                    if not _e_ligacao(sub):
                        try:
                            os.rmdir(sub)
                        except OSError:
                            pass
    return libertado, falhas


class Limpeza(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=t.BG)
        self.q = queue.Queue()
        self.tamanhos, self.vars, self.lbl_tam = {}, {}, {}
        self.ocupado = False

        t.cabecalho(self, "Limpeza", "Analise primeiro. Nada é apagado até carregar em Limpar.")

        resumo = t.Cartao(self, pad=20)
        resumo.pack(fill="x", padx=28, pady=(0, 14))
        esq = tk.Frame(resumo, bg=t.CARTAO)
        esq.pack(side="left", fill="x", expand=True)
        self.lbl_total = tk.Label(esq, text="—", font=t.fonte(28, "bold"), bg=t.CARTAO, fg=t.TEXTO)
        self.lbl_total.pack(anchor="w")
        self.lbl_estado = tk.Label(esq, text="Carregue em Analisar para ver quanto espaço pode libertar",
                                   font=t.fonte(10), bg=t.CARTAO, fg=t.SUAVE)
        self.lbl_estado.pack(anchor="w")
        self.barra = t.Barra(esq)
        self.barra.pack(fill="x", pady=(14, 0))
        dir_ = tk.Frame(resumo, bg=t.CARTAO)
        dir_.pack(side="right", padx=(24, 0))
        self.b_limpar = t.Botao(dir_, "Limpar selecionado", self.limpar)
        self.b_limpar.pack(side="right")
        self.b_analisar = t.Botao(dir_, "Analisar", self.analisar, tipo="secundario")
        self.b_analisar.pack(side="right", padx=(0, 10))
        self.b_limpar.ativar(False)

        lista = t.Cartao(self, pad=0)
        lista.pack(fill="both", expand=True, padx=28, pady=(0, 24))
        for i, (nome, desc) in enumerate(ITENS):
            if i:
                tk.Frame(lista, bg=t.BORDA, height=1).pack(fill="x")
            linha = tk.Frame(lista, bg=t.CARTAO, padx=18, pady=6)
            linha.pack(fill="x")
            v = tk.BooleanVar(value=nome != RECICLAGEM)
            self.vars[nome] = v
            t.Toggle(linha, v, self._atualizar_total).pack(side="left")
            txt = tk.Frame(linha, bg=t.CARTAO)
            txt.pack(side="left", padx=14)
            tk.Label(txt, text=nome, font=t.fonte(10, "bold"), bg=t.CARTAO, fg=t.TEXTO).pack(anchor="w")
            tk.Label(txt, text=desc, font=t.fonte(9), bg=t.CARTAO, fg=t.SUAVE).pack(anchor="w")
            lbl = tk.Label(linha, text="—", font=t.fonte(11, "bold"), bg=t.CARTAO, fg=t.SUAVE)
            lbl.pack(side="right")
            self.lbl_tam[nome] = lbl

        self.after(100, self._ler_fila)

    def _set_ocupado(self, sim):
        self.ocupado = sim
        self.b_analisar.ativar(not sim)
        self._atualizar_total()

    def _selecionados(self):
        return [n for n, _ in ITENS if self.vars[n].get()]

    def _atualizar_total(self):
        sel = self._selecionados()
        self.b_limpar.ativar(bool(self.tamanhos) and bool(sel) and not self.ocupado)
        if self.ocupado or not self.tamanhos:
            return
        total = sum(self.tamanhos.get(n, 0) for n in sel)
        self.lbl_total.config(text=t.fmt(total))
        self.lbl_estado.config(text=f"podem ser libertados ({len(sel)} de {len(ITENS)} categorias selecionadas)")

    def _mostrar_tamanho(self, nome, s):
        cor = t.SUAVE if s == 0 else t.AMARELO if s >= 500 * 1024 ** 2 else t.TEXTO
        self.lbl_tam[nome].config(text=t.fmt(s), fg=cor)

    def _ler_fila(self):
        try:
            while True:
                msg, *dados = self.q.get_nowait()
                if msg == "prog":
                    i, n, texto = dados
                    self.barra.definir(100 * i / n, t.ACENTO)
                    self.lbl_estado.config(text=texto)
                elif msg == "tam":
                    nome, s = dados
                    self.tamanhos[nome] = s
                    self._mostrar_tamanho(nome, s)
                elif msg == "fim_analise":
                    self.barra.definir(100, t.VERDE)
                    self._set_ocupado(False)
                elif msg == "fim_limpeza":
                    libertado, falhas = dados
                    self.barra.definir(100, t.VERDE)
                    self._set_ocupado(False)
                    extra = f"\n\n{falhas} ficheiros estavam em uso e foram ignorados." if falhas else ""
                    messagebox.showinfo("Limpeza concluída", f"Foram libertados {t.fmt(libertado)}.{extra}")
                    self.analisar()
                elif msg == "erro":
                    messagebox.showerror("Erro", dados[0])
        except queue.Empty:
            pass
        self.after(100, self._ler_fila)

    def analisar(self):
        if self.ocupado:
            return
        self.tamanhos = {}
        for nome, _ in ITENS:
            self.lbl_tam[nome].config(text="…", fg=t.SUAVE)
        self.lbl_total.config(text="A analisar…")
        self._set_ocupado(True)
        threading.Thread(target=self._trabalho_analise, daemon=True).start()

    def _trabalho_analise(self):
        try:
            for i, (nome, _) in enumerate(ITENS):
                self.q.put(("prog", i, len(ITENS), f"A analisar: {nome}"))
                self.q.put(("tam", nome, tamanho_categoria(nome)))
        except Exception as e:
            self.q.put(("erro", str(e)))
        finally:
            self.q.put(("fim_analise",))

    def limpar(self):
        sel = self._selecionados()
        if self.ocupado or not sel:
            return
        if not messagebox.askyesno("Confirmar limpeza", "Vão ser apagados os ficheiros de:\n\n• " +
                                   "\n• ".join(sel) + "\n\nEsta ação não pode ser desfeita. Continuar?",
                                   icon="warning"):
            return
        self.lbl_total.config(text="A limpar…")
        self._set_ocupado(True)
        threading.Thread(target=self._trabalho_limpeza, args=(sel,), daemon=True).start()

    def _trabalho_limpeza(self, sel):
        libertado = falhas = 0
        try:
            for i, nome in enumerate(sel):
                self.q.put(("prog", i, len(sel), f"A limpar: {nome}"))
                lib, fal = limpar_categoria(nome)
                libertado += lib
                falhas += fal
        except Exception as e:
            self.q.put(("erro", str(e)))
        finally:
            self.q.put(("fim_limpeza", libertado, falhas))
