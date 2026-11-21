import queue
import threading
import tkinter as tk
from tkinter import messagebox

import arranque
import energia
import limpeza
import monitor
import tema as t

SEGURAS = ["Temporários do utilizador", "Temporários do Windows", "Relatórios de erros",
           "Cache do Chrome", "Cache do Edge"]
BROWSERS = {"Cache do Chrome": ("chrome.exe", "o Chrome"), "Cache do Edge": ("msedge.exe", "o Edge")}


def otimizar_tudo(progresso):
    abertos = {p[0].lower() for p in monitor.processos()}
    res = []
    for i, nome in enumerate(SEGURAS):
        progresso(i, len(SEGURAS), nome)
        if nome in BROWSERS and BROWSERS[nome][0] in abertos:
            res.append((nome, f"Ignorado: {BROWSERS[nome][1]} está aberto", 0))
            continue
        lib, falhas = limpeza.limpar_categoria(nome)
        txt = f"{t.fmt(lib)} libertados" + (f" · {falhas} em uso" if falhas else "")
        res.append((nome, txt, lib))
    return res


class Inicio(tk.Frame):
    def __init__(self, master, ir_para):
        super().__init__(master, bg=t.BG)
        self.q = queue.Queue()
        self.ocupado = False
        t.cabecalho(self, "Início", "O estado do seu PC e otimização num clique.")

        hero = t.Cartao(self, pad=24)
        hero.pack(fill="x", padx=28)
        esq = tk.Frame(hero, bg=t.CARTAO)
        esq.pack(side="left", fill="x", expand=True)
        tk.Label(esq, text="Otimizar tudo", font=t.fonte(18, "bold"), bg=t.CARTAO, fg=t.TEXTO).pack(anchor="w")
        tk.Label(esq, text="Limpa temporários, relatórios de erros e as caches do Chrome e do Edge (se estiverem "
                           "fechados).\nNão mexe na Reciclagem, no Windows Update nem nos programas de arranque.",
                 font=t.fonte(9), bg=t.CARTAO, fg=t.SUAVE, justify="left").pack(anchor="w", pady=(4, 0))
        self.barra = t.Barra(esq)
        self.barra.pack(fill="x", pady=(14, 0))
        self.lbl_estado = tk.Label(esq, text="Pronto.", font=t.fonte(9), bg=t.CARTAO, fg=t.SUAVE)
        self.lbl_estado.pack(anchor="w", pady=(6, 0))
        self.botao = t.Botao(hero, "Otimizar agora", self.otimizar)
        self.botao.pack(side="right", padx=(24, 0))

        linha = tk.Frame(self, bg=t.BG)
        linha.pack(fill="x", padx=28, pady=14)
        self.valores = {}
        for i, (chave, titulo, pagina) in enumerate((("disco", "Espaço livre no disco", "Limpeza"),
                                                     ("arranque", "Programas de arranque", "Arranque"),
                                                     ("energia", "Plano de energia", "Energia"))):
            c = t.Cartao(linha)
            c.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 7, 0 if i == 2 else 7))
            linha.columnconfigure(i, weight=1, uniform="r")
            tk.Label(c, text=titulo, font=t.fonte(10), bg=t.CARTAO, fg=t.SUAVE).pack(anchor="w")
            v = tk.Label(c, text="—", font=t.fonte(16, "bold"), bg=t.CARTAO, fg=t.TEXTO, anchor="w")
            v.pack(fill="x", pady=(4, 0))
            v.bind("<Configure>", lambda e: e.widget.config(wraplength=max(e.width - 4, 50)))
            lk = tk.Label(c, text="Ver detalhes  →", font=t.fonte(9, "bold"), bg=t.CARTAO, fg=t.ACENTO, cursor="hand2")
            lk.pack(anchor="w", pady=(8, 0))
            lk.bind("<Button-1>", lambda e, p=pagina: ir_para(p))
            self.valores[chave] = v

        self.res = t.Cartao(self)
        self.res.pack(fill="both", expand=True, padx=28, pady=(0, 24))
        tk.Label(self.res, text="Último resultado", font=t.fonte(10, "bold"), bg=t.CARTAO,
                 fg=t.TEXTO).pack(anchor="w")
        self.corpo = tk.Frame(self.res, bg=t.CARTAO)
        self.corpo.pack(fill="both", expand=True, pady=(8, 0))
        tk.Label(self.corpo, text="Ainda não otimizou nesta sessão.", font=t.fonte(9), bg=t.CARTAO,
                 fg=t.SUAVE).pack(anchor="w")

        self.atualizar_resumo()
        self.after(100, self._ler_fila)

    def ao_mostrar(self):
        self.atualizar_resumo()

    def atualizar_resumo(self):
        usado, total, pct = monitor.disco()
        livre = total - usado
        self.valores["disco"].config(text=f"{t.fmt(livre)}  ({100 - pct:.0f}%)", fg=t.cor_nivel(pct))
        progs = arranque.listar()
        ativos = sum(p.ativo for p in progs)
        self.valores["arranque"].config(text=f"{ativos} de {len(progs)} ativos",
                                        fg=t.AMARELO if ativos > 10 else t.TEXTO)
        nome = energia.plano_ativo()
        self.valores["energia"].config(text=nome, font=t.fonte(16 if len(nome) <= 18 else 11, "bold"),
                                       justify="left")

    def otimizar(self):
        if self.ocupado:
            return
        if not messagebox.askyesno("Otimizar tudo", "Vão ser apagados os ficheiros de:\n\n• " + "\n• ".join(SEGURAS) +
                                   "\n\nOs ficheiros em uso são ignorados. Continuar?"):
            return
        self.ocupado = True
        self.botao.ativar(False)
        threading.Thread(target=self._trabalho, daemon=True).start()

    def _trabalho(self):
        try:
            res = otimizar_tudo(lambda i, n, nome: self.q.put(("prog", i, n, nome)))
            self.q.put(("fim", res))
        except Exception as e:
            self.q.put(("erro", str(e)))

    def _ler_fila(self):
        try:
            while True:
                msg, *d = self.q.get_nowait()
                if msg == "prog":
                    i, n, nome = d
                    self.barra.definir(100 * i / n, t.ACENTO)
                    self.lbl_estado.config(text=f"A limpar: {nome}")
                elif msg in ("fim", "erro"):
                    self.ocupado = False
                    self.botao.ativar(True)
                    if msg == "erro":
                        self.barra.definir(0)
                        self.lbl_estado.config(text="Ocorreu um erro.")
                        messagebox.showerror("Erro", d[0])
                    else:
                        self._mostrar_resultado(d[0])
                    self.atualizar_resumo()
        except queue.Empty:
            pass
        self.after(100, self._ler_fila)

    def _mostrar_resultado(self, res):
        total = sum(b for *_, b in res)
        self.barra.definir(100, t.VERDE)
        self.lbl_estado.config(text=f"Concluído: {t.fmt(total)} libertados.")
        for w in self.corpo.winfo_children():
            w.destroy()
        for nome, txt, b in res:
            l = tk.Frame(self.corpo, bg=t.CARTAO)
            l.pack(fill="x", pady=3)
            tk.Label(l, text=nome, font=t.fonte(10), bg=t.CARTAO, fg=t.TEXTO).pack(side="left")
            cor = t.VERDE if b else (t.AMARELO if txt.startswith("Ignorado") else t.SUAVE)
            tk.Label(l, text=txt, font=t.fonte(10, "bold"), bg=t.CARTAO, fg=cor).pack(side="right")
