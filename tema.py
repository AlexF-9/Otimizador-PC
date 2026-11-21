import tkinter as tk
from tkinter import ttk

BG = "#0f1117"
LATERAL = "#141823"
CARTAO = "#1a1f2c"
CARTAO2 = "#222839"
BORDA = "#2b3247"
TEXTO = "#e8eaf2"
SUAVE = "#8b93a7"
ACENTO = "#6c8cff"
ACENTO2 = "#5873ee"
PREENCHIMENTO = "#232f58"
VERDE = "#3ddc97"
AMARELO = "#ffb454"
VERMELHO = "#ff6b6b"
VERMELHO2 = "#e85a5a"

FONTE = "Segoe UI"


def fonte(tam=10, peso="normal"):
    return (FONTE, tam, peso)


def cor_nivel(pct):
    return VERDE if pct < 60 else AMARELO if pct < 85 else VERMELHO


def fmt(n):
    for u in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or u == "TB":
            return f"{n:.0f} {u}" if u == "B" else f"{n:.1f} {u}"
        n /= 1024


def estilos(root):
    s = ttk.Style(root)
    s.theme_use("clam")
    s.configure("Escuro.Treeview", background=CARTAO, fieldbackground=CARTAO, foreground=TEXTO,
                rowheight=30, borderwidth=0, font=fonte(10))
    s.configure("Escuro.Treeview.Heading", background=CARTAO, foreground=SUAVE, relief="flat",
                borderwidth=0, font=fonte(9, "bold"), padding=(8, 6))
    s.map("Escuro.Treeview.Heading", background=[("active", CARTAO2)])
    s.map("Escuro.Treeview", background=[("selected", ACENTO2)], foreground=[("selected", "white")])
    s.layout("Escuro.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
    s.configure("Escuro.Vertical.TScrollbar", troughcolor=CARTAO, background=CARTAO2,
                bordercolor=CARTAO, arrowcolor=SUAVE, lightcolor=CARTAO2, darkcolor=CARTAO2,
                gripcount=0)
    s.map("Escuro.Vertical.TScrollbar", background=[("active", BORDA)])


def cabecalho(master, titulo, subtitulo):
    f = tk.Frame(master, bg=BG)
    f.pack(fill="x", padx=28, pady=(24, 16))
    tk.Label(f, text=titulo, font=fonte(20, "bold"), bg=BG, fg=TEXTO).pack(anchor="w")
    tk.Label(f, text=subtitulo, font=fonte(10), bg=BG, fg=SUAVE).pack(anchor="w")
    return f


class Cartao(tk.Frame):
    def __init__(self, master, pad=18, **kw):
        super().__init__(master, bg=CARTAO, padx=pad, pady=pad, highlightthickness=1,
                         highlightbackground=BORDA, **kw)


class Rolavel(tk.Frame):

    def __init__(self, master, bg=CARTAO):
        super().__init__(master, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0)
        sb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview,
                           style="Escuro.Vertical.TScrollbar")
        self.interior = tk.Frame(self.canvas, bg=bg)
        janela = self.canvas.create_window(0, 0, window=self.interior, anchor="nw")
        self.canvas.configure(yscrollcommand=sb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.interior.bind("<Configure>",
                           lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(janela, width=e.width))
        roda = lambda e: self.canvas.yview_scroll(int(-e.delta / 120), "units")
        self.bind("<Enter>", lambda e: self.bind_all("<MouseWheel>", roda))
        self.bind("<Leave>", lambda e: self.unbind_all("<MouseWheel>"))


class Botao(tk.Label):
    CORES = {
        "primario": (ACENTO, ACENTO2, "white"),
        "secundario": (CARTAO2, BORDA, TEXTO),
        "perigo": (VERMELHO, VERMELHO2, "white"),
    }

    def __init__(self, master, texto, comando, tipo="primario"):
        self.normal, self.hover, self.fg = self.CORES[tipo]
        super().__init__(master, text=texto, bg=self.normal, fg=self.fg, font=fonte(10, "bold"),
                         padx=18, pady=9, cursor="hand2")
        self.comando = comando
        self.ativo = True
        self.bind("<Enter>", lambda e: self.ativo and self.config(bg=self.hover))
        self.bind("<Leave>", lambda e: self.ativo and self.config(bg=self.normal))
        self.bind("<Button-1>", lambda e: self.ativo and self.comando())

    def ativar(self, sim):
        self.ativo = bool(sim)
        if self.ativo:
            self.config(bg=self.normal, fg=self.fg, cursor="hand2")
        else:
            self.config(bg=CARTAO2, fg="#5c6378", cursor="arrow")


class Barra(tk.Canvas):

    def __init__(self, master, altura=8, bg=CARTAO):
        super().__init__(master, height=altura, bg=bg, highlightthickness=0)
        self.altura, self.pct, self.cor = altura, 0.0, ACENTO
        self.bind("<Configure>", lambda e: self._desenhar())

    def definir(self, pct, cor=None):
        self.pct = max(0.0, min(100.0, pct))
        if cor:
            self.cor = cor
        self._desenhar()

    def _desenhar(self):
        self.delete("all")
        w, h = self.winfo_width(), self.altura
        r = h / 2
        if w <= h:
            return
        opts = dict(width=h, capstyle="round")
        self.create_line(r, r, w - r, r, fill=CARTAO2, **opts)
        if self.pct > 0:
            x = r + (w - h) * self.pct / 100
            self.create_line(r, r, max(x, r + 0.5), r, fill=self.cor, **opts)


class Toggle(tk.Canvas):

    def __init__(self, master, var, comando=None, bg=CARTAO):
        super().__init__(master, width=44, height=24, bg=bg, highlightthickness=0, cursor="hand2")
        self.var, self.comando = var, comando
        self.bind("<Button-1>", self._clique)
        self._desenhar()

    def _clique(self, _):
        self.var.set(not self.var.get())
        self._desenhar()
        if self.comando:
            self.comando()

    def redesenhar(self):
        self._desenhar()

    def _desenhar(self):
        self.delete("all")
        on = self.var.get()
        self.create_line(12, 12, 32, 12, width=22, capstyle="round", fill=ACENTO if on else BORDA)
        x = 32 if on else 12
        self.create_oval(x - 8, 4, x + 8, 20, fill="white" if on else SUAVE, outline="")


class Grafico(tk.Canvas):

    def __init__(self, master, altura=90, pontos=60, bg=CARTAO):
        super().__init__(master, height=altura, bg=bg, highlightthickness=0)
        self.valores, self.pontos = [], pontos
        self.bind("<Configure>", lambda e: self._desenhar())

    def definir(self, valores):
        self.valores = list(valores)
        self._desenhar()

    def _desenhar(self):
        self.delete("all")
        w, h = self.winfo_width(), int(self["height"])
        if w < 20 or len(self.valores) < 2:
            return
        for p in (25, 50, 75):
            y = h - h * p / 100
            self.create_line(0, y, w, y, fill=CARTAO2)
        passo = w / (self.pontos - 1)
        x0 = w - passo * (len(self.valores) - 1)
        pts = []
        for i, v in enumerate(self.valores):
            pts += [x0 + i * passo, h - 2 - (h - 4) * v / 100]
        self.create_polygon(x0, h, *pts, w, h, fill=PREENCHIMENTO, outline="")
        self.create_line(*pts, fill=ACENTO, width=2)
