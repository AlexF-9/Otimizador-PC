import csv
import ctypes
import io
import os
import queue
import shutil
import subprocess
import threading
import tkinter as tk
from collections import deque
from ctypes import wintypes
from tkinter import messagebox, ttk

import tema as t

CREATE_NO_WINDOW = 0x08000000
INTERVALO_MS = 2000
HISTORICO = 60  # 60 pontos x 2 s = 2 minutos


class _MEM(ctypes.Structure):
    _fields_ = [("dwLength", wintypes.DWORD), ("dwMemoryLoad", wintypes.DWORD),
                ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                ("sullAvailExtendedVirtual", ctypes.c_ulonglong)]


def ram():
    m = _MEM()
    m.dwLength = ctypes.sizeof(_MEM)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return m.ullTotalPhys - m.ullAvailPhys, m.ullTotalPhys, m.dwMemoryLoad


def _tempos():
    i, k, u = (wintypes.FILETIME() for _ in range(3))
    ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(i), ctypes.byref(k), ctypes.byref(u))
    v = lambda ft: (ft.dwHighDateTime << 32) | ft.dwLowDateTime
    return v(i), v(k) + v(u)  # inativo, total (o tempo de kernel já inclui o inativo)


class CpuMeter:
    def __init__(self):
        self.ultimo = _tempos()

    def percent(self):
        inativo, total = _tempos()
        di, dt = inativo - self.ultimo[0], total - self.ultimo[1]
        self.ultimo = (inativo, total)
        return max(0.0, min(100.0, 100.0 * (1 - di / dt))) if dt else 0.0


def disco():
    u = shutil.disk_usage(os.environ.get("SystemDrive", "C:") + "\\")
    return u.used, u.total, 100 * u.used / u.total


def processos():
    out = subprocess.run(["tasklist", "/fo", "csv", "/nh"], capture_output=True, text=True,
                         encoding="oem", errors="replace", creationflags=CREATE_NO_WINDOW).stdout
    res = []
    for row in csv.reader(io.StringIO(out)):
        if len(row) >= 5 and row[1].isdigit():
            mem = "".join(c for c in row[4] if c.isdigit())
            res.append((row[0], int(row[1]), int(mem or 0) * 1024))
    return sorted(res, key=lambda r: r[2], reverse=True)


def terminar_processo(pid, forcar=False):
    cmd = ["taskkill", "/PID", str(pid)] + (["/F"] if forcar else [])
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="oem", errors="replace",
                       creationflags=CREATE_NO_WINDOW)
    return r.returncode == 0, (r.stderr or r.stdout).strip()


class Monitor(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=t.BG)
        self.cpu = CpuMeter()
        self.q = queue.Queue()
        self.a_ler = False
        self.hist = deque(maxlen=HISTORICO)

        t.cabecalho(self, "Monitorização", "Atualiza a cada 2 segundos.")

        linha = tk.Frame(self, bg=t.BG)
        linha.pack(fill="x", padx=28)
        self.stats = {}
        nomes = ("CPU", "Memória RAM", "Disco " + os.environ.get("SystemDrive", "C:"))
        for i, nome in enumerate(nomes):
            c = t.Cartao(linha)
            c.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 7, 0 if i == 2 else 7))
            linha.columnconfigure(i, weight=1, uniform="stats")
            tk.Label(c, text=nome, font=t.fonte(10), bg=t.CARTAO, fg=t.SUAVE).pack(anchor="w")
            v = tk.Label(c, text="—", font=t.fonte(24, "bold"), bg=t.CARTAO, fg=t.TEXTO)
            v.pack(anchor="w")
            d = tk.Label(c, text=" ", font=t.fonte(9), bg=t.CARTAO, fg=t.SUAVE)
            d.pack(anchor="w")
            b = t.Barra(c)
            b.pack(fill="x", pady=(10, 0))
            self.stats[i] = (v, d, b)

        g = t.Cartao(self)
        g.pack(fill="x", padx=28, pady=(14, 0))
        tk.Label(g, text="Histórico da CPU (últimos 2 minutos)", font=t.fonte(10, "bold"),
                 bg=t.CARTAO, fg=t.TEXTO).pack(anchor="w")
        self.grafico = t.Grafico(g, altura=80, pontos=HISTORICO)
        self.grafico.pack(fill="x", pady=(10, 0))

        tab = t.Cartao(self)
        tab.pack(fill="both", expand=True, padx=28, pady=(14, 24))
        topo = tk.Frame(tab, bg=t.CARTAO)
        topo.pack(fill="x")
        tk.Label(topo, text="Processos que mais memória usam", font=t.fonte(10, "bold"),
                 bg=t.CARTAO, fg=t.TEXTO).pack(side="left")
        self.b_terminar = t.Botao(topo, "Terminar processo", self.terminar, tipo="perigo")
        self.b_terminar.pack(side="right")
        self.b_terminar.ativar(False)
        corpo = tk.Frame(tab, bg=t.CARTAO)
        corpo.pack(fill="both", expand=True, pady=(12, 0))
        self.tree = ttk.Treeview(corpo, columns=("nome", "pid", "mem"), show="headings",
                                 style="Escuro.Treeview", selectmode="browse")
        for col, titulo, larg, anc in (("nome", "PROCESSO", 320, "w"), ("pid", "PID", 90, "e"),
                                       ("mem", "MEMÓRIA", 120, "e")):
            self.tree.heading(col, text=titulo, anchor=anc)
            self.tree.column(col, width=larg, anchor=anc, stretch=(col == "nome"))
        self.tree.tag_configure("par", background=t.CARTAO2)
        sb = ttk.Scrollbar(corpo, orient="vertical", command=self.tree.yview,
                           style="Escuro.Vertical.TScrollbar")
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.b_terminar.ativar(bool(self.tree.selection())))

        self._tick()
        self._ler_fila()

    def _tick(self):
        c = self.cpu.percent()
        self.hist.append(c)
        self.grafico.definir(self.hist)
        self._mostrar(0, c, f"{c:.0f}%", "Utilização do processador")
        u, tot, p = ram()
        self._mostrar(1, p, f"{p:.0f}%", f"{t.fmt(u)} de {t.fmt(tot)}")
        u, tot, p = disco()
        self._mostrar(2, p, f"{p:.0f}%", f"{t.fmt(u)} de {t.fmt(tot)} · {t.fmt(tot - u)} livres")
        if self.winfo_ismapped() and not self.a_ler:
            self.a_ler = True
            threading.Thread(target=self._ler_processos, daemon=True).start()
        self.after(INTERVALO_MS, self._tick)

    def _mostrar(self, i, pct, valor, detalhe):
        v, d, b = self.stats[i]
        cor = t.cor_nivel(pct)
        v.config(text=valor, fg=cor)
        d.config(text=detalhe)
        b.definir(pct, cor)

    def _ler_processos(self):
        try:
            self.q.put(("procs", processos()[:50]))
        except Exception:
            self.q.put(("procs", None))

    def _ler_fila(self):
        try:
            while True:
                msg, dados = self.q.get_nowait()
                if msg == "procs":
                    self.a_ler = False
                    if dados is not None:
                        self._preencher(dados)
        except queue.Empty:
            pass
        self.after(100, self._ler_fila)

    def _preencher(self, procs):
        sel = self.tree.selection()
        pid_sel = self.tree.item(sel[0], "values")[1] if sel else None
        topo = self.tree.yview()[0]
        self.tree.delete(*self.tree.get_children())
        for i, (nome, pid, mem) in enumerate(procs):
            iid = self.tree.insert("", "end", values=(nome, pid, t.fmt(mem)),
                                   tags=("par",) if i % 2 else ())
            if pid_sel is not None and str(pid) == str(pid_sel):
                self.tree.selection_set(iid)
        self.tree.yview_moveto(topo)
        if not self.tree.selection():
            self.b_terminar.ativar(False)

    def terminar(self):
        sel = self.tree.selection()
        if not sel:
            return
        nome, pid, _ = self.tree.item(sel[0], "values")
        if not messagebox.askyesno("Terminar processo", f"Terminar '{nome}' (PID {pid})?\n\n"
                                   "Qualquer trabalho não guardado nesse programa perde-se.", icon="warning"):
            return
        ok, msg = terminar_processo(pid)
        if not ok and messagebox.askyesno("Não respondeu", f"{msg}\n\nForçar o encerramento?", icon="warning"):
            ok, msg = terminar_processo(pid, forcar=True)
        if not ok:
            messagebox.showwarning("Não foi possível", msg or "O processo não pôde ser terminado.")
